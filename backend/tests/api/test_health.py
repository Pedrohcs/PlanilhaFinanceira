"""Testes de `GET /api/health` (CA-16.1, CA-16.2, CA-F02.8, CA-F02.9)."""

import pytest
from fastapi.testclient import TestClient

from app.domain.erros import (
    ApiSheetsDesabilitada,
    CredenciaisInvalidas,
    ErroPlanilha,
    PlanilhaIndisponivel,
    PlanilhaNaoEncontrada,
    SemPermissaoPlanilha,
)
from app.infra.sheets_client import PlanilhaAberta
from app.main import criar_app

TITULO = "Planilha Financeira do Pedro"
EMAIL_SERVICO = "robo-financeiro@projeto-falso.iam.gserviceaccount.com"


class ConexaoFalsa:
    """Dublê de `ConexaoPlanilha`, contando as tentativas de conexão."""

    def __init__(self, *, erro: ErroPlanilha | None = None, titulo: str = TITULO) -> None:
        self._erro = erro
        self._titulo = titulo
        self._planilha: PlanilhaAberta | None = None
        self.tentativas = 0

    @property
    def planilha(self) -> PlanilhaAberta | None:
        return self._planilha

    @property
    def erro(self) -> ErroPlanilha | None:
        return self._erro

    @property
    def conectada(self) -> bool:
        return self._planilha is not None

    def definir_erro(self, erro: ErroPlanilha | None) -> None:
        """Simula a causa da falha sendo corrigida (ou aparecendo)."""
        self._erro = erro

    def conectar(self) -> PlanilhaAberta | None:
        if self._planilha is not None:
            return self._planilha
        self.tentativas += 1
        if self._erro is not None:
            return None
        self._planilha = PlanilhaAberta(titulo=self._titulo, documento=object())
        return self._planilha


def cliente_com(conexao: ConexaoFalsa) -> TestClient:
    """Cliente sobre uma aplicação com a conexão injetada (lifespan incluído)."""
    return TestClient(criar_app(conexao=conexao))


def test_health_ok_com_titulo__CA_F02_8() -> None:
    with cliente_com(ConexaoFalsa()) as cliente:
        resposta = cliente.get("/api/health")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "status": "ok",
        "planilha": {"ok": True, "titulo": TITULO, "erro": None},
    }


@pytest.mark.parametrize(
    ("erro", "codigo"),
    [
        (CredenciaisInvalidas(), "CREDENCIAIS_INVALIDAS"),
        (SemPermissaoPlanilha.para(EMAIL_SERVICO), "SEM_PERMISSAO_PLANILHA"),
        (ApiSheetsDesabilitada(), "API_SHEETS_DESABILITADA"),
        (PlanilhaNaoEncontrada(), "PLANILHA_NAO_ENCONTRADA"),
        (PlanilhaIndisponivel(), "PLANILHA_INDISPONIVEL"),
    ],
)
def test_health_200_com_planilha_inacessivel__CA_F02_9(erro: ErroPlanilha, codigo: str) -> None:
    with cliente_com(ConexaoFalsa(erro=erro)) as cliente:
        resposta = cliente.get("/api/health")

    assert resposta.status_code == 200, "health nunca devolve 503 (SPECS/03 §6.3)"
    corpo = resposta.json()
    assert corpo["status"] == "degradado"
    assert corpo["planilha"] == {
        "ok": False,
        "titulo": None,
        "erro": {"codigo": codigo, "mensagem": erro.mensagem},
    }


def test_health_sem_permissao_pede_compartilhar_como_editor__CA_16_1() -> None:
    conexao = ConexaoFalsa(erro=SemPermissaoPlanilha.para(EMAIL_SERVICO))

    with cliente_com(conexao) as cliente:
        resposta = cliente.get("/api/health")

    mensagem = resposta.json()["planilha"]["erro"]["mensagem"]
    assert EMAIL_SERVICO in mensagem
    assert "como Editor" in mensagem


def test_health_reconecta_sem_reiniciar__CA_16_2() -> None:
    conexao = ConexaoFalsa(erro=PlanilhaIndisponivel())

    with cliente_com(conexao) as cliente:
        primeira = cliente.get("/api/health").json()

        # Usuário corrige a causa (a internet voltou) e clica "Tentar novamente".
        conexao.definir_erro(None)
        segunda = cliente.get("/api/health").json()

    assert primeira["planilha"]["ok"] is False
    assert primeira["status"] == "degradado"
    assert segunda["planilha"]["ok"] is True
    assert segunda["status"] == "ok"
    assert segunda["planilha"]["titulo"] == TITULO


def test_health_nao_reautentica_quando_ja_conectado__CA_F02_8() -> None:
    conexao = ConexaoFalsa()

    with cliente_com(conexao) as cliente:
        cliente.get("/api/health")
        cliente.get("/api/health")
        cliente.get("/api/health")

    # Uma tentativa na subida (lifespan) e nenhuma repetição: a conexão é reusada.
    assert conexao.tentativas == 1
