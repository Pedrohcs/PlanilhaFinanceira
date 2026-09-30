"""`GET /api/resumo/mensal` (REQ-12, RN-03, RN-13, RN-16; `SPECS/03` §6; F-09)."""

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

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
