"""Bootstrap e repositório contra a planilha real de teste (`SPECS/02` §8; F-03 §8).

Só roda com `pytest -m integracao` e `SPREADSHEET_ID_TESTE` definida no
terminal ou no `backend/.env`. Usa uma planilha **separada** da do usuário; cria as abas nela (se
faltarem) e apaga o lançamento que criar, mesmo se uma asserção falhar.
"""

from collections.abc import Callable
from contextlib import suppress
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

import gspread
import pytest
from gspread.utils import ValueRenderOption

from app.domain.enums import FormaPagamento, TipoLancamento
from app.domain.erros import NaoEncontrado
from app.domain.modelos import Lancamento
from app.infra.bootstrap import preparar_planilha
from app.infra.cache import CacheAbas
from app.infra.schema_planilha import ABA_CATEGORIAS, ABAS
from app.infra.sheets_client import executar_com_retry
from app.repositories.planilha import LancamentoRepositoryPlanilha


class FonteReal:
    """`ConexaoPlanilha.executar` sem o estado de conexão: a planilha já está aberta."""

    def __init__(self, documento: gspread.Spreadsheet) -> None:
        self._documento = documento

    def executar[R](self, operacao: Callable[[gspread.Spreadsheet], R]) -> R:
        return executar_com_retry(lambda: operacao(self._documento))


def conteudo(documento: gspread.Spreadsheet) -> dict[str, list[list[Any]]]:
    return {
        aba.nome: documento.worksheet(aba.nome).get_all_values(
            value_render_option=ValueRenderOption.unformatted
        )
        for aba in ABAS
    }


def lancamento(id_: str, descricao: str) -> Lancamento:
    instante = datetime(2026, 9, 30, 12, 0)
    return Lancamento(
        id=id_,
        data=date(2026, 9, 30),
        tipo=TipoLancamento.GASTO,
        descricao=descricao,
        valor=Decimal("12.34"),
        categoria_id="alimentacao",
        forma_pagamento=FormaPagamento.PIX,
        observacao="teste de integração — pode apagar",
        criado_em=instante,
        atualizado_em=instante,
    )


@pytest.mark.integracao
def test_bootstrap_e_crud_em_planilha_de_teste__CA_15_1(
    documento_teste: gspread.Spreadsheet,
) -> None:
    """CA-15.1, CA-15.2, CA-F03.9 e CA-F03.22 numa planilha do Google de verdade."""
    documento = documento_teste

    # CA-15.1 / CA-F03.9: abas e cabeçalhos exatamente como `03` §5.
    preparar_planilha(documento)
    antes = conteudo(documento)
    for aba in ABAS:
        assert antes[aba.nome][0][: len(aba.colunas)] == list(aba.colunas)
    assert len(antes[ABA_CATEGORIAS.nome]) > 1  # seed de RN-15 (ou categorias já existentes)

    # CA-15.2: rodar de novo não muda nada.
    preparar_planilha(documento)
    assert conteudo(documento) == antes

    # CRUD pelo repositório, com descrição que viraria fórmula sem RAW (CA-F03.22).
    repositorio = LancamentoRepositoryPlanilha(FonteReal(documento), CacheAbas(30))
    id_ = f"teste-integracao-{uuid4().hex}"
    try:
        repositorio.inserir([lancamento(id_, "=SOMA(A1:A2)")])
        assert repositorio.obter(id_).descricao == "=SOMA(A1:A2)"

        repositorio.atualizar(lancamento(id_, "Alterado pelo teste"))
        assert repositorio.obter(id_).descricao == "Alterado pelo teste"
    finally:
        with suppress(NaoEncontrado):
            repositorio.remover([id_])

    with pytest.raises(NaoEncontrado):
        repositorio.obter(id_)
