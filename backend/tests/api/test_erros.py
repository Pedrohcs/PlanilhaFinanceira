"""Testes dos handlers de erro (CA-F02.5, CA-F02.6, CA-F02.7).

As rotas abaixo existem só no teste: levantam de propósito para exercitar
cada handler registrado por `criar_app`.
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.domain.erros import SemPermissaoPlanilha
from app.main import criar_app

EMAIL_SERVICO = "robo-financeiro@projeto-falso.iam.gserviceaccount.com"


class EntradaFalsa(BaseModel):
    valor: int
    descricao: str


@pytest.fixture
def cliente_com_rotas_de_erro() -> TestClient:
    """Aplicação real, com rotas extras que falham de formas conhecidas."""
    app = criar_app()

    @app.get("/api/_teste/erro-de-planilha")
    def erro_de_planilha() -> None:
        raise SemPermissaoPlanilha.para(EMAIL_SERVICO)

    @app.get("/api/_teste/defeito")
    def defeito() -> None:
        raise ZeroDivisionError("defeito proposital")

    @app.post("/api/_teste/entrada")
    def entrada(dados: EntradaFalsa) -> dict[str, int]:
        return {"valor": dados.valor}

    return TestClient(app, raise_server_exceptions=False)


def test_formato_de_erro_503__CA_F02_5(cliente_com_rotas_de_erro: TestClient) -> None:
    resposta = cliente_com_rotas_de_erro.get("/api/_teste/erro-de-planilha")

    assert resposta.status_code == 503
    assert resposta.json() == {
        "erro": {
            "codigo": "SEM_PERMISSAO_PLANILHA",
            "mensagem": f"Compartilhe a planilha com {EMAIL_SERVICO} como Editor.",
            "detalhes": [],
        }
    }


def test_validacao_pydantic_vira_422__CA_F02_6(
    cliente_com_rotas_de_erro: TestClient,
) -> None:
    resposta = cliente_com_rotas_de_erro.post("/api/_teste/entrada", json={"valor": "nao-e-numero"})

    assert resposta.status_code == 422
    erro = resposta.json()["erro"]
    assert erro["codigo"] == "VALIDACAO"
    campos = {detalhe["campo"] for detalhe in erro["detalhes"]}
    assert campos == {"valor", "descricao"}
    assert all(detalhe["mensagem"] for detalhe in erro["detalhes"])


def test_excecao_inesperada_vira_500_generico__CA_F02_7(
    cliente_com_rotas_de_erro: TestClient,
) -> None:
    resposta = cliente_com_rotas_de_erro.get("/api/_teste/defeito")

    assert resposta.status_code == 500
    erro = resposta.json()["erro"]
    assert erro["codigo"] == "ERRO_INTERNO"
    # Mensagem genérica: nem a exceção original nem caminho de arquivo aparecem.
    assert "defeito proposital" not in resposta.text
    assert "ZeroDivisionError" not in resposta.text
    assert "Traceback" not in resposta.text
    assert ".py" not in resposta.text


def test_rota_inexistente_usa_o_envelope_padrao__CA_F02_5(
    cliente_com_rotas_de_erro: TestClient,
) -> None:
    """Erro do próprio framework também sai no formato de `SPECS/03` §6.2."""
    resposta = cliente_com_rotas_de_erro.get("/api/nao-existe")

    assert resposta.status_code == 404
    assert resposta.json() == {
        "erro": {
            "codigo": "NAO_ENCONTRADO",
            "mensagem": "Recurso não encontrado.",
            "detalhes": [],
        }
    }
