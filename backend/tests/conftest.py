"""Fixtures e configuração compartilhadas dos testes do backend (`SPECS/02` §8)."""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Antes das trocas abaixo: o módulo guarda o `SPREADSHEET_ID` e a credencial do
# terminal, para a trava e a credencial da integração (F-15 §3.2).
from tests.integracao.ambiente import (
    VARIAVEIS_PLUGGY,
    VARIAVEL_PLANILHA_TESTE,
    caminho_da_credencial,
    ler_planilha_teste,
    ler_pluggy_de_contrato,
)

# A suíte não depende de um `backend/.env` real: basta existir um id qualquer.
# Precisa vir antes de qualquer import de `app.main`, que instancia `Settings`.
os.environ.setdefault("SPREADSHEET_ID", "planilha-de-teste")

# Aponta a credencial para um caminho que não existe, de propósito: o padrão
# (`../credentials.json`) é o arquivo real do usuário, e o lifespan tentaria
# autenticar no Google a cada `pytest`. Assim a carga falha na hora, sem rede e
# sem tocar na credencial (RNF-05). Quem precisa de conexão boa injeta um dublê.
#
# O caminho que existia antes fica guardado em `tests.integracao.ambiente`, para
# os testes `integracao`, os únicos que falam com o Google de verdade. Só o
# **caminho**: o conteúdo nunca é lido pelos testes — quem abre o arquivo é o
# `google-auth`, como no app.
os.environ.setdefault("GOOGLE_CREDENTIALS_PATH", "credencial-inexistente-de-teste.json")

# Integração com a Pluggy **desligada** em toda a suíte, mesmo com as `PLUGGY_*`
# preenchidas no `backend/.env` ou no terminal: variável vazia no ambiente vale
# mais que o arquivo. Nenhum teste padrão acessa a Pluggy (`SPECS/02` §8) nem
# carrega o segredo. Os valores do terminal ficam em `tests.integracao.ambiente`,
# só para o teste de contrato (`pytest -m pluggy`).
for _variavel in VARIAVEIS_PLUGGY:
    os.environ[_variavel] = ""


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Pula os testes `integracao` sem a planilha de teste e os `pluggy` sem o item Sandbox.

    A planilha vem do terminal ou, sem ela, do `backend/.env` (F-15 Q5); as
    credenciais e o item do teste de contrato, do mesmo jeito (`SPECS/02` §8).
    """
    pulos: dict[str, pytest.MarkDecorator] = {}
    if not ler_planilha_teste(os.environ):
        pulos["integracao"] = pytest.mark.skip(reason=f"{VARIAVEL_PLANILHA_TESTE} não definida")
    if ler_pluggy_de_contrato() is None:
        pulos["pluggy"] = pytest.mark.skip(
            reason="PLUGGY_CLIENT_ID, PLUGGY_CLIENT_SECRET ou PLUGGY_ITEM_ID_TESTE não definidas"
        )
    for item in items:
        for marcador, motivo in pulos.items():
            if marcador in item.keywords:
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


@pytest.fixture
def credencial_real() -> Path:
    """Caminho da credencial para os testes `integracao` (ver `caminho_da_credencial`)."""
    return caminho_da_credencial()
