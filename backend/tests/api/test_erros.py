"""Testes dos handlers de erro (CA-F02.5, CA-F02.6, CA-F02.7).

As rotas abaixo existem só no teste: levantam de propósito para exercitar
cada handler registrado por `criar_app`.
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.domain.erros import ErroValidacao, SemPermissaoPlanilha
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

    @app.get("/api/_teste/regra-no-campo")
    def regra_no_campo() -> None:
        raise ErroValidacao.no_campo("forma_pagamento", "Informe a forma de pagamento.")

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


def test_erro_de_dominio_leva_detalhes__F06_3_4(cliente_com_rotas_de_erro: TestClient) -> None:
    """Regra de negócio violada num campo: o formulário sabe qual campo marcar (T-015)."""
    resposta = cliente_com_rotas_de_erro.get("/api/_teste/regra-no-campo")

    assert resposta.status_code == 422
    assert resposta.json() == {
        "erro": {
            "codigo": "VALIDACAO",
            "mensagem": "Informe a forma de pagamento.",
            "detalhes": [{"campo": "forma_pagamento", "mensagem": "Informe a forma de pagamento."}],
        }
    }


LANCAMENTO = {
    "data": "2026-09-29",
    "tipo": "GASTO",
    "descricao": "Almoço",
    "valor": 42.5,
    "categoria_id": "mercado",
    "forma_pagamento": "PIX",
}
RECORRENCIA = {
    "tipo": "GASTO",
    "descricao": "Aluguel",
    "valor": 1500,
    "categoria_id": "moradia",
    "forma_pagamento": "PIX",
    "dia_do_mes": 5,
    "mes_inicio": "2026-09",
}
PARCELAMENTO = {
    "data": "2026-09-29",
    "descricao": "Geladeira",
    "valor_total": 3000,
    "parcelas": 10,
    "categoria_id": "casa",
    "forma_pagamento": "CREDITO",
}


def sem(dados: dict[str, object], campo: str) -> dict[str, object]:
    return {chave: valor for chave, valor in dados.items() if chave != campo}


@pytest.mark.parametrize(
    ("caminho", "corpo", "campo", "mensagem"),
    [
        (
            "/api/recorrencias",
            RECORRENCIA | {"dia_do_mes": 32},
            "dia_do_mes",
            "Deve ser no máximo 31.",
        ),
        (
            "/api/lancamentos",
            LANCAMENTO | {"valor": 1.005},
            "valor",
            "Use no máximo 2 casas decimais.",
        ),
        ("/api/lancamentos", LANCAMENTO | {"descricao": ""}, "descricao", "Texto obrigatório."),
        (
            "/api/recorrencias",
            RECORRENCIA | {"mes_inicio": "julho"},
            "mes_inicio",
            "Formato inválido.",
        ),
        ("/api/lancamentos", sem(LANCAMENTO, "data"), "data", "Campo obrigatório."),
        ("/api/lancamentos", LANCAMENTO | {"valor": 0}, "valor", "Deve ser maior que 0."),
        ("/api/parcelamentos", PARCELAMENTO | {"parcelas": 1}, "parcelas", "Deve ser no mínimo 2."),
        (
            "/api/lancamentos",
            LANCAMENTO | {"descricao": "a" * 101},
            "descricao",
            "Use no máximo 100 caracteres.",
        ),
        (
            "/api/lancamentos",
            LANCAMENTO | {"valor": 10_000_000_000},
            "valor",
            "Valor acima do máximo permitido.",
        ),
        ("/api/lancamentos", LANCAMENTO | {"valor": "abc"}, "valor", "Número inválido."),
        ("/api/recorrencias", RECORRENCIA | {"dia_do_mes": 1.5}, "dia_do_mes", "Número inválido."),
        ("/api/lancamentos", LANCAMENTO | {"data": "2026-02-30"}, "data", "Data inválida."),
        (
            "/api/lancamentos",
            LANCAMENTO | {"data": "29/09/2026"},
            "data",
            "Data deve estar no formato AAAA-MM-DD.",
        ),
        ("/api/lancamentos", LANCAMENTO | {"tipo": "DOACAO"}, "tipo", "Valor não permitido."),
        ("/api/lancamentos", LANCAMENTO | {"descricao": 3}, "descricao", "Valor inválido."),
    ],
)
def test_mensagens_pydantic_em_ptbr__CA_F14_14(
    cliente: TestClient, caminho: str, corpo: dict[str, object], campo: str, mensagem: str
) -> None:
    """F-14 §3.5: `codigo`, mensagem geral e `campo` não mudam; o texto do campo sai em pt-BR."""
    resposta = cliente.post(caminho, json=corpo)

    assert resposta.status_code == 422
    erro = resposta.json()["erro"]
    assert erro["codigo"] == "VALIDACAO"
    assert erro["mensagem"] == "Dados inválidos."
    assert erro["detalhes"] == [{"campo": campo, "mensagem": mensagem}]


def test_mensagem_de_parametro_de_consulta_em_ptbr__CA_F14_14(cliente: TestClient) -> None:
    resposta = cliente.get("/api/lancamentos?mes=julho")

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["detalhes"] == [
        {"campo": "mes", "mensagem": "Formato inválido."}
    ]
