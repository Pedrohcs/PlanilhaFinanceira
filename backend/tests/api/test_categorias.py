"""`/api/categorias` (REQ-11; `SPECS/03` §6.1–§6.3; F-05).

A maior parte usa repositórios em memória via `dependency_overrides` (`02` §8);
um teste percorre a composição real com a planilha falsa, e outro a falta de
conexão (503).
"""

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.deps import Repositorios, obter_repositorios
from app.domain.enums import FormaPagamento, TipoLancamento
from app.domain.modelos import Categoria, Lancamento
from app.infra import sheets_client
from app.infra.sheets_client import PlanilhaAberta
from app.main import criar_app
from app.repositories.memoria import (
    CategoriaRepositoryMemoria,
    LancamentoRepositoryMemoria,
    RecorrenciaRepositoryMemoria,
)
from tests.planilha_falsa import PlanilhaFalsa

CRIADO = datetime(2026, 9, 29, 10, 15)


def categoria(id_: str, nome: str, tipo: str = "GASTO", *, ativa: bool = True) -> Categoria:
    return Categoria(
        id=id_, nome=nome, tipo=TipoLancamento(tipo), cor="#E57373", ativa=ativa, criado_em=CRIADO
    )


def lancamento(categoria_id: str) -> Lancamento:
    return Lancamento(
        id="l1",
        data=date(2026, 9, 29),
        tipo=TipoLancamento.GASTO,
        descricao="Almoço",
        valor=Decimal("42.50"),
        categoria_id=categoria_id,
        forma_pagamento=FormaPagamento.PIX,
        criado_em=CRIADO,
        atualizado_em=CRIADO,
    )


@pytest.fixture
def repositorios() -> Repositorios:
    return Repositorios(
        categorias=CategoriaRepositoryMemoria(
            [
                categoria("mercado", "Mercado"),
                categoria("velha", "Velha", ativa=False),
                categoria("salario", "Salário", "RECEITA"),
            ]
        ),
        lancamentos=LancamentoRepositoryMemoria([lancamento("mercado")]),
        recorrencias=RecorrenciaRepositoryMemoria(),
    )


@pytest.fixture
def cliente_memoria(repositorios: Repositorios) -> Iterator[TestClient]:
    app = criar_app()
    app.dependency_overrides[obter_repositorios] = lambda: repositorios
    with TestClient(app) as cliente:
        yield cliente


def ids(resposta: Any) -> list[str]:
    return [item["id"] for item in resposta.json()]


def test_listar_filtra_tipo_e_inativas__CA_11_4(cliente_memoria: TestClient) -> None:
    """CA-F05.8: só ativas por padrão; `incluir_inativas`; `tipo`."""
    assert ids(cliente_memoria.get("/api/categorias")) == ["mercado", "salario"]
    assert ids(cliente_memoria.get("/api/categorias?incluir_inativas=true")) == [
        "mercado",
        "velha",
        "salario",
    ]
    assert ids(cliente_memoria.get("/api/categorias?tipo=GASTO")) == ["mercado"]
    assert ids(cliente_memoria.get("/api/categorias?tipo=RECEITA&incluir_inativas=true")) == [
        "salario"
    ]


def test_formato_da_resposta__CA_F05_13(cliente_memoria: TestClient) -> None:
    """CA-F05.13 e CA-F05.21: `snake_case`, enum em maiúsculas, booleanos, `em_uso`."""
    corpo = cliente_memoria.get("/api/categorias?incluir_inativas=true").json()

    assert corpo[0] == {
        "id": "mercado",
        "nome": "Mercado",
        "tipo": "GASTO",
        "cor": "#E57373",
        "ativa": True,
        "criado_em": "2026-09-29T10:15:00",
        "em_uso": True,
        "reservada": False,
    }
    assert [item["em_uso"] for item in corpo] == [True, False, False]


def test_criar_201_e_duplicada_409__CA_11_1(
    cliente_memoria: TestClient, repositorios: Repositorios
) -> None:
    criada = cliente_memoria.post(
        "/api/categorias", json={"nome": "  Pet   Shop ", "tipo": "GASTO", "cor": "#a1887f"}
    )
    assert criada.status_code == 201
    assert criada.json() | {"criado_em": None} == {
        "id": "pet-shop",
        "nome": "Pet Shop",
        "tipo": "GASTO",
        "cor": "#A1887F",
        "ativa": True,
        "criado_em": None,
        "em_uso": False,
        "reservada": False,
    }

    duplicada = cliente_memoria.post(
        "/api/categorias", json={"nome": "MÉRCADO", "tipo": "GASTO", "cor": "#FF8A65"}
    )
    assert duplicada.status_code == 409
    assert duplicada.json() == {
        "erro": {
            "codigo": "CATEGORIA_DUPLICADA",
            "mensagem": 'Já existe uma categoria de gasto chamada "MÉRCADO".',
            "detalhes": [],
        }
    }
    assert len(repositorios.categorias.listar().itens) == 4


def test_mesmo_nome_em_outro_tipo__CA_F05_2(cliente_memoria: TestClient) -> None:
    resposta = cliente_memoria.post(
        "/api/categorias", json={"nome": "Mercado", "tipo": "RECEITA", "cor": "#66BB6A"}
    )

    assert resposta.status_code == 201
    assert resposta.json()["id"] == "mercado-2"


def test_atualizar_renomeia_desativa_e_ignora_tipo__F05_3_3(cliente_memoria: TestClient) -> None:
    """CA-F05.9, borda 16: `tipo` no corpo é ignorado."""
    resposta = cliente_memoria.put(
        "/api/categorias/mercado",
        json={"nome": "Supermercado", "cor": "#FF8A65", "ativa": False, "tipo": "RECEITA"},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert (corpo["id"], corpo["nome"], corpo["tipo"], corpo["ativa"]) == (
        "mercado",
        "Supermercado",
        "GASTO",
        False,
    )
    assert corpo["em_uso"] is True
    assert "mercado" not in ids(cliente_memoria.get("/api/categorias"))


def test_renomear_para_duplicado_409__CA_11_1(cliente_memoria: TestClient) -> None:
    resposta = cliente_memoria.put(
        "/api/categorias/mercado", json={"nome": "velha", "cor": "#FF8A65", "ativa": True}
    )

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "CATEGORIA_DUPLICADA"


def test_excluir_em_uso_409__CA_11_3(cliente_memoria: TestClient) -> None:
    resposta = cliente_memoria.delete("/api/categorias/mercado")

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "CATEGORIA_EM_USO"
    assert "Desative-a" in resposta.json()["erro"]["mensagem"]
    assert "mercado" in ids(cliente_memoria.get("/api/categorias"))


def test_excluir_204__CA_F05_7(cliente_memoria: TestClient) -> None:
    resposta = cliente_memoria.delete("/api/categorias/velha")

    assert resposta.status_code == 204
    assert resposta.content == b""
    assert "velha" not in ids(cliente_memoria.get("/api/categorias?incluir_inativas=true"))


def test_reservada_nao_exclui_nem_desativa__RN_24(
    cliente_memoria: TestClient, repositorios: Repositorios
) -> None:
    """CA-11.5, CA-F16.7: 409 `CATEGORIA_RESERVADA`; renomear e trocar a cor continuam → 200."""
    repositorios.categorias.inserir([categoria("a-classificar", "A classificar")])
    corpo = {"nome": "A classificar", "cor": "#90A4AE", "ativa": True}

    excluir = cliente_memoria.delete("/api/categorias/a-classificar")
    desativar = cliente_memoria.put("/api/categorias/a-classificar", json=corpo | {"ativa": False})
    renomear = cliente_memoria.put(
        "/api/categorias/a-classificar", json=corpo | {"nome": "Revisar", "cor": "#123456"}
    )

    assert excluir.status_code == 409
    assert excluir.json()["erro"] == {
        "codigo": "CATEGORIA_RESERVADA",
        "mensagem": (
            'A categoria "A classificar" é usada pela importação dos cartões e não pode ser '
            "excluída."
        ),
        "detalhes": [],
    }
    assert desativar.status_code == 409
    assert desativar.json()["erro"]["codigo"] == "CATEGORIA_RESERVADA"
    assert desativar.json()["erro"]["mensagem"].endswith("não pode ser desativada.")
    assert renomear.status_code == 200
    assert renomear.json() | {"criado_em": None, "em_uso": None} == {
        "id": "a-classificar",
        "nome": "Revisar",
        "tipo": "GASTO",
        "cor": "#123456",
        "ativa": True,
        "criado_em": None,
        "em_uso": None,
        "reservada": True,
    }


@pytest.mark.parametrize(
    ("metodo", "caminho", "corpo"),
    [
        ("put", "/api/categorias/nao-existe", {"nome": "X", "cor": "#E57373", "ativa": True}),
        ("delete", "/api/categorias/nao-existe", None),
    ],
)
def test_id_inexistente_404__CA_F05_10(
    cliente_memoria: TestClient, metodo: str, caminho: str, corpo: dict[str, Any] | None
) -> None:
    resposta = cliente_memoria.request(metodo.upper(), caminho, json=corpo)

    assert resposta.status_code == 404
    assert resposta.json()["erro"] == {
        "codigo": "NAO_ENCONTRADO",
        "mensagem": "Categoria não encontrada.",
        "detalhes": [],
    }


@pytest.mark.parametrize(
    ("corpo", "campo"),
    [
        ({"nome": "Pet", "tipo": "GASTO", "cor": "red"}, "cor"),
        ({"nome": "Pet", "tipo": "GASTO", "cor": "#FFF"}, "cor"),
        ({"nome": "Pet", "tipo": "GASTO", "cor": "E57373"}, "cor"),
        ({"nome": "   ", "tipo": "GASTO", "cor": "#E57373"}, "nome"),
        ({"nome": "x" * 41, "tipo": "GASTO", "cor": "#E57373"}, "nome"),
        ({"nome": "Pet", "tipo": "DESPESA", "cor": "#E57373"}, "tipo"),
        ({"nome": "Pet", "tipo": "gasto", "cor": "#E57373"}, "tipo"),
        ({"tipo": "GASTO", "cor": "#E57373"}, "nome"),
    ],
)
def test_validacao_422__CA_F05_11(
    cliente_memoria: TestClient, corpo: dict[str, Any], campo: str
) -> None:
    """Bordas 7a, 15 e 17."""
    resposta = cliente_memoria.post("/api/categorias", json=corpo)

    assert resposta.status_code == 422
    erro = resposta.json()["erro"]
    assert erro["codigo"] == "VALIDACAO"
    assert [detalhe["campo"] for detalhe in erro["detalhes"]] == [campo]


def test_nome_com_40_caracteres_e_aceito__CA_F05_23(cliente_memoria: TestClient) -> None:
    """Borda 7a: o limite conta depois de normalizar os espaços."""
    nome = "x" * 20 + "   " + "y" * 19  # 42 caracteres digitados, 40 depois de normalizar

    resposta = cliente_memoria.post(
        "/api/categorias", json={"nome": nome, "tipo": "GASTO", "cor": "#E57373"}
    )

    assert resposta.status_code == 201
    assert len(resposta.json()["nome"]) == 40


def test_filtro_de_tipo_invalido_422__CA_F05_11(cliente_memoria: TestClient) -> None:
    for tipo in ("gasto", "OUTRO"):
        resposta = cliente_memoria.get(f"/api/categorias?tipo={tipo}")
        assert resposta.status_code == 422
        assert resposta.json()["erro"]["detalhes"][0]["campo"] == "tipo"


def test_planilha_inacessivel_503__CA_F05_12(cliente: TestClient) -> None:
    """App real: a credencial de teste não existe, então os endpoints dão 503 com a causa."""
    for resposta in (
        cliente.get("/api/categorias"),
        cliente.post("/api/categorias", json={"nome": "Pet", "tipo": "GASTO", "cor": "#E57373"}),
        cliente.delete("/api/categorias/pet"),
    ):
        assert resposta.status_code == 503
        assert resposta.json()["erro"]["codigo"] == "CREDENCIAIS_INVALIDAS"


def test_ponta_a_ponta_com_repositorio_de_planilha(monkeypatch: pytest.MonkeyPatch) -> None:
    """Composição real de `main.py`: bootstrap semeia, a API lista e grava na planilha."""
    documento = PlanilhaFalsa()
    monkeypatch.setattr(
        sheets_client,
        "abrir_planilha",
        lambda *_a, **_k: PlanilhaAberta(titulo="Planilha", documento=documento),
    )

    with TestClient(criar_app()) as cliente:
        listagem = cliente.get("/api/categorias").json()
        criada = cliente.post(
            "/api/categorias", json={"nome": "Pet", "tipo": "GASTO", "cor": "#A1887F"}
        )
        excluida = cliente.delete("/api/categorias/pet")

    assert len(listagem) == 17
    assert [item["nome"] for item in listagem[:3]] == [
        "A classificar",
        "Alimentação",
        "Assinaturas",
    ]
    assert [item["id"] for item in listagem if item["reservada"]] == [
        "a-classificar",
        "a-classificar-receita",
    ]
    assert all(item["em_uso"] is False for item in listagem)
    assert criada.status_code == 201
    assert excluida.status_code == 204
    assert "pet" not in [linha[0] for linha in documento.linhas("Categorias")[1:]]
    # Criar = um `append_rows` na aba; excluir = um único `batch_update` (T-009).
    assert [escrita[0] for escrita in documento.escritas[-2:]] == ["append_rows", "batch_update"]
    assert documento.escritas[-2][1] == "Categorias"
