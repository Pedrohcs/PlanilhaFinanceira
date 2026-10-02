"""Desempenho com 5.000 lançamentos numa planilha do Google de verdade (RNF-04; F-14 §3.6.2).

Só roda com `pytest -m integracao` e `SPREADSHEET_ID_TESTE` definida (terminal ou
`backend/.env`) — nunca na planilha do app (trava do `conftest`). Grava 5.000
linhas marcadas numa única chamada, mede resumo, histórico e registro com o
cache frio e apaga **todas** as linhas marcadas ao final, mesmo se uma asserção
falhar (Q6, borda 13).
"""

import time
from datetime import date
from typing import Any
from uuid import uuid4

import gspread
import pytest
from fastapi.testclient import TestClient
from gspread.utils import InsertDataOption, ValueInputOption, ValueRenderOption

from app.domain.datas import mes_corrente, meses_entre, somar_meses
from app.infra.schema_planilha import ABA_CATEGORIAS, ABA_LANCAMENTOS
from tests.integracao.ambiente import apagar_linhas_marcadas

QUANTIDADE = 5000
LIMITE_SEGUNDOS = 3
INSTANTE = "2026-10-02T12:00:00"


def categoria_de_gasto(documento: gspread.Spreadsheet) -> str:
    """Id de uma categoria de gasto ativa (a seed de RN-15 garante pelo menos uma)."""
    linhas = documento.worksheet(ABA_CATEGORIAS.nome).get_all_values(
        value_render_option=ValueRenderOption.unformatted
    )
    cabecalho = linhas[0]
    for valores in linhas[1:]:
        dados = dict(zip(cabecalho, valores, strict=False))
        if dados.get("tipo") == "GASTO" and str(dados.get("ativa")).upper() == "TRUE":
            return str(dados["id"])
    pytest.fail("A planilha de teste não tem categoria de gasto ativa.")


def linhas_marcadas(marca: str, categoria_id: str, meses: list[str]) -> list[list[Any]]:
    """`QUANTIDADE` lançamentos espalhados pelos 12 meses do histórico padrão."""
    linhas = []
    for numero in range(QUANTIDADE):
        dados: dict[str, Any] = {
            "id": f"{marca}-{numero}", "data": f"{meses[numero % len(meses)]}-15",
            "tipo": "GASTO", "descricao": f"{marca} {numero}", "valor": 1.25,
            "categoria_id": categoria_id, "forma_pagamento": "PIX",
            "observacao": "teste de desempenho — pode apagar", "parcelamento_id": "",
            "parcela_numero": "", "parcela_total": "", "recorrencia_id": "",
            "criado_em": INSTANTE, "atualizado_em": INSTANTE,
        }  # fmt: skip
        linhas.append([dados[coluna] for coluna in ABA_LANCAMENTOS.colunas])
    return linhas


def medir(cliente: TestClient, metodo: str, caminho: str, **opcoes: Any) -> tuple[Any, float]:
    """Esvazia o cache (`POST /api/sistema/recarregar`) e mede uma requisição com o cache frio."""
    assert cliente.post("/api/sistema/recarregar").status_code == 204
    inicio = time.perf_counter()
    resposta = cliente.request(metodo, caminho, **opcoes)
    return resposta, time.perf_counter() - inicio


@pytest.mark.integracao
def test_desempenho_5000__RNF_04(
    documento_teste: gspread.Spreadsheet, cliente_teste: TestClient
) -> None:
    """CA-F14.16: resumo, histórico (12 meses) e registro abaixo de 3 s cada."""
    marca = f"teste-desempenho-{uuid4().hex[:12]}"
    corrente = mes_corrente()
    meses = meses_entre(mes_corrente(somar_meses(date.today().replace(day=1), -11)), corrente)
    categoria_id = categoria_de_gasto(documento_teste)  # bootstrap feito pelo `cliente_teste`

    try:
        documento_teste.worksheet(ABA_LANCAMENTOS.nome).append_rows(
            values=linhas_marcadas(marca, categoria_id, meses),
            value_input_option=ValueInputOption.raw,
            insert_data_option=InsertDataOption.insert_rows,
        )

        resumo, tempo_resumo = medir(cliente_teste, "GET", f"/api/resumo/mensal?mes={corrente}")
        historico, tempo_historico = medir(cliente_teste, "GET", "/api/resumo/historico")
        registro, tempo_registro = medir(
            cliente_teste,
            "POST",
            "/api/lancamentos",
            json={
                "data": f"{corrente}-15",
                "tipo": "GASTO",
                "descricao": f"{marca} registro",
                "valor": 1.25,
                "categoria_id": categoria_id,
                "forma_pagamento": "PIX",
            },
        )

        assert resumo.status_code == 200
        assert historico.status_code == 200
        assert len(historico.json()["meses"]) == 12
        assert registro.status_code == 201
        assert tempo_resumo < LIMITE_SEGUNDOS, f"resumo: {tempo_resumo:.2f} s"
        assert tempo_historico < LIMITE_SEGUNDOS, f"histórico: {tempo_historico:.2f} s"
        assert tempo_registro < LIMITE_SEGUNDOS, f"registro: {tempo_registro:.2f} s"
    finally:
        apagar_linhas_marcadas(documento_teste)

    descricoes = documento_teste.worksheet(ABA_LANCAMENTOS.nome).col_values(
        ABA_LANCAMENTOS.colunas.index("descricao") + 1
    )
    assert not [texto for texto in descricoes if texto.startswith(marca)]
