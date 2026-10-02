"""Edição manual da planilha e "Recarregar dados" pelo app real (CA-16.3, RN-14; F-15 §3.2.5).

Grava direto na aba uma linha com valor "abc", como o usuário faria à mão, e
depois a corrige. O número de linhas ignoradas é da aba inteira, então é
conferido por diferença.
"""

from typing import Any

import gspread
import pytest
from fastapi.testclient import TestClient
from gspread.utils import InsertDataOption, ValueInputOption, rowcol_to_a1

from app.infra.schema_planilha import ABA_LANCAMENTOS
from tests.integracao.ambiente import apagar_linhas_marcadas, nova_marca

MES = "2098-05"
INSTANTE = "2026-10-02T12:00:00"


@pytest.mark.integracao
def test_linha_invalida_e_recarregar__RN_14(
    cliente_teste: TestClient, documento_teste: gspread.Spreadsheet, categoria_gasto_id: str
) -> None:
    marca = nova_marca()
    aba = documento_teste.worksheet(ABA_LANCAMENTOS.nome)

    def recarregar_e_listar() -> dict[str, Any]:
        assert cliente_teste.post("/api/sistema/recarregar").status_code == 204
        return cliente_teste.get(f"/api/lancamentos?mes={MES}").json()

    def nossos(lista: dict[str, Any]) -> list[dict[str, Any]]:
        return [i for i in lista["itens"] if i["descricao"] == marca]

    antes = recarregar_e_listar()
    try:
        dados: dict[str, Any] = {
            "id": f"{marca}-manual", "data": f"{MES}-10", "tipo": "GASTO", "descricao": marca,
            "valor": "abc", "categoria_id": categoria_gasto_id, "forma_pagamento": "PIX",
            "observacao": "", "parcelamento_id": "", "parcela_numero": "", "parcela_total": "",
            "recorrencia_id": "", "criado_em": INSTANTE, "atualizado_em": INSTANTE,
        }  # fmt: skip
        aba.append_rows(
            values=[[dados[coluna] for coluna in ABA_LANCAMENTOS.colunas]],
            value_input_option=ValueInputOption.raw,
            insert_data_option=InsertDataOption.insert_rows,
        )

        # CA-16.3: a linha inválida fica fora da lista e dos totais, e é contada.
        com_invalida = recarregar_e_listar()
        assert com_invalida["linhas_ignoradas"] == antes["linhas_ignoradas"] + 1
        assert nossos(com_invalida) == []
        assert com_invalida["totais"] == antes["totais"]

        # RN-14: corrigida à mão, entra assim que o usuário recarrega.
        linha = aba.col_values(1).index(f"{marca}-manual") + 1
        coluna = ABA_LANCAMENTOS.colunas.index("valor") + 1
        aba.update(
            values=[[12.34]],
            range_name=rowcol_to_a1(linha, coluna),
            value_input_option=ValueInputOption.raw,
        )
        corrigida = recarregar_e_listar()
        assert corrigida["linhas_ignoradas"] == antes["linhas_ignoradas"]
        assert [i["valor"] for i in nossos(corrigida)] == [12.34]
        assert corrigida["totais"]["gastos"] == round(antes["totais"]["gastos"] + 12.34, 2)
    finally:
        apagar_linhas_marcadas(documento_teste)
