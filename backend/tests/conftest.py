"""Fixtures e configuração compartilhadas dos testes do backend (SPECS/02 §8)."""

import os

import pytest
from fastapi.testclient import TestClient

VARIAVEL_PLANILHA_TESTE = "SPREADSHEET_ID_TESTE"

# A suíte não depende de um `backend/.env` real: basta existir um id qualquer.
# Precisa vir antes de qualquer import de `app.main`, que instancia `Settings`.
os.environ.setdefault("SPREADSHEET_ID", "planilha-de-teste")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Pula os testes marcados como `integracao` quando falta a planilha de teste."""
    if os.getenv(VARIAVEL_PLANILHA_TESTE):
        return
    motivo = pytest.mark.skip(reason=f"{VARIAVEL_PLANILHA_TESTE} não definida")
    for item in items:
        if "integracao" in item.keywords:
            item.add_marker(motivo)


@pytest.fixture
def cliente() -> TestClient:
    """Cliente HTTP sobre uma instância nova da aplicação."""
    from app.main import criar_app

    return TestClient(criar_app())
