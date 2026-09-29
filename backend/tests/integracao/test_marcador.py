"""Sentinela do marcador `integracao` (CA-F01.7).

Sem `SPREADSHEET_ID_TESTE` o `conftest` pula este teste; o `addopts` padrão
(`-m 'not integracao'`) ainda o retira da execução normal. Os testes de
integração de verdade chegam em T-009 e T-034.
"""

import os

import pytest


@pytest.mark.integracao
def test_integracao_pulado_sem_variavel__CA_F01_7() -> None:
    """Só executa quando a planilha de teste está configurada."""
    assert os.environ["SPREADSHEET_ID_TESTE"]
