"""Acesso ao Google Sheets via gspread (`SPECS/02` §5).

Único módulo, junto com `repositories/planilha/`, que conhece o gspread
(`SPECS/03` §4.2). Recebe parâmetros simples em vez de `Settings`, para não
depender de outra camada.
"""

import json
import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import gspread
from google.auth.exceptions import TransportError
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError, SpreadsheetNotFound
from requests.exceptions import RequestException

from app.domain.erros import (
    ApiSheetsDesabilitada,
    CredenciaisInvalidas,
    ErroPlanilha,
    PlanilhaIndisponivel,
    PlanilhaNaoEncontrada,
    SemPermissaoPlanilha,
)

ESCOPOS = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

TENTATIVAS_PADRAO = 4
ESPERA_MAXIMA_SEGUNDOS = 16.0

# Motivos de 403 que indicam API desativada no projeto, não falta de
# compartilhamento (`SPECS/02` §5.6).
MOTIVOS_API_DESABILITADA = frozenset({"SERVICE_DISABLED", "accessNotConfigured"})

CODIGOS_TRANSITORIOS = frozenset({429, 500, 502, 503, 504})

# Falta de rede e afins (`SPECS/02` §5.6): também são transitórios.
ERROS_DE_TRANSPORTE = (RequestException, TransportError, OSError)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlanilhaAberta:
    """Planilha já aberta, com o título lido na abertura."""

    titulo: str
    documento: gspread.Spreadsheet


def obter_client_email(caminho_credenciais: str | Path) -> str | None:
    """Lê **somente** o campo `client_email` do arquivo de credenciais.

    Serve para a mensagem de 403 (CA-16.1). Nenhum outro campo é lido, e a
    função nunca levanta: se o arquivo não puder ser lido, devolve `None`,
    para que montar uma mensagem de erro não gere outro erro.
    """
    try:
        with open(caminho_credenciais, encoding="utf-8") as arquivo:
            valor = json.load(arquivo).get("client_email")
    except (OSError, ValueError):
        return None
    return valor if isinstance(valor, str) and valor else None


def carregar_credenciais(caminho_credenciais: str | Path) -> Credentials:
    """Carrega a chave da service account com os escopos de `SPECS/02` §5.3."""
    try:
        return Credentials.from_service_account_file(str(caminho_credenciais), scopes=ESCOPOS)
    except (OSError, ValueError, KeyError) as erro:
        # Nunca inclui o conteúdo do arquivo na mensagem nem no log (RNF-05).
        logger.error("Falha ao carregar credenciais de %s", caminho_credenciais)
        raise CredenciaisInvalidas() from erro


def calcular_espera(falhas: int) -> float:
    """Backoff exponencial truncado: 2 s, 4 s, 8 s... com teto de 16 s.

    `falhas` é quantas tentativas já falharam (1 para a espera antes da 2ª).
    """
    return min(2.0**falhas + random.random(), ESPERA_MAXIMA_SEGUNDOS)


def executar_com_retry[T](
    operacao: Callable[[], T],
    *,
    client_email: str | None = None,
    tentativas: int = TENTATIVAS_PADRAO,
    dormir: Callable[[float], None] = time.sleep,
) -> T:
    """Executa `operacao` retentando apenas falhas transitórias.

    429, 5xx e erros de transporte são retentados (`SPECS/02` §5.5); 403, 404
    e credencial inválida falham na primeira tentativa.
    """
    for numero in range(1, tentativas + 1):
        try:
            return operacao()
        except Exception as erro:
            traduzido = traduzir_erro(erro, client_email=client_email)
            if not isinstance(traduzido, ErroPlanilha):
                # Não é falha de planilha (provavelmente um defeito nosso):
                # sobe intacto para virar ERRO_INTERNO, sem gastar tentativas.
                raise
            if not isinstance(traduzido, PlanilhaIndisponivel) or numero == tentativas:
                raise traduzido from erro
            espera = calcular_espera(numero)
            logger.warning(
                "Google Sheets falhou (tentativa %d de %d); nova tentativa em %.1fs",
                numero,
                tentativas,
                espera,
            )
            dormir(espera)
    raise AssertionError("inalcançável: o laço sempre retorna ou levanta")


def traduzir_erro(erro: Exception, *, client_email: str | None = None) -> Exception:
    """Converte um erro do Google na exceção de domínio de `SPECS/02` §5.6.

    Devolve o **próprio** erro quando ele não é uma falha conhecida de
    planilha, para que defeitos de programação não sejam mascarados como
    indisponibilidade.
    """
    if isinstance(erro, ErroPlanilha):
        return erro
    if isinstance(erro, SpreadsheetNotFound):
        return PlanilhaNaoEncontrada()
    if isinstance(erro, APIError):
        return _traduzir_api_error(erro, client_email=client_email)
    if isinstance(erro, ERROS_DE_TRANSPORTE):
        return PlanilhaIndisponivel()
    return erro


def _traduzir_api_error(erro: APIError, *, client_email: str | None) -> Exception:
    codigo = erro.code
    if codigo == 403:
        if _motivos(erro) & MOTIVOS_API_DESABILITADA:
            return ApiSheetsDesabilitada()
        return SemPermissaoPlanilha.para(client_email)
    if codigo == 404:
        return PlanilhaNaoEncontrada()
    if codigo in CODIGOS_TRANSITORIOS:
        return PlanilhaIndisponivel()
    # Código inesperado (ex.: 400): reporta de uma vez, sem retry, mantendo
    # o código PLANILHA_INDISPONIVEL de `SPECS/03` §6.2.
    return ErroPlanilha()


def _motivos(erro: APIError) -> frozenset[str]:
    """Motivos declarados dentro do erro do Google (`errors[]` e `details[]`)."""
    detalhe = erro.error if isinstance(erro.error, dict) else {}
    motivos = {str(detalhe.get("status", ""))}
    for chave in ("errors", "details"):
        for item in detalhe.get(chave) or []:
            if isinstance(item, dict):
                motivos.add(str(item.get("reason", "")))
    return frozenset(motivo for motivo in motivos if motivo)


def abrir_planilha(
    caminho_credenciais: str | Path,
    spreadsheet_id: str,
    *,
    tentativas: int = TENTATIVAS_PADRAO,
    dormir: Callable[[float], None] = time.sleep,
) -> PlanilhaAberta:
    """Autentica e abre a planilha por ID (`SPECS/02` §5.2).

    Levanta a exceção de domínio correspondente a cada falha de §5.6.
    """
    client_email = obter_client_email(caminho_credenciais)
    credenciais = carregar_credenciais(caminho_credenciais)

    def operacao() -> PlanilhaAberta:
        cliente = gspread.authorize(credenciais)
        documento = cliente.open_by_key(spreadsheet_id)
        return PlanilhaAberta(titulo=documento.title, documento=documento)

    planilha = executar_com_retry(
        operacao, client_email=client_email, tentativas=tentativas, dormir=dormir
    )
    logger.info("Planilha aberta: %s", planilha.titulo)
    return planilha


class ConexaoPlanilha:
    """Mantém a planilha aberta e o último erro, permitindo nova tentativa.

    Uma instância vive durante todo o processo (criada no lifespan). Guardar o
    erro em vez de propagá-lo é o que deixa o servidor no ar com a planilha
    inacessível (`SPECS/03` §4.5) e o que permite ao `GET /api/health` tentar
    de novo sem reiniciar (CA-16.2).

    `preparar` roda logo depois de abrir, a cada conexão estabelecida — é o
    `bootstrap` das abas, injetado por `main.py`. A conexão só conta como
    estabelecida se ele também passar (`SPECS/03` §4.5).
    """

    def __init__(
        self,
        caminho_credenciais: str | Path,
        spreadsheet_id: str,
        *,
        tentativas: int = 1,
        preparar: Callable[[gspread.Spreadsheet], None] | None = None,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        self._caminho_credenciais = caminho_credenciais
        self._spreadsheet_id = spreadsheet_id
        self._tentativas = tentativas
        self._preparar = preparar
        self._dormir = dormir
        self._planilha: PlanilhaAberta | None = None
        self._erro: ErroPlanilha | None = None

    @property
    def planilha(self) -> PlanilhaAberta | None:
        return self._planilha

    @property
    def erro(self) -> ErroPlanilha | None:
        return self._erro

    @property
    def conectada(self) -> bool:
        return self._planilha is not None

    def conectar(self) -> PlanilhaAberta | None:
        """Tenta abrir e preparar a planilha, sem propagar falha.

        Reaproveita a conexão já estabelecida (cotas — `SPECS/02` §5.5). Em
        caso de falha, guarda a exceção de domínio e devolve `None`.
        """
        if self._planilha is not None:
            return self._planilha
        try:
            planilha = abrir_planilha(
                self._caminho_credenciais,
                self._spreadsheet_id,
                tentativas=self._tentativas,
            )
            self._preparar_planilha(planilha)
            self._planilha = planilha
            self._erro = None
        except ErroPlanilha as erro:
            self._planilha = None
            self._erro = erro
            logger.warning("Planilha inacessível: %s", erro.mensagem)
        return self._planilha

    def _preparar_planilha(self, planilha: PlanilhaAberta) -> None:
        """Roda `preparar` com a mesma política de tentativas da abertura.

        Retentar é seguro porque o `bootstrap` é idempotente.
        """
        preparar = self._preparar
        if preparar is None:
            return
        executar_com_retry(
            lambda: preparar(planilha.documento),
            client_email=obter_client_email(self._caminho_credenciais),
            tentativas=self._tentativas,
        )
        logger.info("Planilha preparada: %s", planilha.titulo)

    def exigir_planilha(self) -> PlanilhaAberta:
        """Devolve a planilha aberta ou levanta o erro que impediu a conexão.

        É o que faz os endpoints de negócio responderem 503 (`SPECS/03` §4.5).
        """
        if self._planilha is not None:
            return self._planilha
        raise self._erro or PlanilhaIndisponivel()

    def executar[T](self, operacao: Callable[[gspread.Spreadsheet], T]) -> T:
        """Roda uma operação de repositório sobre a planilha aberta.

        Sem conexão, levanta o erro guardado (503). Com conexão, aplica a
        política de tentativas de `SPECS/02` §5.5 e traduz os erros do Google.
        """
        documento = self.exigir_planilha().documento
        return executar_com_retry(
            lambda: operacao(documento),
            client_email=obter_client_email(self._caminho_credenciais),
            dormir=self._dormir,
        )
