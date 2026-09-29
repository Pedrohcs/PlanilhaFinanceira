"""Fixtures e configuração compartilhadas dos testes do backend (`SPECS/02` §8)."""

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

VARIAVEL_PLANILHA_TESTE = "SPREADSHEET_ID_TESTE"

# A suíte não depende de um `backend/.env` real: basta existir um id qualquer.
# Precisa vir antes de qualquer import de `app.main`, que instancia `Settings`.
os.environ.setdefault("SPREADSHEET_ID", "planilha-de-teste")

# Aponta a credencial para um caminho que não existe, de propósito: o padrão
# (`../credentials.json`) é o arquivo real do usuário, e o lifespan tentaria
# autenticar no Google a cada `pytest`. Assim a carga falha na hora, sem rede e
# sem tocar na credencial (RNF-05). Quem precisa de conexão boa injeta um dublê.
os.environ.setdefault("GOOGLE_CREDENTIALS_PATH", "credencial-inexistente-de-teste.json")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Pula os testes marcados como `integracao` quando falta a planilha de teste."""
    if os.getenv(VARIAVEL_PLANILHA_TESTE):
        return
    motivo = pytest.mark.skip(reason=f"{VARIAVEL_PLANILHA_TESTE} não definida")
    for item in items:
        if "integracao" in item.keywords:
            item.add_marker(motivo)


@pytest.fixture
def cliente() -> Iterator[TestClient]:
    """Cliente HTTP sobre uma instância nova da aplicação.

    Usado como gerenciador de contexto para que o lifespan rode — sem ele,
    `app.state.conexao` não existiria.
    """
    from app.main import criar_app

    with TestClient(criar_app()) as cliente_http:
        yield cliente_http
