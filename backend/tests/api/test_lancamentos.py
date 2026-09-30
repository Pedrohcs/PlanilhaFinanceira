"""`POST /api/lancamentos` (REQ-01, REQ-02, RN-01..06; `SPECS/03` §6; F-06)."""

import time
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


# GET /api/lancamentos (F-07) -----------------------------------------------------

CABECALHO = list(ABA_LANCAMENTOS.colunas)


def linha(id_: str, data: str, valor: Any = 42.5, **campos: Any) -> list[Any]:
    dados: dict[str, Any] = {
        "id": id_, "data": data, "tipo": "GASTO", "descricao": f"Compra {id_}", "valor": valor,
        "categoria_id": "alimentacao", "forma_pagamento": "PIX", "observacao": "",
        "parcelamento_id": "", "parcela_numero": "", "parcela_total": "", "recorrencia_id": "",
        "criado_em": "2026-09-29T10:15:00", "atualizado_em": "2026-09-29T10:15:00",
    }  # fmt: skip
    dados.update(campos)
    return [dados[coluna] for coluna in CABECALHO]


def cliente_com_planilha(
    monkeypatch: pytest.MonkeyPatch, *linhas: list[Any]
) -> tuple[TestClient, PlanilhaFalsa]:
    documento = PlanilhaFalsa({"Lancamentos": [CABECALHO, *linhas]})
    monkeypatch.setattr(
        sheets_client,
        "abrir_planilha",
        lambda *_a, **_k: PlanilhaAberta(titulo="Planilha", documento=documento),
    )
    return TestClient(criar_app()), documento


def test_get_formato_de_lista__CA_03_1(cliente_memoria: TestClient) -> None:
    """Contrato de `03` §6.3, com parcela, recorrência e saldo negativo."""
    cliente_memoria.post("/api/lancamentos", json=entrada(valor=100.0, data="2026-09-10"))
    cliente_memoria.post(
        "/api/lancamentos",
        json=entrada(tipo="RECEITA", categoria_id="salario", valor=40.0, data="2026-09-20"),
    )

    resposta = cliente_memoria.get("/api/lancamentos?mes=2026-09")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["mes"] == "2026-09"
    assert corpo["totais"] == {"gastos": 100.0, "receitas": 40.0, "saldo": -60.0}
    assert corpo["linhas_ignoradas"] == 0
    assert [item["data"] for item in corpo["itens"]] == ["2026-09-20", "2026-09-10"]
    assert set(corpo["itens"][0]) == {
        "id", "data", "tipo", "descricao", "valor", "categoria_id", "categoria_nome",
        "categoria_cor", "forma_pagamento", "observacao", "parcelamento_id", "parcela_numero",
        "parcela_total", "recorrencia_id", "criado_em", "atualizado_em",
    }  # fmt: skip


def test_get_mes_vazio_e_filtros(cliente_memoria: TestClient) -> None:
    cliente_memoria.post("/api/lancamentos", json=entrada(data="2026-09-10"))

    vazio = cliente_memoria.get("/api/lancamentos?mes=2026-10").json()
    filtrado = cliente_memoria.get(
        "/api/lancamentos?mes=2026-09&tipo=RECEITA&categoria_id=nao-existe&forma_pagamento=PIX"
    ).json()

    assert vazio["itens"] == []
    assert vazio["totais"] == {"gastos": 0.0, "receitas": 0.0, "saldo": 0.0}
    assert filtrado["itens"] == []


@pytest.mark.parametrize(
    ("consulta", "campo"),
    [
        ("", "mes"),
        ("?mes=2026-13", "mes"),
        ("?mes=setembro", "mes"),
        ("?mes=2026-9", "mes"),
        ("?mes=2026-09&tipo=gasto", "tipo"),
        ("?mes=2026-09&forma_pagamento=CHEQUE", "forma_pagamento"),
    ],
)
def test_get_422__CA_F07_5(cliente_memoria: TestClient, consulta: str, campo: str) -> None:
    resposta = cliente_memoria.get(f"/api/lancamentos{consulta}")

    assert resposta.status_code == 422
    assert campos_com_erro(resposta) == [campo]


def test_get_ignora_linha_invalida__CA_16_3(monkeypatch: pytest.MonkeyPatch) -> None:
    """CA-F07.7, borda 9: fora da lista e dos totais, contada em `linhas_ignoradas`."""
    cliente, _ = cliente_com_planilha(
        monkeypatch,
        linha("boa", "2026-09-10", 42.5),
        linha("zero", "2026-09-11", 0),
        linha("outro-mes", "2026-08-11", 10),
    )

    with cliente:
        corpo = cliente.get("/api/lancamentos?mes=2026-09").json()

    assert [item["id"] for item in corpo["itens"]] == ["boa"]
    assert corpo["totais"]["gastos"] == 42.5
    assert corpo["linhas_ignoradas"] == 1
    assert corpo["itens"][0]["categoria_nome"] == "Alimentação"  # da categoria semeada


def test_get_uma_leitura_por_aba__RNF_04(monkeypatch: pytest.MonkeyPatch) -> None:
    """CA-F07.8, borda 20 de F-03: 5.000 linhas, uma leitura de cada aba, bem abaixo de 3 s."""
    linhas = [linha(f"l{n}", f"2026-{(n % 12) + 1:02d}-15", 1.25) for n in range(5000)]
    cliente, documento = cliente_com_planilha(monkeypatch, *linhas)

    with cliente:
        documento.leituras.clear()
        inicio = time.perf_counter()
        corpo = cliente.get("/api/lancamentos?mes=2026-09").json()
        duracao = time.perf_counter() - inicio

    # 5000 = 12 × 416 + 8: jan–ago têm 417; setembro (índice 8) tem 416.
    assert len(corpo["itens"]) == 416
    assert corpo["totais"]["gastos"] == 520.0
    assert documento.leituras == {"Lancamentos": 1, "Categorias": 1}
    assert duracao < 3


def test_get_503__CA_F07_9(cliente: TestClient) -> None:
    resposta = cliente.get("/api/lancamentos?mes=2026-09")

    assert resposta.status_code == 503
    assert resposta.json()["erro"]["codigo"] == "CREDENCIAIS_INVALIDAS"


def test_post_e_get_ponta_a_ponta__CA_01_5(monkeypatch: pytest.MonkeyPatch) -> None:
    """O registrado aparece na listagem seguinte: a escrita invalida o cache (F-03)."""
    cliente, _ = cliente_com_planilha(monkeypatch)

    with cliente:
        antes = cliente.get("/api/lancamentos?mes=2026-09").json()
        cliente.post("/api/lancamentos", json=entrada(categoria_id="alimentacao"))
        depois = cliente.get("/api/lancamentos?mes=2026-09").json()

    assert antes["itens"] == []
    assert [item["descricao"] for item in depois["itens"]] == ["Almoço"]
    assert depois["totais"]["gastos"] == 42.5


# PUT e DELETE /api/lancamentos/{id} (F-08) -------------------------------------


def linhas_de(documento: PlanilhaFalsa) -> list[list[Any]]:
    return [list(valores) for valores in documento.worksheet(ABA_LANCAMENTOS.nome).valores[1:]]


def test_put_so_a_linha_do_id_apos_reordenacao__CA_05_2(monkeypatch: pytest.MonkeyPatch) -> None:
    """CA-F08.2, borda 1: o usuário reordenou a planilha depois da última leitura."""
    cliente, documento = cliente_com_planilha(
        monkeypatch,
        linha("a", "2026-09-10"),
        linha("b", "2026-09-11"),
        linha("c", "2026-09-12"),
    )

    with cliente:
        cliente.get("/api/lancamentos?mes=2026-09")  # cache com a ordem antiga
        aba = documento.worksheet(ABA_LANCAMENTOS.nome)
        aba.valores[1], aba.valores[3] = aba.valores[3], aba.valores[1]  # c, b, a
        antes = {linha_[0]: linha_ for linha_ in linhas_de(documento)}

        resposta = cliente.put(
            "/api/lancamentos/a",
            json=entrada(categoria_id="alimentacao", descricao="Corrigido", valor=50.0),
        )

    assert resposta.status_code == 200
    depois = {linha_[0]: linha_ for linha_ in linhas_de(documento)}
    assert [linha_[0] for linha_ in linhas_de(documento)] == ["c", "b", "a"]  # posições mantidas
    assert depois["b"] == antes["b"]
    assert depois["c"] == antes["c"]
    assert (depois["a"][3], depois["a"][4]) == ("Corrigido", 50.0)
    assert depois["a"][12] == antes["a"][12]  # criado_em preservado
    assert depois["a"][13] != antes["a"][13]  # atualizado_em novo


def test_put_muda_de_mes__CA_05_3(cliente_memoria: TestClient) -> None:
    """CA-F08.6, borda 6: sai de setembro, entra em outubro; os totais acompanham."""
    criado = cliente_memoria.post(
        "/api/lancamentos", json=entrada(data="2026-09-30", valor=80.0)
    ).json()

    resposta = cliente_memoria.put(
        f"/api/lancamentos/{criado['id']}", json=entrada(data="2026-10-02", valor=80.0)
    )
    setembro = cliente_memoria.get("/api/lancamentos?mes=2026-09").json()
    outubro = cliente_memoria.get("/api/lancamentos?mes=2026-10").json()

    assert resposta.status_code == 200
    assert resposta.json()["data"] == "2026-10-02"
    assert setembro["itens"] == [] and setembro["totais"]["gastos"] == 0.0
    assert [item["id"] for item in outubro["itens"]] == [criado["id"]]
    assert outubro["totais"]["gastos"] == 80.0


def test_delete_so_a_linha_e_totais__CA_06_2(monkeypatch: pytest.MonkeyPatch) -> None:
    """CA-F08.7: remove só a linha do `id`, mesmo após reordenação; totais recalculados."""
    cliente, documento = cliente_com_planilha(
        monkeypatch,
        linha("a", "2026-09-10", 10.0),
        linha("b", "2026-09-11", 20.0),
        linha("c", "2026-09-12", 30.0),
    )

    with cliente:
        cliente.get("/api/lancamentos?mes=2026-09")
        aba = documento.worksheet(ABA_LANCAMENTOS.nome)
        aba.valores[1], aba.valores[3] = aba.valores[3], aba.valores[1]  # c, b, a
        antes = {linha_[0]: linha_ for linha_ in linhas_de(documento)}

        resposta = cliente.delete("/api/lancamentos/b")
        lista = cliente.get("/api/lancamentos?mes=2026-09").json()

    assert resposta.status_code == 204
    assert linhas_de(documento) == [antes["c"], antes["a"]]
    assert lista["totais"]["gastos"] == 40.0


@pytest.mark.parametrize(("metodo", "corpo"), [("PUT", entrada()), ("DELETE", None)])
def test_put_delete_404__CA_F08_3(
    cliente_memoria: TestClient, metodo: str, corpo: dict[str, Any] | None
) -> None:
    resposta = cliente_memoria.request(metodo, "/api/lancamentos/nao-existe", json=corpo)

    assert resposta.status_code == 404
    assert resposta.json()["erro"] == {
        "codigo": "NAO_ENCONTRADO",
        "mensagem": "Lançamento não encontrado.",
        "detalhes": [],
    }


@pytest.mark.parametrize(
    ("alteracoes", "status_esperado", "codigo"),
    [
        ({"valor": 0}, 422, "VALIDACAO"),
        ({"categoria_id": "salario"}, 409, "CATEGORIA_TIPO_INCOMPATIVEL"),
        ({"categoria_id": "velha"}, 409, "CATEGORIA_INATIVA"),  # trocar para outra inativa
        ({"forma_pagamento": None}, 422, "VALIDACAO"),
    ],
)
def test_put_validacoes__CA_F08_4(
    cliente_memoria: TestClient, alteracoes: dict[str, Any], status_esperado: int, codigo: str
) -> None:
    criado = cliente_memoria.post("/api/lancamentos", json=entrada()).json()

    resposta = cliente_memoria.put(f"/api/lancamentos/{criado['id']}", json=entrada(**alteracoes))

    assert resposta.status_code == status_esperado
    assert resposta.json()["erro"]["codigo"] == codigo
    lista = cliente_memoria.get("/api/lancamentos?mes=2026-09").json()
    assert lista["itens"][0]["valor"] == 42.5  # nada mudou


def test_put_delete_503__CA_F08_9(cliente: TestClient) -> None:
    for resposta in (
        cliente.put("/api/lancamentos/x", json=entrada()),
        cliente.delete("/api/lancamentos/x"),
    ):
        assert resposta.status_code == 503
        assert resposta.json()["erro"]["codigo"] == "CREDENCIAIS_INVALIDAS"


def test_descricao_com_igual_editada__ADR_04(monkeypatch: pytest.MonkeyPatch) -> None:
    """Borda 13: continua texto na planilha (RAW)."""
    cliente, documento = cliente_com_planilha(monkeypatch, linha("a", "2026-09-10"))

    with cliente:
        cliente.put(
            "/api/lancamentos/a",
            json=entrada(categoria_id="alimentacao", descricao="=SOMA(A1:A9)"),
        )

    assert linhas_de(documento)[0][3] == "=SOMA(A1:A9)"
