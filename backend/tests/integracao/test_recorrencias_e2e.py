"""Sincronização de recorrências pelo app real (CA-10.1 a CA-10.4, RN-09 a RN-11; F-15 §3.2.5).

A recorrência começa dois meses antes do corrente, no dia 31 (borda 12). Não há
`DELETE` de recorrência (`03` §6.1): a linha dela e os lançamentos gerados, todos
com a marca na descrição, são apagados na aba no fim.

O "período pausado não é gerado" ao reativar num mês **posterior** exige avançar
o relógio; fica nos testes unitários de F-13. Aqui: pausar e reativar no mesmo
mês não geram nada nem mexem em `ultimo_mes_gerado`.
"""

from typing import Any

import gspread
import pytest
from fastapi.testclient import TestClient

from app.domain.datas import (
    ano_e_mes,
    dias_no_mes,
    mes_anterior,
    mes_corrente,
    meses_entre,
    proximo_mes,
)
from tests.integracao.ambiente import apagar_linhas_marcadas, nova_marca


@pytest.mark.integracao
def test_sincronizacao__RN_10(
    cliente_teste: TestClient, documento_teste: gspread.Spreadsheet, categoria_gasto_id: str
) -> None:
    marca = nova_marca()
    corrente = mes_corrente()
    inicio = mes_anterior(mes_anterior(corrente))
    esperados = meses_entre(inicio, corrente)

    def sincronizar(recorrencia_id: str) -> list[str]:
        resposta = cliente_teste.post("/api/recorrencias/sincronizar")
        assert resposta.status_code == 200, resposta.text
        detalhes = resposta.json()["detalhes"]
        return next((d["meses"] for d in detalhes if d["recorrencia_id"] == recorrencia_id), [])

    def gerados(mes: str) -> list[dict[str, Any]]:
        itens = cliente_teste.get(f"/api/lancamentos?mes={mes}").json()["itens"]
        return [i for i in itens if i["descricao"] == marca]

    def recorrencia(recorrencia_id: str) -> dict[str, Any]:
        todas = cliente_teste.get("/api/recorrencias").json()
        return next(r for r in todas if r["id"] == recorrencia_id)

    def mudar_status(recorrencia_id: str, status: str) -> None:
        resposta = cliente_teste.patch(
            f"/api/recorrencias/{recorrencia_id}/status", json={"status": status}
        )
        assert resposta.status_code == 200, resposta.text

    try:
        criada = cliente_teste.post(
            "/api/recorrencias",
            json={
                "tipo": "GASTO",
                "descricao": marca,
                "valor": 50,
                "categoria_id": categoria_gasto_id,
                "forma_pagamento": "PIX",
                "dia_do_mes": 31,
                "mes_inicio": inicio,
            },
        )
        assert criada.status_code == 201, criada.text
        recorrencia_id = criada.json()["id"]

        # CA-10.1: os três meses de vigência, no último dia de cada um (RN-09).
        assert sincronizar(recorrencia_id) == esperados
        for mes in esperados:
            [item] = gerados(mes)
            ano, numero = ano_e_mes(mes)
            ultimo_dia = min(31, dias_no_mes(mes))
            assert item["data"] == f"{ano:04d}-{numero:02d}-{ultimo_dia:02d}"
            assert item["recorrencia_id"] == recorrencia_id

        # CA-10.2: de novo, nada duplicado.
        assert sincronizar(recorrencia_id) == []

        # CA-10.3 / RN-10: excluído não volta.
        [do_meio] = gerados(esperados[1])
        assert cliente_teste.delete(f"/api/lancamentos/{do_meio['id']}").status_code == 204
        assert sincronizar(recorrencia_id) == []
        assert gerados(esperados[1]) == []

        # CA-10.4: nada no mês seguinte.
        assert gerados(proximo_mes(corrente)) == []
        assert recorrencia(recorrencia_id)["ultimo_mes_gerado"] == corrente

        # RN-11: pausada não gera; reativada no mesmo mês também não, e a marca d'água fica.
        mudar_status(recorrencia_id, "PAUSADA")
        assert sincronizar(recorrencia_id) == []
        mudar_status(recorrencia_id, "ATIVA")
        assert sincronizar(recorrencia_id) == []
        assert recorrencia(recorrencia_id)["ultimo_mes_gerado"] == corrente
    finally:
        apagar_linhas_marcadas(documento_teste)
