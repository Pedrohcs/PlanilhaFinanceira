"""Compra parcelada pelo app real (CA-07.1 a CA-07.3, CA-08.1, CA-08.2, RN-07, RN-08; F-15 §3.2.5).

Datas fixas em anos distantes (borda 13): 2096 é bissexto, 2097 não.
"""

from contextlib import suppress
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.integracao.ambiente import nova_marca


@pytest.mark.integracao
def test_parcelas_e_exclusao__RN_07(cliente_teste: TestClient, categoria_gasto_id: str) -> None:
    marca = nova_marca()
    parcelamentos: list[str] = []

    def parcelar(data: str, valor_total: float, parcelas: int) -> list[dict[str, Any]]:
        resposta = cliente_teste.post(
            "/api/parcelamentos",
            json={
                "data": data,
                "descricao": marca,
                "valor_total": valor_total,
                "parcelas": parcelas,
                "categoria_id": categoria_gasto_id,
                "forma_pagamento": "CREDITO",
            },
        )
        assert resposta.status_code == 201, resposta.text
        parcelamentos.append(resposta.json()["parcelamento_id"])
        return resposta.json()["lancamentos"]

    def do_mes(mes: str) -> list[dict[str, Any]]:
        itens = cliente_teste.get(f"/api/lancamentos?mes={mes}").json()["itens"]
        return [i for i in itens if i["descricao"] == marca]

    try:
        # CA-07.1 / RN-07: o centavo que sobra vai para a 1ª parcela.
        parcelas = parcelar("2098-01-15", 1000, 3)
        assert [p["valor"] for p in parcelas] == [333.34, 333.33, 333.33]
        assert [p["data"] for p in parcelas] == ["2098-01-15", "2098-02-15", "2098-03-15"]

        # CA-07.3: cada mês mostra "k/N" e a descrição original.
        fevereiro = do_mes("2098-02")
        assert [(i["parcela_numero"], i["parcela_total"]) for i in fevereiro] == [(2, 3)]

        # CA-07.2: 31/01 em 2 → último dia de fevereiro.
        assert [p["data"] for p in parcelar("2096-01-31", 100, 2)] == ["2096-01-31", "2096-02-29"]
        assert [p["data"] for p in parcelar("2097-01-31", 100, 2)] == ["2097-01-31", "2097-02-28"]

        # CA-08.1 / RN-08: editar uma parcela não mexe nas outras.
        segunda = fevereiro[0]
        editada = cliente_teste.put(
            f"/api/lancamentos/{segunda['id']}",
            json={
                "data": segunda["data"],
                "tipo": "GASTO",
                "descricao": marca,
                "valor": 300,
                "categoria_id": categoria_gasto_id,
                "forma_pagamento": "CREDITO",
            },
        )
        assert editada.status_code == 200, editada.text
        assert [i["valor"] for i in do_mes("2098-03")] == [333.33]

        # CA-08.2: excluir o parcelamento inteiro remove todas as parcelas, em todos os meses.
        resposta = cliente_teste.delete(f"/api/parcelamentos/{parcelamentos[0]}")
        assert resposta.status_code == 204
        assert [do_mes(mes) for mes in ("2098-01", "2098-02", "2098-03")] == [[], [], []]
    finally:
        for id_ in parcelamentos:
            with suppress(Exception):
                cliente_teste.delete(f"/api/parcelamentos/{id_}")
