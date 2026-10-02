"""Preparação de uma planilha vazia pelo app real (CA-15.1, CA-15.2, RN-15; F-15 Q6).

Apaga as 4 abas do app **na planilha de teste** — a trava do `conftest` impede
que seja a planilha do usuário — e deixa o app recriá-las ao subir. O Google
exige ao menos uma aba, então uma aba de apoio vazia é criada antes, se preciso,
e removida no fim.
"""

from typing import Any
from uuid import uuid4

import gspread
import pytest
from fastapi.testclient import TestClient
from gspread.utils import ValueRenderOption

from app.config import Settings
from app.infra.bootstrap import CATEGORIAS_PADRAO
from app.infra.schema_planilha import ABA_CATEGORIAS, ABAS
from app.main import criar_app

PREFIXO_APOIO = "apoio-teste-integracao-"


def conteudo(documento: gspread.Spreadsheet) -> dict[str, list[list[Any]]]:
    return {
        aba.nome: documento.worksheet(aba.nome).get_all_values(
            value_render_option=ValueRenderOption.unformatted
        )
        for aba in ABAS
    }


def subir_app(settings: Settings) -> None:
    with TestClient(criar_app(settings)) as cliente:
        saude = cliente.get("/api/health").json()
    assert saude["planilha"]["ok"] is True, saude


@pytest.mark.integracao
def test_planilha_vazia_preparada__CA_15_1(
    documento_teste: gspread.Spreadsheet, settings_teste: Settings
) -> None:
    """Sem as abas do app, subir cria abas, cabeçalhos e as 15 categorias; de novo, nada muda."""
    nomes_do_app = {aba.nome for aba in ABAS}
    for sobra in documento_teste.worksheets():  # de uma execução interrompida
        if sobra.title.startswith(PREFIXO_APOIO) and len(documento_teste.worksheets()) > 1:
            documento_teste.del_worksheet(sobra)
    apoio = None
    if all(aba.title in nomes_do_app for aba in documento_teste.worksheets()):
        apoio = documento_teste.add_worksheet(
            title=f"{PREFIXO_APOIO}{uuid4().hex[:8]}", rows=1, cols=1
        )
    try:
        for aba in documento_teste.worksheets():
            if aba.title in nomes_do_app:
                documento_teste.del_worksheet(aba)
        assert not nomes_do_app & {aba.title for aba in documento_teste.worksheets()}

        subir_app(settings_teste)  # CA-15.1

        preparada = conteudo(documento_teste)
        for aba in ABAS:
            assert preparada[aba.nome][0][: len(aba.colunas)] == list(aba.colunas)
        categorias = preparada[ABA_CATEGORIAS.nome]
        assert len(categorias) == 1 + len(CATEGORIAS_PADRAO) == 16
        coluna_nome = ABA_CATEGORIAS.colunas.index("nome")
        assert [linha[coluna_nome] for linha in categorias[1:]] == [
            nome for _id, nome, _tipo, _cor in CATEGORIAS_PADRAO
        ]  # RN-15

        subir_app(settings_teste)  # CA-15.2

        assert conteudo(documento_teste) == preparada
    finally:
        if apoio is not None:
            documento_teste.del_worksheet(apoio)
