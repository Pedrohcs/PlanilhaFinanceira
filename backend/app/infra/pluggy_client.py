"""Cliente da API da Pluggy, só leitura (`SPECS/02` §11; ADR-16, ADR-17).

Único módulo do app que usa o `httpx` para falar com a Pluggy (`SPECS/03`
§4.2). Recebe parâmetros simples em vez de `Settings`, para não depender de
outra camada, e implementa o Protocol `FontePluggy` da importação.

Segredos (RNF-05): o Client Secret e a `apiKey` ficam só em memória e nunca
entram em log nem em mensagem de erro — os logs trazem apenas método, caminho
e status.
"""

import logging
import random
import threading
import time
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.domain.datas import data_em_brasilia, hora_em_brasilia
from app.domain.enums import SituacaoConexao
from app.domain.erros import PluggyCredenciaisInvalidas, PluggyIndisponivel
from app.domain.pluggy import CartaoPluggy, ConexaoPluggy, TransacaoPluggy

URL_BASE = "https://api.pluggy.ai"
TIMEOUT_SEGUNDOS = 30.0

# A `apiKey` vale 2 h; renovada com 1 h 50 min de idade (`02` §11.3).
IDADE_MAXIMA_DA_CHAVE_SEGUNDOS = 110 * 60

TENTATIVAS = 4
ESPERA_MAXIMA_SEGUNDOS = 16.0
CABECALHO_DE_ESPERA = "RateLimit-Reset"  # segundos até a cota zerar

DIAS_DE_AVISO_DA_VALIDADE = 30
# Trava contra um cursor que nunca termina: 200 páginas de 500 = 100 mil transações.
PAGINAS_MAXIMAS = 200

logger = logging.getLogger(__name__)


class _FalhaTransitoria(Exception):
    """429, 5xx, timeout ou erro de rede: vale tentar de novo (`02` §11.5)."""


class PluggyClient:
    """Uma instância por processo: guarda a `apiKey` em memória entre as chamadas."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        transporte: httpx.BaseTransport | None = None,
        dormir: Callable[[float], None] = time.sleep,
        relogio: Callable[[], float] = time.monotonic,
        agora: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._http = httpx.Client(base_url=URL_BASE, timeout=TIMEOUT_SEGUNDOS, transport=transporte)
        self._dormir = dormir
        self._relogio = relogio
        self._agora = agora
        self._chave: str | None = None
        self._chave_obtida_em = 0.0
        self._trava_da_chave = threading.Lock()

    # Leituras (`FontePluggy`) ------------------------------------------------

    def obter_conexao(self, item_id: str) -> ConexaoPluggy:
        """Situação da conexão pela tabela de `02` §11.4; inexistente não é erro (RN-24)."""
        item = self._obter(f"/items/{item_id}", aceitar_404=True)
        if item is None:
            return ConexaoPluggy(item_id=item_id, situacao=SituacaoConexao.NAO_ENCONTRADA)
        conector = item.get("connector")
        expira = _instante(item.get("consentExpiresAt"), obrigatorio=False)
        atualizada = _instante(item.get("lastUpdatedAt"), obrigatorio=False)
        agora = self._agora()
        return ConexaoPluggy(
            item_id=item_id,
            situacao=_situacao(item, expira, agora),
            banco=_texto(conector.get("name")) if isinstance(conector, dict) else None,
            ultima_atualizacao=hora_em_brasilia(atualizada) if atualizada else None,
            autorizacao_expira_em=data_em_brasilia(expira) if expira else None,
            aviso_validade=(
                expira is not None and expira - agora <= timedelta(days=DIAS_DE_AVISO_DA_VALIDADE)
            ),
        )

    def listar_cartoes(self, item_id: str) -> list[CartaoPluggy]:
        """Contas `CREDIT_CARD` da conexão, de todas as páginas."""
        cartoes: list[CartaoPluggy] = []
        pagina = 1
        while True:
            corpo = self._obter(
                "/accounts", params={"itemId": item_id, "type": "CREDIT", "page": pagina}
            )
            for conta in _resultados(corpo):
                if conta.get("subtype") == "CREDIT_CARD":
                    cartoes.append(
                        CartaoPluggy(
                            id=_obrigatorio(conta, "id"),
                            nome=_texto(conta.get("name")) or "Cartão",
                            final=_final(conta.get("number")),
                        )
                    )
            total = corpo.get("totalPages")
            if not isinstance(total, int) or pagina >= total or pagina >= PAGINAS_MAXIMAS:
                return cartoes
            pagina += 1

    def listar_transacoes(self, conta_id: str, desde: date) -> list[TransacaoPluggy]:
        """Transações do cartão a partir de `desde`, sem data final (RN-23).

        Paginação por cursor de `GET /v2/transactions`: o `next` de cada página é
        a query string da seguinte, usada como veio, até vir `null`.
        """
        transacoes: list[TransacaoPluggy] = []
        caminho = "/v2/transactions"
        params: dict[str, Any] | None = {"accountId": conta_id, "dateFrom": desde.isoformat()}
        cursores: set[str] = set()
        while True:
            corpo = self._obter(caminho, params=params)
            transacoes.extend(_transacao(item) for item in _resultados(corpo))
            proxima = corpo.get("next")
            if proxima is None:
                return transacoes
            if not isinstance(proxima, str) or not proxima.startswith("?"):
                logger.error("Pluggy: cursor fora do formato esperado em /v2/transactions")
                raise PluggyIndisponivel()
            if proxima in cursores or len(cursores) >= PAGINAS_MAXIMAS:
                logger.error("Pluggy: paginação de /v2/transactions não termina")
                raise PluggyIndisponivel()
            cursores.add(proxima)
            caminho, params = f"/v2/transactions{proxima}", None

    def fechar(self) -> None:
        self._http.close()

    # Autenticação ------------------------------------------------------------

    def _chave_valida(self) -> str:
        """`apiKey` em memória; pedida na primeira necessidade e renovada antes de vencer."""
        with self._trava_da_chave:
            idade = self._relogio() - self._chave_obtida_em
            if self._chave is None or idade >= IDADE_MAXIMA_DA_CHAVE_SEGUNDOS:
                self._chave = self._autenticar()
                self._chave_obtida_em = self._relogio()
            return self._chave

    def _esquecer_chave(self, chave: str) -> None:
        with self._trava_da_chave:
            if self._chave == chave:  # outra requisição pode já ter renovado
                self._chave = None

    def _autenticar(self) -> str:
        resposta = self._enviar(
            "POST",
            "/auth",
            json={"clientId": self._client_id, "clientSecret": self._client_secret},
        )
        if resposta.status_code in (401, 403):
            logger.error("Pluggy recusou as credenciais (POST /auth → %d)", resposta.status_code)
            raise PluggyCredenciaisInvalidas()
        # O corpo de `/auth` nunca vai para o log: é onde a `apiKey` vem.
        chave = _json(resposta, "/auth").get("apiKey") if resposta.is_success else None
        if not isinstance(chave, str) or not chave:
            logger.error("Pluggy: POST /auth → %d sem apiKey", resposta.status_code)
            raise PluggyIndisponivel()
        return chave

    # HTTP --------------------------------------------------------------------

    def _obter(
        self, caminho: str, *, params: dict[str, Any] | None = None, aceitar_404: bool = False
    ) -> Any:
        """`GET` autenticado; um `401` renova a `apiKey` **uma** vez e repete."""
        rota = caminho.split("?")[0]
        resposta: httpx.Response | None = None
        for _ in range(2):
            chave = self._chave_valida()
            resposta = self._enviar("GET", caminho, params=params, chave=chave)
            if resposta.status_code != 401:
                break
            self._esquecer_chave(chave)
        assert resposta is not None
        if aceitar_404 and resposta.status_code == 404:
            return None
        if not resposta.is_success:
            logger.error("Pluggy: GET %s → %d", rota, resposta.status_code)
            raise PluggyIndisponivel()
        return _json(resposta, rota)

    def _enviar(
        self,
        metodo: str,
        caminho: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        chave: str | None = None,
    ) -> httpx.Response:
        """Envia com até 4 tentativas para 429, 5xx, timeout e erro de rede (`02` §11.5)."""
        rota = caminho.split("?")[0]
        cabecalhos = {"X-API-KEY": chave} if chave else None
        for tentativa in range(1, TENTATIVAS + 1):
            espera_pedida: str | None = None
            try:
                resposta = self._http.request(
                    metodo, caminho, params=params, json=json, headers=cabecalhos
                )
                if resposta.status_code != 429 and resposta.status_code < 500:
                    return resposta
                motivo = str(resposta.status_code)
                espera_pedida = resposta.headers.get(CABECALHO_DE_ESPERA)
            except httpx.TransportError as erro:
                # Só o tipo do erro: a mensagem do httpx pode citar a requisição.
                motivo = type(erro).__name__
            if tentativa == TENTATIVAS:
                logger.error(
                    "Pluggy: %s %s falhou em %d tentativas (%s)", metodo, rota, TENTATIVAS, motivo
                )
                raise PluggyIndisponivel()
            espera = calcular_espera(tentativa, espera_pedida)
            logger.warning(
                "Pluggy: %s %s falhou (%s; tentativa %d de %d); nova tentativa em %.1fs",
                metodo,
                rota,
                motivo,
                tentativa,
                TENTATIVAS,
                espera,
            )
            self._dormir(espera)
        raise AssertionError("inalcançável: o laço sempre retorna ou levanta")


def calcular_espera(falhas: int, espera_pedida: str | None = None) -> float:
    """`min(RateLimit-Reset (se vier), 2^n + aleatório(0–1 s), 16 s)` (`02` §11.5)."""
    espera = min(2.0**falhas + random.random(), ESPERA_MAXIMA_SEGUNDOS)
    try:
        pedida = float(espera_pedida) if espera_pedida is not None else None
    except ValueError:
        pedida = None
    if pedida is not None and pedida >= 0:
        espera = min(espera, pedida)
    return espera


# Interpretação das respostas ----------------------------------------------------


def _situacao(item: dict[str, Any], expira: datetime | None, agora: datetime) -> SituacaoConexao:
    """Condições de `02` §11.4, avaliadas na ordem da tabela."""
    if expira is not None and expira <= agora:
        return SituacaoConexao.AUTORIZACAO_VENCIDA
    status = item.get("status")
    if status == "LOGIN_ERROR":
        return SituacaoConexao.ERRO_LOGIN
    if status == "OUTDATED":
        return SituacaoConexao.DESATUALIZADA
    if status in ("UPDATING", "WAITING_USER_INPUT"):
        return SituacaoConexao.ATUALIZANDO
    if status == "UPDATED":
        if item.get("executionStatus") == "PARTIAL_SUCCESS":
            return SituacaoConexao.PARCIAL
        return SituacaoConexao.OK
    # Status que a tabela não prevê: segue com os dados que a Pluggy já tem.
    logger.warning("Pluggy: status de item desconhecido (%s); tratado como desatualizado", status)
    return SituacaoConexao.DESATUALIZADA


def _transacao(item: Any) -> TransacaoPluggy:
    if not isinstance(item, dict):
        raise _fora_do_formato("transação")
    instante = _instante(item.get("date"), obrigatorio=True)
    assert instante is not None
    valor = _decimal(item.get("amount"))
    if valor is None:
        raise _fora_do_formato("transação sem amount")
    cartao = item.get("creditCardMetadata")
    cartao = cartao if isinstance(cartao, dict) else {}
    return TransacaoPluggy(
        id=_obrigatorio(item, "id"),
        instante=instante,
        valor=valor,
        descricao=_texto(item.get("description")) or "",
        provider_id=_texto(item.get("providerId")),
        valor_na_moeda_da_conta=_decimal(item.get("amountInAccountCurrency")),
        moeda=_texto(item.get("currencyCode")),
        tipo_operacao=_texto(item.get("operationType")),
        status=_texto(item.get("status")) or "POSTED",
        parcela_numero=_inteiro(cartao.get("installmentNumber")),
        parcela_total=_inteiro(cartao.get("totalInstallments")),
    )


def _fora_do_formato(o_que: str) -> PluggyIndisponivel:
    """Resposta que o app não sabe ler (`02` §11.6); o detalhe fica só no log."""
    logger.error("Pluggy: resposta fora do formato esperado (%s)", o_que)
    return PluggyIndisponivel()


def _json(resposta: httpx.Response, rota: str) -> Any:
    try:
        corpo = resposta.json()
    except ValueError as erro:
        raise _fora_do_formato(f"{rota} não devolveu JSON") from erro
    if not isinstance(corpo, dict):
        raise _fora_do_formato(f"{rota} não devolveu um objeto")
    return corpo


def _resultados(corpo: dict[str, Any]) -> list[dict[str, Any]]:
    resultados = corpo.get("results")
    if not isinstance(resultados, list):
        raise _fora_do_formato("lista sem results")
    return resultados


def _obrigatorio(item: dict[str, Any], campo: str) -> str:
    valor = _texto(item.get(campo))
    if valor is None:
        raise _fora_do_formato(f"registro sem {campo}")
    return valor


def _texto(valor: Any) -> str | None:
    """Texto aparado; vazio, ausente ou de outro tipo → `None`."""
    return (valor.strip() or None) if isinstance(valor, str) else None


def _inteiro(valor: Any) -> int | None:
    if isinstance(valor, bool) or not isinstance(valor, int | float) or valor != int(valor):
        return None
    return int(valor)


def _decimal(valor: Any) -> Decimal | None:
    """Número do JSON → `Decimal` pelo texto, sem o erro binário do `float`."""
    if isinstance(valor, bool) or not isinstance(valor, int | float | str):
        return None
    try:
        numero = Decimal(str(valor))
    except InvalidOperation:
        return None
    return numero if numero.is_finite() else None


def _instante(valor: Any, *, obrigatorio: bool) -> datetime | None:
    """Data ISO 8601 da Pluggy (UTC); sem fuso declarado, vale UTC."""
    if isinstance(valor, str) and valor.strip():
        try:
            instante = datetime.fromisoformat(valor.strip())
        except ValueError:
            instante = None
        if instante is not None:
            return instante if instante.tzinfo else instante.replace(tzinfo=UTC)
    if obrigatorio or valor not in (None, ""):
        raise _fora_do_formato("data inválida")
    return None


def _final(numero: Any) -> str | None:
    """4 últimos dígitos do número do cartão, como texto (`"0123"` fica `"0123"`)."""
    digitos = "".join(caractere for caractere in str(numero or "") if caractere.isdigit())
    return digitos[-4:] or None
