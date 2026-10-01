"""`GET /api/resumo/mensal` e `/historico` (REQ-12, REQ-14, RN-03, RN-13, RN-16; F-09, F-11)."""

import time
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.deps import Repositorios, obter_repositorios
from app.domain.datas import mes_corrente
from app.main import criar_app
from app.repositories.memoria import (
    CategoriaRepositoryMemoria,
    LancamentoRepositoryMemoria,
    RecorrenciaRepositoryMemoria,
)
from tests.api.test_lancamentos import campos_com_erro, cliente_com_planilha, linha


def test_get_formato__CA_12_1(monkeypatch: pytest.MonkeyPatch) -> None:
    """Contrato exato de `03` §6.3; categorias semeadas pelo bootstrap (RN-15)."""
    cliente, _ = cliente_com_planilha(
        monkeypatch,
        linha("a", "2026-09-01", 1000.0, categoria_id="moradia", forma_pagamento="CREDITO"),
        linha("b", "2026-09-02", 300.0, forma_pagamento="PIX"),
        linha("c", "2026-09-02", 200.0, forma_pagamento="CREDITO"),
        linha(
            "r", "2026-09-05", 5000.0, tipo="RECEITA", categoria_id="salario", forma_pagamento=""
        ),
        linha("fora", "2026-10-01", 99.0),
    )

    with cliente:
        resposta = cliente.get("/api/resumo/mensal?mes=2026-09")
        lista = cliente.get("/api/lancamentos?mes=2026-09").json()

    assert resposta.status_code == 200
    corpo = resposta.json()
    acumulado = corpo.pop("gasto_acumulado_diario")
    assert corpo == {
        "mes": "2026-09",
        "total_gastos": 1500.0,
        "total_receitas": 5000.0,
        "saldo": 3500.0,
        "por_categoria": [
            {
                "categoria_id": "moradia",
                "nome": "Moradia",
                "cor": corpo["por_categoria"][0]["cor"],
                "total": 1000.0,
                "percentual": 66.7,
            },
            {
                "categoria_id": "alimentacao",
                "nome": "Alimentação",
                "cor": "#E57373",
                "total": 500.0,
                "percentual": 33.3,
            },
        ],
        "por_forma_pagamento": [
            {
                "forma_pagamento": "CREDITO",
                "nome": "Cartão de crédito",
                "total": 1200.0,
                "percentual": 80.0,
            },
            {"forma_pagamento": "PIX", "nome": "Pix", "total": 300.0, "percentual": 20.0},
        ],
        "linhas_ignoradas": 0,
    }
    assert len(acumulado) == 30
    assert acumulado[0] == {"dia": 1, "total": 1000.0}
    assert acumulado[1] == {"dia": 2, "total": 1500.0}
    assert acumulado[29] == {"dia": 30, "total": 1500.0}
    # Mesmos números da listagem sem filtro (CA-F09.1).
    assert lista["totais"] == {"gastos": 1500.0, "receitas": 5000.0, "saldo": 3500.0}


@pytest.mark.parametrize("consulta", ["", "?mes=2026-13", "?mes=2026-9", "?mes=setembro"])
def test_get_422_mes__CA_F09_7(cliente: TestClient, consulta: str) -> None:
    resposta = cliente.get(f"/api/resumo/mensal{consulta}")

    assert resposta.status_code == 422
    assert campos_com_erro(resposta) == ["mes"]


def test_get_503__CA_F09_7(cliente: TestClient) -> None:
    resposta = cliente.get("/api/resumo/mensal?mes=2026-09")

    assert resposta.status_code == 503
    assert resposta.json()["erro"]["codigo"] == "CREDENCIAIS_INVALIDAS"


def test_linha_invalida_ignorada__CA_16_3(monkeypatch: pytest.MonkeyPatch) -> None:
    """CA-F09.8, borda 11: fora de todas as somas, contada em `linhas_ignoradas`."""
    cliente, _ = cliente_com_planilha(
        monkeypatch,
        linha("boa", "2026-09-10", 42.5),
        linha("ruim", "2026-09-11", "abc"),
    )

    with cliente:
        corpo: dict[str, Any] = cliente.get("/api/resumo/mensal?mes=2026-09").json()

    assert corpo["total_gastos"] == 42.5
    assert [item["total"] for item in corpo["por_categoria"]] == [42.5]
    assert corpo["gasto_acumulado_diario"][-1]["total"] == 42.5
    assert corpo["linhas_ignoradas"] == 1


def test_uma_leitura_por_aba__RNF_04(monkeypatch: pytest.MonkeyPatch) -> None:
    """CA-F09.9: 5.000 linhas, uma leitura de cada aba, nenhuma escrita, bem abaixo de 3 s."""
    linhas = [linha(f"l{n}", f"2026-{(n % 12) + 1:02d}-15", 1.25) for n in range(5000)]
    cliente, documento = cliente_com_planilha(monkeypatch, *linhas)

    with cliente:
        documento.leituras.clear()
        escritas_antes = len(documento.escritas)
        inicio = time.perf_counter()
        corpo = cliente.get("/api/resumo/mensal?mes=2026-09").json()
        duracao = time.perf_counter() - inicio

    assert corpo["total_gastos"] == 520.0  # 416 × 1,25 (setembro, como na listagem)
    assert documento.leituras == {"Lancamentos": 1, "Categorias": 1}
    assert len(documento.escritas) == escritas_antes
    assert duracao < 3


# Histórico (F-11) --------------------------------------------------------------------


@pytest.fixture
def cliente_memoria() -> Iterator[TestClient]:
    app = criar_app()
    app.dependency_overrides[obter_repositorios] = lambda: Repositorios(
        categorias=CategoriaRepositoryMemoria(),
        lancamentos=LancamentoRepositoryMemoria(),
        recorrencias=RecorrenciaRepositoryMemoria(),
    )
    with TestClient(app) as cliente:
        yield cliente


def test_get_historico_formato__CA_14_1(monkeypatch: pytest.MonkeyPatch) -> None:
    """Contrato exato de `03` §6.3 (exemplo de F-11 §6); mês vazio com zero."""
    cliente, _ = cliente_com_planilha(
        monkeypatch,
        linha("a", "2026-08-01", 1000.0, categoria_id="moradia", forma_pagamento="CREDITO"),
        linha("b", "2026-08-02", 200.0),
        linha("c", "2026-09-01", 1000.0, categoria_id="moradia", forma_pagamento="CREDITO"),
        linha("d", "2026-09-02", 500.0),
        linha(
            "r1", "2026-08-05", 5000.0, tipo="RECEITA", categoria_id="salario", forma_pagamento=""
        ),
        linha(
            "r2", "2026-09-05", 1000.0, tipo="RECEITA", categoria_id="salario", forma_pagamento=""
        ),
        linha("fora", "2026-10-01", 99.0),
    )

    with cliente:
        resposta = cliente.get("/api/resumo/historico?inicio=2026-07&fim=2026-09")
        setembro = cliente.get("/api/resumo/mensal?mes=2026-09").json()

    assert resposta.status_code == 200
    corpo = resposta.json()
    cor_moradia = corpo["por_categoria"][0]["cor"]
    assert corpo == {
        "inicio": "2026-07",
        "fim": "2026-09",
        "meses": [
            {"mes": "2026-07", "total_gastos": 0.0, "total_receitas": 0.0, "saldo": 0.0},
            {"mes": "2026-08", "total_gastos": 1200.0, "total_receitas": 5000.0, "saldo": 3800.0},
            {"mes": "2026-09", "total_gastos": 1500.0, "total_receitas": 1000.0, "saldo": -500.0},
        ],
        "por_categoria": [
            {
                "categoria_id": "moradia",
                "nome": "Moradia",
                "cor": cor_moradia,
                "valores": [0.0, 1000.0, 1000.0],
            },
            {
                "categoria_id": "alimentacao",
                "nome": "Alimentação",
                "cor": "#E57373",
                "valores": [0.0, 200.0, 500.0],
            },
        ],
        "total_gastos_periodo": 2700.0,
        "media_mensal_gastos": 900.0,
        "linhas_ignoradas": 0,
    }
    # Mesmos números do resumo mensal (CA-F11.2).
    assert corpo["meses"][2]["total_gastos"] == setembro["total_gastos"]
    assert corpo["meses"][2]["saldo"] == setembro["saldo"]


def test_get_historico_padrao__CA_14_1(cliente_memoria: TestClient) -> None:
    """Sem parâmetros: os 12 meses até o corrente (CA-F11.1)."""
    corpo = cliente_memoria.get("/api/resumo/historico").json()

    assert corpo["fim"] == mes_corrente()
    assert len(corpo["meses"]) == 12
    assert corpo["meses"][0]["mes"] == corpo["inicio"]
    assert corpo["meses"][-1]["mes"] == corpo["fim"]


@pytest.mark.parametrize(
    ("consulta", "campo"),
    [
        ("?inicio=2026-13&fim=2026-12", "inicio"),
        ("?inicio=2026-01&fim=2026-9", "fim"),
        ("?inicio=2026-01", "fim"),
        ("?fim=2026-01", "inicio"),
        ("?inicio=2026-09&fim=2026-01", "fim"),
        ("?inicio=2024-01&fim=2027-01", "fim"),  # 37 meses
    ],
)
def test_get_historico_422__CA_F11_8(
    cliente_memoria: TestClient, consulta: str, campo: str
) -> None:
    resposta = cliente_memoria.get(f"/api/resumo/historico{consulta}")

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "VALIDACAO"
    assert campos_com_erro(resposta) == [campo]


def test_get_historico_503__CA_F11_8(cliente: TestClient) -> None:
    resposta = cliente.get("/api/resumo/historico")

    assert resposta.status_code == 503
    assert resposta.json()["erro"]["codigo"] == "CREDENCIAIS_INVALIDAS"


def test_historico_linha_invalida_ignorada__CA_16_3(monkeypatch: pytest.MonkeyPatch) -> None:
    """CA-F11.9, borda 16: fora de todas as somas, contada em `linhas_ignoradas`."""
    cliente, _ = cliente_com_planilha(
        monkeypatch,
        linha("boa", "2026-09-10", 42.5),
        linha("ruim", "2026-09-11", "abc"),
    )

    with cliente:
        corpo: dict[str, Any] = cliente.get(
            "/api/resumo/historico?inicio=2026-09&fim=2026-09"
        ).json()

    assert corpo["total_gastos_periodo"] == 42.5
    assert corpo["por_categoria"][0]["valores"] == [42.5]
    assert corpo["linhas_ignoradas"] == 1


def test_historico_uma_leitura_por_aba__RNF_04(monkeypatch: pytest.MonkeyPatch) -> None:
    """CA-F11.10: 5.000 linhas, 36 meses, uma leitura de cada aba, nenhuma escrita, < 3 s."""
    linhas = [linha(f"l{n}", f"2026-{(n % 12) + 1:02d}-15", 1.25) for n in range(5000)]
    cliente, documento = cliente_com_planilha(monkeypatch, *linhas)

    with cliente:
        documento.leituras.clear()
        escritas_antes = len(documento.escritas)
        inicio = time.perf_counter()
        corpo = cliente.get("/api/resumo/historico?inicio=2024-01&fim=2026-12").json()
        duracao = time.perf_counter() - inicio

    assert len(corpo["meses"]) == 36
    assert corpo["total_gastos_periodo"] == 6250.0  # 5.000 × 1,25, todas em 2026
    assert documento.leituras == {"Lancamentos": 1, "Categorias": 1}
    assert len(documento.escritas) == escritas_antes
    assert duracao < 3
