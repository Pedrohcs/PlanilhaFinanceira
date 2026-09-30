"""`POST /api/lancamentos` (REQ-01, REQ-02, RN-01..06; `SPECS/03` §6; F-06)."""

from collections.abc import Iterator
from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.deps import Repositorios, obter_repositorios
from app.domain.enums import TipoLancamento
from app.domain.modelos import Categoria
from app.infra import sheets_client
from app.infra.schema_planilha import ABA_LANCAMENTOS
from app.infra.sheets_client import PlanilhaAberta
from app.main import criar_app
from app.repositories.memoria import (
    CategoriaRepositoryMemoria,
    LancamentoRepositoryMemoria,
    RecorrenciaRepositoryMemoria,
)
from tests.planilha_falsa import PlanilhaFalsa

CRIADO = datetime(2026, 9, 29, 10, 15)


def categoria(id_: str, nome: str, tipo: str, *, ativa: bool = True) -> Categoria:
    return Categoria(
        id=id_, nome=nome, tipo=TipoLancamento(tipo), cor="#E57373", ativa=ativa, criado_em=CRIADO
    )


def entrada(**alteracoes: Any) -> dict[str, Any]:
    dados: dict[str, Any] = {
        "data": "2026-09-29",
        "tipo": "GASTO",
        "descricao": "Almoço",
        "valor": 42.5,
        "categoria_id": "mercado",
        "forma_pagamento": "PIX",
        "observacao": None,
    }
    dados.update(alteracoes)
    return dados


@pytest.fixture
def repositorios() -> Repositorios:
    return Repositorios(
        categorias=CategoriaRepositoryMemoria(
            [
                categoria("mercado", "Mercado", "GASTO"),
                categoria("velha", "Velha", "GASTO", ativa=False),
                categoria("salario", "Salário", "RECEITA"),
            ]
        ),
        lancamentos=LancamentoRepositoryMemoria(),
        recorrencias=RecorrenciaRepositoryMemoria(),
    )


@pytest.fixture
def cliente_memoria(repositorios: Repositorios) -> Iterator[TestClient]:
    app = criar_app()
    app.dependency_overrides[obter_repositorios] = lambda: repositorios
    with TestClient(app) as cliente:
        yield cliente


def campos_com_erro(resposta: Any) -> list[str]:
    return [detalhe["campo"] for detalhe in resposta.json()["erro"]["detalhes"]]


def test_post_201_formato_e_linha_na_planilha__CA_F06_1(monkeypatch: pytest.MonkeyPatch) -> None:
    """Composição real + planilha falsa já preparada pelo bootstrap (seed de RN-15)."""
    documento = PlanilhaFalsa()
    monkeypatch.setattr(
        sheets_client,
        "abrir_planilha",
        lambda *_a, **_k: PlanilhaAberta(titulo="Planilha", documento=documento),
    )

    with TestClient(criar_app()) as cliente:
        resposta = cliente.post(
            "/api/lancamentos",
            json=entrada(categoria_id="alimentacao", descricao="=SOMA(A1:A9)", valor=1234.5),
        )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert len(corpo["id"]) == 32
    assert corpo | {"id": None, "criado_em": None, "atualizado_em": None} == {
        "id": None,
        "data": "2026-09-29",
        "tipo": "GASTO",
        "descricao": "=SOMA(A1:A9)",  # borda 10: texto, não fórmula
        "valor": 1234.5,
        "categoria_id": "alimentacao",
        "categoria_nome": "Alimentação",
        "categoria_cor": "#E57373",
        "forma_pagamento": "PIX",
        "observacao": None,
        "parcelamento_id": None,
        "parcela_numero": None,
        "parcela_total": None,
        "recorrencia_id": None,
        "criado_em": None,
        "atualizado_em": None,
    }
    assert corpo["criado_em"] == corpo["atualizado_em"]

    linhas = documento.worksheet(ABA_LANCAMENTOS.nome).valores
    assert len(linhas) == 2  # cabeçalho + uma linha
    assert linhas[1] == [
        corpo["id"], "2026-09-29", "GASTO", "=SOMA(A1:A9)", 1234.5, "alimentacao", "PIX",
        "", "", "", "", "", corpo["criado_em"], corpo["atualizado_em"],
    ]  # fmt: skip


def test_uma_leitura_de_categorias_e_uma_escrita__RNF_04(monkeypatch: pytest.MonkeyPatch) -> None:
    """Borda 15: registrar não relê a aba de lançamentos e escreve uma vez só."""
    documento = PlanilhaFalsa()
    monkeypatch.setattr(
        sheets_client,
        "abrir_planilha",
        lambda *_a, **_k: PlanilhaAberta(titulo="Planilha", documento=documento),
    )

    with TestClient(criar_app()) as cliente:
        escritas_antes = len(documento.escritas)
        documento.leituras.clear()
        cliente.post("/api/lancamentos", json=entrada(categoria_id="alimentacao"))
        cliente.post("/api/lancamentos", json=entrada(categoria_id="mercado"))

    assert documento.leituras == {"Categorias": 1}  # a 2ª vem do cache
    assert [e[0] for e in documento.escritas[escritas_antes:]] == ["append_rows", "append_rows"]


@pytest.mark.parametrize("valor", [0, -5, 1.005, 10000000000.0, "abc", "42,50", None, True])
def test_valor_invalido_422__RN_01(
    cliente_memoria: TestClient, repositorios: Repositorios, valor: Any
) -> None:
    """CA-F06.2, bordas 1–3."""
    resposta = cliente_memoria.post("/api/lancamentos", json=entrada(valor=valor))

    assert resposta.status_code == 422
    assert campos_com_erro(resposta) == ["valor"]
    assert repositorios.lancamentos.listar().itens == []


def test_maior_valor_aceito__RN_01(cliente_memoria: TestClient) -> None:
    """Borda 3: 12 dígitos no total."""
    resposta = cliente_memoria.post("/api/lancamentos", json=entrada(valor=9999999999.99))

    assert resposta.status_code == 201
    assert resposta.json()["valor"] == 9999999999.99


@pytest.mark.parametrize("data", ["2026-02-30", "30/09/2026", 46294, "", None])
def test_data_422__RN_02(cliente_memoria: TestClient, data: Any) -> None:
    """CA-F06.3."""
    resposta = cliente_memoria.post("/api/lancamentos", json=entrada(data=data))

    assert resposta.status_code == 422
    assert campos_com_erro(resposta) == ["data"]


def test_data_ausente_422__RN_02(cliente_memoria: TestClient) -> None:
    corpo = entrada()
    del corpo["data"]

    resposta = cliente_memoria.post("/api/lancamentos", json=corpo)

    assert resposta.status_code == 422
    assert campos_com_erro(resposta) == ["data"]


@pytest.mark.parametrize("data", ["1999-01-01", "2030-12-31"])
def test_datas_extremas_aceitas__RN_02(cliente_memoria: TestClient, data: str) -> None:
    """Borda 4."""
    resposta = cliente_memoria.post("/api/lancamentos", json=entrada(data=data))

    assert resposta.status_code == 201
    assert resposta.json()["data"] == data


@pytest.mark.parametrize(
    ("alteracoes", "codigo"),
    [
        ({"categoria_id": "velha"}, "CATEGORIA_INATIVA"),
        ({"categoria_id": "salario"}, "CATEGORIA_TIPO_INCOMPATIVEL"),
    ],
)
def test_409_de_categoria__RN_04(
    cliente_memoria: TestClient,
    repositorios: Repositorios,
    alteracoes: dict[str, Any],
    codigo: str,
) -> None:
    """CA-F06.4."""
    resposta = cliente_memoria.post("/api/lancamentos", json=entrada(**alteracoes))

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == codigo
    assert repositorios.lancamentos.listar().itens == []


def test_categoria_inexistente_e_gasto_sem_forma_422_com_campo(
    cliente_memoria: TestClient,
) -> None:
    """CA-F06.4 e CA-F06.5: o formulário sabe qual campo marcar."""
    sem_categoria = cliente_memoria.post(
        "/api/lancamentos", json=entrada(categoria_id="nao-existe")
    )
    sem_forma = cliente_memoria.post("/api/lancamentos", json=entrada(forma_pagamento=None))

    assert sem_categoria.status_code == 422
    assert sem_categoria.json()["erro"] == {
        "codigo": "VALIDACAO",
        "mensagem": "Categoria não encontrada.",
        "detalhes": [{"campo": "categoria_id", "mensagem": "Categoria não encontrada."}],
    }
    assert sem_forma.status_code == 422
    assert campos_com_erro(sem_forma) == ["forma_pagamento"]


def test_receita_sem_forma_201__CA_02_2(cliente_memoria: TestClient) -> None:
    corpo = entrada(tipo="RECEITA", categoria_id="salario")
    del corpo["forma_pagamento"]

    resposta = cliente_memoria.post("/api/lancamentos", json=corpo)

    assert resposta.status_code == 201
    assert resposta.json()["forma_pagamento"] is None


@pytest.mark.parametrize(
    ("alteracoes", "campo"),
    [
        ({"descricao": ""}, "descricao"),
        ({"descricao": "     "}, "descricao"),
        ({"descricao": "x" * 101}, "descricao"),
        ({"observacao": "y" * 501}, "observacao"),
        ({"forma_pagamento": "CHEQUE"}, "forma_pagamento"),
        ({"tipo": "gasto"}, "tipo"),
    ],
)
def test_descricao_observacao_e_enums_422__RN_06(
    cliente_memoria: TestClient, alteracoes: dict[str, Any], campo: str
) -> None:
    """CA-F06.6."""
    resposta = cliente_memoria.post("/api/lancamentos", json=entrada(**alteracoes))

    assert resposta.status_code == 422
    assert campos_com_erro(resposta) == [campo]


def test_descricao_e_observacao_aparadas__RN_06(cliente_memoria: TestClient) -> None:
    """Borda 9: pontas aparadas; observação só de espaços vira `null`."""
    no_limite = cliente_memoria.post(
        "/api/lancamentos",
        json=entrada(descricao="  " + "x" * 100 + "  ", observacao="   "),
    )
    com_observacao = cliente_memoria.post(
        "/api/lancamentos", json=entrada(descricao="  Almoço  ", observacao=" nota ")
    )

    assert no_limite.status_code == 201
    assert no_limite.json()["descricao"] == "x" * 100
    assert no_limite.json()["observacao"] is None
    assert com_observacao.json()["descricao"] == "Almoço"
    assert com_observacao.json()["observacao"] == "nota"


def test_planilha_inacessivel_503__CA_F06_8(cliente: TestClient) -> None:
    resposta = cliente.post("/api/lancamentos", json=entrada())

    assert resposta.status_code == 503
    assert resposta.json()["erro"]["codigo"] == "CREDENCIAIS_INVALIDAS"
