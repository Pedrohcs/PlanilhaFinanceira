"""Testes do cliente da planilha (CA-F02.1 a .4, .11, .14).

Tudo com dublês: nenhuma chamada real ao Google, e o `credentials.json` do
projeto nunca é aberto — cada teste usa um arquivo falso em `tmp_path`.
"""

import json
import logging
from pathlib import Path
from typing import Any

import pytest
from google.auth.exceptions import TransportError
from gspread.exceptions import APIError, SpreadsheetNotFound

from app.domain.erros import (
    ApiSheetsDesabilitada,
    CredenciaisInvalidas,
    ErroPlanilha,
    PlanilhaIndisponivel,
    PlanilhaNaoEncontrada,
    SemPermissaoPlanilha,
)
from app.infra import sheets_client
from app.infra.sheets_client import (
    ESCOPOS,
    abrir_planilha,
    calcular_espera,
    executar_com_retry,
    obter_client_email,
    traduzir_erro,
)

EMAIL_SERVICO = "robo-financeiro@projeto-falso.iam.gserviceaccount.com"
CHAVE_FALSA = "-----BEGIN PRIVATE KEY-----\nCHAVE-FALSA-SO-DE-TESTE\n-----END PRIVATE KEY-----\n"
ID_PLANILHA = "1IdDePlanilhaDeTeste"
TITULO = "Planilha Financeira"


class RespostaFalsa:
    """Mínimo que `APIError` precisa: `.json()` e `.text`."""

    def __init__(self, corpo: dict[str, Any]) -> None:
        self._corpo = corpo
        self.text = json.dumps(corpo)
        self.status_code = int(corpo.get("error", {}).get("code", 0))

    def json(self) -> dict[str, Any]:
        return self._corpo


def erro_api(codigo: int, *, motivo: str | None = None, status: str = "") -> APIError:
    """Monta um `APIError` como o que o Google devolveria."""
    erro: dict[str, Any] = {"code": codigo, "message": "falha simulada", "status": status}
    if motivo:
        erro["errors"] = [{"reason": motivo, "message": "falha simulada"}]
    return APIError(RespostaFalsa({"error": erro}))


@pytest.fixture
def credencial_falsa(tmp_path: Path) -> Path:
    """Arquivo de credencial fictício — nunca o real do projeto."""
    caminho = tmp_path / "credencial-falsa.json"
    caminho.write_text(
        json.dumps(
            {
                "type": "service_account",
                "project_id": "projeto-falso",
                "private_key": CHAVE_FALSA,
                "client_email": EMAIL_SERVICO,
            }
        ),
        encoding="utf-8",
    )
    return caminho


class DocumentoFalso:
    def __init__(self, titulo: str = TITULO) -> None:
        self.title = titulo


class ClienteFalso:
    """Dublê de `gspread.Client`, registrando como foi chamado."""

    def __init__(self, *, resultado: Any = None, erros: list[Exception] | None = None) -> None:
        self.resultado = resultado if resultado is not None else DocumentoFalso()
        self.erros = list(erros or [])
        self.ids_abertos: list[str] = []
        self.nomes_abertos: list[str] = []

    def open_by_key(self, chave: str) -> Any:
        self.ids_abertos.append(chave)
        if self.erros:
            raise self.erros.pop(0)
        return self.resultado

    def open(self, titulo: str) -> Any:  # pragma: no cover - não deve ser chamado
        self.nomes_abertos.append(titulo)
        raise AssertionError("abrir por nome é proibido (SPECS/02 §5.2)")


@pytest.fixture
def gspread_falso(monkeypatch: pytest.MonkeyPatch) -> ClienteFalso:
    """Substitui `gspread.authorize` e a carga de credenciais."""
    cliente = ClienteFalso()
    chamadas: dict[str, Any] = {}

    def authorize_falso(credenciais: Any) -> ClienteFalso:
        chamadas["credenciais"] = credenciais
        return cliente

    class CredenciaisFalsas:
        @staticmethod
        def from_service_account_file(caminho: str, scopes: list[str]) -> str:
            chamadas["caminho"] = caminho
            chamadas["scopes"] = scopes
            return "credencial-carregada"

    monkeypatch.setattr(sheets_client.gspread, "authorize", authorize_falso)
    monkeypatch.setattr(sheets_client, "Credentials", CredenciaisFalsas)
    cliente.chamadas = chamadas  # type: ignore[attr-defined]
    return cliente


def nao_dormir(_segundos: float) -> None:
    """Substitui `time.sleep` para o teste não esperar de verdade."""


# --------------------------------------------------------------------------- #
# CA-F02.1 — credencial, escopos e abertura por ID
# --------------------------------------------------------------------------- #


def test_usa_from_service_account_file_e_escopos__CA_F02_1(
    credencial_falsa: Path, gspread_falso: ClienteFalso
) -> None:
    abrir_planilha(credencial_falsa, ID_PLANILHA, dormir=nao_dormir)

    chamadas = gspread_falso.chamadas  # type: ignore[attr-defined]
    assert chamadas["caminho"] == str(credencial_falsa)
    assert chamadas["scopes"] == [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    assert chamadas["scopes"] == ESCOPOS


def test_abre_por_id_e_nao_por_nome__CA_F02_1(
    credencial_falsa: Path, gspread_falso: ClienteFalso
) -> None:
    planilha = abrir_planilha(credencial_falsa, ID_PLANILHA, dormir=nao_dormir)

    assert gspread_falso.ids_abertos == [ID_PLANILHA]
    assert gspread_falso.nomes_abertos == []
    assert planilha.titulo == TITULO


# --------------------------------------------------------------------------- #
# CA-F02.2 / CA-F02.3 — retry
# --------------------------------------------------------------------------- #


def test_retenta_ate_quatro_vezes_no_429__CA_F02_2() -> None:
    tentativas: list[int] = []

    def operacao() -> None:
        tentativas.append(1)
        raise erro_api(429)

    with pytest.raises(PlanilhaIndisponivel):
        executar_com_retry(operacao, dormir=nao_dormir)

    assert len(tentativas) == 4


def test_sucesso_na_terceira_tentativa__CA_F02_2() -> None:
    erros = [erro_api(429), erro_api(503)]

    def operacao() -> str:
        if erros:
            raise erros.pop(0)
        return "pronto"

    assert executar_com_retry(operacao, dormir=nao_dormir) == "pronto"


def test_espera_cresce_e_tem_teto_de_16s__CA_F02_2() -> None:
    esperas: list[float] = []

    def operacao() -> None:
        raise erro_api(500)

    with pytest.raises(PlanilhaIndisponivel):
        executar_com_retry(operacao, dormir=esperas.append)

    assert len(esperas) == 3
    assert 2 <= esperas[0] < 3
    assert 4 <= esperas[1] < 5
    assert 8 <= esperas[2] < 9
    assert esperas == sorted(esperas)
    assert all(espera <= 16 for espera in esperas)
    assert calcular_espera(10) == 16.0


@pytest.mark.parametrize(
    ("erro", "esperada"),
    [
        (erro_api(403), SemPermissaoPlanilha),
        (erro_api(404), PlanilhaNaoEncontrada),
        (erro_api(400), ErroPlanilha),
    ],
)
def test_nao_retenta_403_e_404__CA_F02_3(erro: APIError, esperada: type[Exception]) -> None:
    tentativas: list[int] = []

    def operacao() -> None:
        tentativas.append(1)
        raise erro

    with pytest.raises(esperada):
        executar_com_retry(operacao, dormir=nao_dormir)

    assert len(tentativas) == 1


def test_erro_inesperado_sobe_intacto_sem_retry__CA_F02_3() -> None:
    tentativas: list[int] = []

    def operacao() -> None:
        tentativas.append(1)
        raise ZeroDivisionError("defeito nosso")

    with pytest.raises(ZeroDivisionError):
        executar_com_retry(operacao, dormir=nao_dormir)

    assert len(tentativas) == 1


# --------------------------------------------------------------------------- #
# CA-F02.4 / CA-F02.14 — tradução de cada linha de SPECS/02 §5.6
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("erro", "esperada", "trecho"),
    [
        (erro_api(403), SemPermissaoPlanilha, "como Editor"),
        (erro_api(404), PlanilhaNaoEncontrada, "Confira SPREADSHEET_ID"),
        (SpreadsheetNotFound(), PlanilhaNaoEncontrada, "Confira SPREADSHEET_ID"),
        (erro_api(429), PlanilhaIndisponivel, "indisponível"),
        (erro_api(503), PlanilhaIndisponivel, "indisponível"),
        (TransportError("sem rede"), PlanilhaIndisponivel, "indisponível"),
        (ConnectionError("sem rede"), PlanilhaIndisponivel, "indisponível"),
    ],
)
def test_traduz_cada_erro_do_google__CA_F02_4(
    erro: Exception, esperada: type[ErroPlanilha], trecho: str
) -> None:
    traduzido = traduzir_erro(erro)

    assert type(traduzido) is esperada
    assert trecho in traduzido.mensagem


def test_403_de_api_desativada_vira_excecao_propria__CA_F02_14() -> None:
    desabilitada = traduzir_erro(erro_api(403, motivo="SERVICE_DISABLED"))
    nao_configurada = traduzir_erro(erro_api(403, motivo="accessNotConfigured"))
    sem_permissao = traduzir_erro(erro_api(403, motivo="forbidden"))

    assert type(desabilitada) is ApiSheetsDesabilitada
    assert "Ative a Google Sheets API" in desabilitada.mensagem
    assert type(nao_configurada) is ApiSheetsDesabilitada
    assert type(sem_permissao) is SemPermissaoPlanilha


def test_mensagem_de_403_nomeia_a_conta_de_servico__CA_16_1(credencial_falsa: Path) -> None:
    erro = traduzir_erro(erro_api(403), client_email=obter_client_email(credencial_falsa))

    assert isinstance(erro, SemPermissaoPlanilha)
    assert EMAIL_SERVICO in erro.mensagem
    assert "como Editor" in erro.mensagem


def test_credencial_ausente_e_invalida__CA_F02_4(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ausente = tmp_path / "nao-existe.json"
    with pytest.raises(CredenciaisInvalidas) as erro:
        abrir_planilha(ausente, ID_PLANILHA, dormir=nao_dormir)
    assert "credenciais" in erro.value.mensagem.lower()

    invalida = tmp_path / "invalida.json"
    invalida.write_text("isto nao e json", encoding="utf-8")
    with pytest.raises(CredenciaisInvalidas):
        abrir_planilha(invalida, ID_PLANILHA, dormir=nao_dormir)

    assert obter_client_email(ausente) is None
    assert obter_client_email(invalida) is None


# --------------------------------------------------------------------------- #
# CA-F02.11 — nada da credencial em log nem em mensagem
# --------------------------------------------------------------------------- #


def test_nao_loga_conteudo_da_credencial__CA_F02_11(
    credencial_falsa: Path,
    gspread_falso: ClienteFalso,
    caplog: pytest.LogCaptureFixture,
) -> None:
    gspread_falso.erros = [erro_api(429), erro_api(403)]

    with caplog.at_level(logging.DEBUG), pytest.raises(SemPermissaoPlanilha) as erro:
        abrir_planilha(credencial_falsa, ID_PLANILHA, dormir=nao_dormir)

    registrado = caplog.text
    assert "CHAVE-FALSA-SO-DE-TESTE" not in registrado
    assert "private_key" not in registrado
    assert "BEGIN PRIVATE KEY" not in registrado
    assert "CHAVE-FALSA-SO-DE-TESTE" not in erro.value.mensagem
    # O client_email é o único campo que pode aparecer (Q2 de F-02).
    assert EMAIL_SERVICO in erro.value.mensagem
    # E o retry avisou antes de desistir.
    assert "tentativa 1 de 4" in registrado
