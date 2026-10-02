"""Registro, listagem, edição, exclusão e totais pelo app real (F-15 §3.2.5).

Num mês distante (2098), que só os testes usam: os totais podem ser conferidos
centavo a centavo (borda 11). As linhas são marcadas e apagadas no fim.
"""

from contextlib import suppress
from typing import Any

import gspread
import pytest
from fastapi.testclient import TestClient
from gspread.utils import ValueRenderOption

from app.infra.schema_planilha import ABA_LANCAMENTOS
from tests.integracao.ambiente import nova_marca

MES = "2098-03"
MES_SEGUINTE = "2098-04"


def linhas_por_id(documento: gspread.Spreadsheet) -> dict[str, list[Any]]:
    linhas = documento.worksheet(ABA_LANCAMENTOS.nome).get_all_values(
        value_render_option=ValueRenderOption.unformatted
    )
    return {str(linha[0]): linha for linha in linhas[1:] if linha and linha[0]}


@pytest.mark.integracao
def test_crud_e_totais__CA_05_2(
    cliente_teste: TestClient,
    documento_teste: gspread.Spreadsheet,
    categoria_gasto_id: str,
    categoria_receita_id: str,
) -> None:
    """CA-01.2, CA-01.5, CA-02.2, CA-05.2, CA-05.3, CA-06.2, CA-12.1, RN-13 e RN-16."""
    marca = nova_marca()
    criados: list[str] = []

    def entrada(descricao: str, valor: float, **campos: Any) -> dict[str, Any]:
        return {
            "data": f"{MES}-10",
            "tipo": "GASTO",
            "descricao": f"{marca} {descricao}",
            "valor": valor,
            "categoria_id": categoria_gasto_id,
            "forma_pagamento": "PIX",
        } | campos

    def registrar(dados: dict[str, Any]) -> dict[str, Any]:
        resposta = cliente_teste.post("/api/lancamentos", json=dados)
        assert resposta.status_code == 201, resposta.text
        criados.append(resposta.json()["id"])
        return resposta.json()

    def listar(mes: str) -> dict[str, Any]:
        corpo = cliente_teste.get(f"/api/lancamentos?mes={mes}").json()
        corpo["itens"] = [i for i in corpo["itens"] if i["descricao"].startswith(marca)]
        return corpo

    try:
        # CA-01.2 / CA-02.2: dois gastos e uma receita sem forma de pagamento.
        gasto_a = registrar(entrada("a", 0.10))
        gasto_b = registrar(entrada("b", 0.20))
        registrar(
            entrada(
                "salário",
                1000,
                tipo="RECEITA",
                categoria_id=categoria_receita_id,
                forma_pagamento=None,
            )
        )
        assert set(criados) <= set(linhas_por_id(documento_teste))

        # CA-01.5 / CA-12.1 / RN-13 / RN-16: 0,10 + 0,20 = 0,30 exatos, na lista e no resumo.
        lista = listar(MES)
        assert len(lista["itens"]) == 3
        assert lista["totais"] == {"gastos": 0.3, "receitas": 1000.0, "saldo": 999.7}
        resumo = cliente_teste.get(f"/api/resumo/mensal?mes={MES}").json()
        assert (resumo["total_gastos"], resumo["total_receitas"], resumo["saldo"]) == (
            0.3,
            1000.0,
            999.7,
        )

        # CA-05.2: editar muda só a linha daquele id.
        antes = linhas_por_id(documento_teste)
        resposta = cliente_teste.put(
            f"/api/lancamentos/{gasto_a['id']}", json=entrada("a editado", 0.10)
        )
        assert resposta.status_code == 200, resposta.text
        depois = linhas_por_id(documento_teste)
        assert depois.keys() == antes.keys()
        mudaram = [id_ for id_ in antes if antes[id_] != depois[id_]]
        assert mudaram == [gasto_a["id"]]

        # CA-05.3: a data em outro mês leva o lançamento para lá.
        resposta = cliente_teste.put(
            f"/api/lancamentos/{gasto_a['id']}",
            json=entrada("a editado", 0.10, data=f"{MES_SEGUINTE}-05"),
        )
        assert resposta.status_code == 200, resposta.text
        assert [i["id"] for i in listar(MES_SEGUINTE)["itens"]] == [gasto_a["id"]]
        assert listar(MES)["totais"]["gastos"] == 0.2

        # CA-06.2: excluir tira a linha da planilha e dos totais.
        assert cliente_teste.delete(f"/api/lancamentos/{gasto_b['id']}").status_code == 204
        assert gasto_b["id"] not in linhas_por_id(documento_teste)
        assert listar(MES)["totais"] == {"gastos": 0.0, "receitas": 1000.0, "saldo": 1000.0}
    finally:
        for id_ in criados:
            with suppress(Exception):
                cliente_teste.delete(f"/api/lancamentos/{id_}")
