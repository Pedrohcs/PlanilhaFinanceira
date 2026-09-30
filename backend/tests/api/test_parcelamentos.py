"""`POST`/`DELETE /api/parcelamentos` (REQ-07, REQ-08, RN-07, RN-08; `SPECS/03` §6; F-12)."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.deps import Repositorios, obter_repositorios
from app.infra.schema_planilha import ABA_LANCAMENTOS
from app.main import criar_app
from app.repositories.memoria import (
    CategoriaRepositoryMemoria,
    LancamentoRepositoryMemoria,
    RecorrenciaRepositoryMemoria,
)
from tests.api.test_lancamentos import (
    categoria,
    cliente_com_planilha,
    entrada,
    linha,
    linhas_de,
)

COLUNA = {nome: indice for indice, nome in enumerate(ABA_LANCAMENTOS.colunas)}


def parcelamento(**alteracoes: Any) -> dict[str, Any]:
    dados: dict[str, Any] = {
        "data": "2026-01-15",
        "descricao": "Geladeira",
        "valor_total": 1000.0,
        "parcelas": 3,
        "categoria_id": "mercado",
        "forma_pagamento": "CREDITO",
        "observacao": None,
    }
    dados.update(alteracoes)
    return dados


def parcela(id_: str, data: str, numero: int, total: int = 3, grupo: str = "par") -> list[Any]:
    return linha(
        id_,
        data,
        100.0,
        descricao="Geladeira",
        parcelamento_id=grupo,
        parcela_numero=numero,
        parcela_total=total,
    )


@pytest.fixture
def cliente_memoria() -> Iterator[TestClient]:
    repositorios = Repositorios(
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
    app = criar_app()
    app.dependency_overrides[obter_repositorios] = lambda: repositorios
    with TestClient(app) as cliente:
        yield cliente


def test_post_uma_escrita__CA_F12_2(monkeypatch: pytest.MonkeyPatch) -> None:
    """CA-F12.1 + CA-F12.2 na composição real; borda 16: descrição continua texto (RAW)."""
    cliente, documento = cliente_com_planilha(monkeypatch)

    with cliente:
        escritas_antes = len(documento.escritas)
        resposta = cliente.post(
            "/api/parcelamentos",
            json=parcelamento(categoria_id="alimentacao", descricao="=SOMA(A1:A3)"),
        )

    assert resposta.status_code == 201
    corpo = resposta.json()
    grupo = corpo["parcelamento_id"]
    assert len(grupo) == 32
    assert [
        (p["data"], p["valor"], p["parcela_numero"], p["parcela_total"])
        for p in corpo["lancamentos"]
    ] == [
        ("2026-01-15", 333.34, 1, 3),
        ("2026-02-15", 333.33, 2, 3),
        ("2026-03-15", 333.33, 3, 3),
    ]
    assert {p["parcelamento_id"] for p in corpo["lancamentos"]} == {grupo}
    assert {p["categoria_nome"] for p in corpo["lancamentos"]} == {"Alimentação"}
    assert len({p["id"] for p in corpo["lancamentos"]}) == 3
    novas = documento.escritas[escritas_antes:]
    assert [escrita[0] for escrita in novas] == ["append_rows"]  # uma chamada, 3 linhas
    assert len(novas[0][2]) == 3
    gravadas = linhas_de(documento)
    assert [g[COLUNA["descricao"]] for g in gravadas] == ["=SOMA(A1:A3)"] * 3
    assert [g[COLUNA["parcelamento_id"]] for g in gravadas] == [grupo] * 3
    assert [g[COLUNA["parcela_numero"]] for g in gravadas] == [1, 2, 3]
    assert [g[COLUNA["parcela_total"]] for g in gravadas] == [3, 3, 3]


@pytest.mark.parametrize(
    ("alteracoes", "status_esperado", "codigo", "campo"),
    [
        ({"parcelas": 1}, 422, "VALIDACAO", "parcelas"),
        ({"parcelas": 49}, 422, "VALIDACAO", "parcelas"),
        ({"parcelas": "três"}, 422, "VALIDACAO", "parcelas"),
        ({"valor_total": 0}, 422, "VALIDACAO", "valor_total"),
        ({"valor_total": 0.05, "parcelas": 10}, 422, "VALIDACAO", "valor_total"),
        ({"categoria_id": "nao-existe"}, 422, "VALIDACAO", "categoria_id"),
        ({"forma_pagamento": None}, 422, "VALIDACAO", "forma_pagamento"),
        ({"categoria_id": "velha"}, 409, "CATEGORIA_INATIVA", None),
        ({"categoria_id": "salario"}, 409, "CATEGORIA_TIPO_INCOMPATIVEL", None),
    ],
)
def test_post_validacoes__CA_F12_3(
    cliente_memoria: TestClient,
    alteracoes: dict[str, Any],
    status_esperado: int,
    codigo: str,
    campo: str | None,
) -> None:
    """CA-F12.3 e CA-F12.4: erro no campo certo e nada gravado."""
    resposta = cliente_memoria.post("/api/parcelamentos", json=parcelamento(**alteracoes))

    assert resposta.status_code == status_esperado
    erro = resposta.json()["erro"]
    assert erro["codigo"] == codigo
    if campo:
        assert [detalhe["campo"] for detalhe in erro["detalhes"]] == [campo]
    assert cliente_memoria.get("/api/lancamentos?mes=2026-01").json()["itens"] == []


def test_valor_minimo_mensagem__RN_07(cliente_memoria: TestClient) -> None:
    resposta = cliente_memoria.post(
        "/api/parcelamentos", json=parcelamento(valor_total=0.05, parcelas=10)
    )

    assert resposta.json()["erro"]["detalhes"] == [
        {
            "campo": "valor_total",
            "mensagem": "10 parcelas exigem um valor total de no mínimo R$ 0,10.",
        }
    ]


def test_delete_so_as_parcelas_apos_reordenacao__CA_F12_5(monkeypatch: pytest.MonkeyPatch) -> None:
    """CA-08.2: todas as parcelas, em qualquer mês, num `batch_update`; o resto intacto."""
    cliente, documento = cliente_com_planilha(
        monkeypatch,
        parcela("p1", "2026-01-15", 1),
        linha("avulso", "2026-01-20", 10.0),
        parcela("p2", "2026-02-15", 2),
        parcela("o1", "2026-02-20", 1, total=2, grupo="outro"),
        parcela("p3", "2026-03-15", 3),
    )

    with cliente:
        cliente.get("/api/lancamentos?mes=2026-01")  # cache com a ordem antiga
        aba = documento.worksheet(ABA_LANCAMENTOS.nome)
        aba.valores[1:] = aba.valores[:0:-1]  # o usuário inverteu as linhas à mão
        escritas_antes = len(documento.escritas)

        resposta = cliente.delete("/api/parcelamentos/par")
        meses = [
            cliente.get(f"/api/lancamentos?mes=2026-0{mes}").json()["totais"]["gastos"]
            for mes in (1, 2, 3)
        ]

    assert resposta.status_code == 204
    assert [escrita[0] for escrita in documento.escritas[escritas_antes:]] == ["batch_update"]
    assert [g[COLUNA["id"]] for g in linhas_de(documento)] == ["o1", "avulso"]
    assert meses == [10.0, 100.0, 0.0]


def test_delete_apos_linha_apagada_a_mao__CA_F12_8(monkeypatch: pytest.MonkeyPatch) -> None:
    """Borda 14: a leitura em cache ainda tem a p2, que o usuário já apagou."""
    cliente, documento = cliente_com_planilha(
        monkeypatch,
        parcela("p1", "2026-01-15", 1),
        parcela("p2", "2026-02-15", 2),
        parcela("p3", "2026-03-15", 3),
    )

    with cliente:
        cliente.get("/api/lancamentos?mes=2026-01")  # cache com as 3
        del documento.worksheet(ABA_LANCAMENTOS.nome).valores[2]  # p2 apagada à mão

        resposta = cliente.delete("/api/parcelamentos/par")

    assert resposta.status_code == 204
    assert linhas_de(documento) == []


def test_delete_404__CA_F12_7(cliente_memoria: TestClient) -> None:
    resposta = cliente_memoria.delete("/api/parcelamentos/nao-existe")

    assert resposta.status_code == 404
    assert resposta.json()["erro"] == {
        "codigo": "NAO_ENCONTRADO",
        "mensagem": "Parcelamento não encontrado.",
        "detalhes": [],
    }


def test_listagem_mostra_k_de_n__CA_07_3(cliente_memoria: TestClient) -> None:
    cliente_memoria.post("/api/parcelamentos", json=parcelamento())

    fevereiro = cliente_memoria.get("/api/lancamentos?mes=2026-02").json()

    [item] = fevereiro["itens"]
    assert (item["descricao"], item["valor"]) == ("Geladeira", 333.33)
    assert (item["parcela_numero"], item["parcela_total"]) == (2, 3)
    assert fevereiro["totais"]["gastos"] == 333.33


def test_editar_parcela_so_ela__CA_08_1(cliente_memoria: TestClient) -> None:
    """Borda 11: a parcela editada continua "2/3" e no parcelamento; as outras não mudam."""
    criado = cliente_memoria.post("/api/parcelamentos", json=parcelamento()).json()
    segunda = criado["lancamentos"][1]

    resposta = cliente_memoria.put(
        f"/api/lancamentos/{segunda['id']}",
        json=entrada(data="2026-02-15", descricao="Geladeira", valor=300.0),
    )
    itens = [
        item
        for mes in ("2026-01", "2026-02", "2026-03")
        for item in cliente_memoria.get(f"/api/lancamentos?mes={mes}").json()["itens"]
    ]

    assert resposta.status_code == 200
    assert [item["valor"] for item in itens] == [333.34, 300.0, 333.33]
    assert {item["parcelamento_id"] for item in itens} == {criado["parcelamento_id"]}
    assert [item["parcela_numero"] for item in itens] == [1, 2, 3]


def test_post_delete_503__CA_F12_9(cliente: TestClient) -> None:
    for resposta in (
        cliente.post("/api/parcelamentos", json=parcelamento()),
        cliente.delete("/api/parcelamentos/par"),
    ):
        assert resposta.status_code == 503
        assert resposta.json()["erro"]["codigo"] == "CREDENCIAIS_INVALIDAS"
