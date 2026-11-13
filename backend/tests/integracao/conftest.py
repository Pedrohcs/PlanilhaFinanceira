"""Fixtures da suíte de integração (`SPECS/features/F-15` §3.2).

Só valem para os testes marcados `integracao` — o teste de contrato da Pluggy
(`-m pluggy`), que mora na mesma pasta, não abre a planilha nem espera a cota.
Rodam com `pytest -m integracao` e a planilha de teste definida (terminal ou
`backend/.env`). Antes de qualquer escrita, a trava confere que a planilha de
teste não é a do app; no início e no fim da sessão, as linhas marcadas por
testes (inclusive de uma execução interrompida) são apagadas.
"""

import os
import time
from collections.abc import Iterator
from pathlib import Path

import gspread
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.infra.sheets_client import abrir_planilha
from app.main import criar_app
from tests.integracao.ambiente import (
    MENSAGEM_MESMA_PLANILHA,
    SPREADSHEET_ID_DO_AMBIENTE,
    apagar_linhas_marcadas,
    caminho_da_credencial,
    ler_planilha_teste,
    mesma_planilha_do_app,
    planilhas_do_app,
    segundos_de_espera,
)


@pytest.fixture(scope="session")
def planilha_teste_id() -> str:
    id_ = ler_planilha_teste(os.environ)
    assert id_, "o conftest raiz pula a integração sem planilha de teste"
    return id_


@pytest.fixture(scope="session")
def credencial_teste() -> Path:
    return caminho_da_credencial()


@pytest.fixture(scope="session")
def documento_teste(planilha_teste_id: str, credencial_teste: Path) -> gspread.Spreadsheet:
    """A planilha de teste aberta direto pelo gspread, para conferir e limpar as abas."""
    return abrir_planilha(credencial_teste, planilha_teste_id).documento


@pytest.fixture(scope="session")
def planilha_separada_e_limpa(planilha_teste_id: str) -> Iterator[None]:
    """Trava (CA-F15.8) e varredura das linhas marcadas no início e no fim (CA-F15.9, borda 10).

    A trava vem primeiro e não abre a planilha: com a planilha do app, nada é
    lido nem escrito.
    """
    if mesma_planilha_do_app(planilha_teste_id, planilhas_do_app(SPREADSHEET_ID_DO_AMBIENTE)):
        pytest.exit(MENSAGEM_MESMA_PLANILHA, returncode=pytest.ExitCode.USAGE_ERROR)
    documento = abrir_planilha(caminho_da_credencial(), planilha_teste_id).documento
    apagar_linhas_marcadas(documento)
    yield
    apagar_linhas_marcadas(documento)


_fim_do_teste_anterior: list[float] = []


@pytest.fixture(autouse=True)
def respeitar_cota_do_google(request: pytest.FixtureRequest) -> Iterator[None]:
    """Cada teste começa com a janela de cota de leituras zerada (F-15 §3.2.7).

    Pede a fixture de sessão antes, para a trava e a varredura virem antes da
    espera — e só para teste `integracao`: o de contrato da Pluggy passa direto.
    """
    if request.node.get_closest_marker("integracao") is None:
        yield
        return
    request.getfixturevalue("planilha_separada_e_limpa")
    espera = segundos_de_espera(
        _fim_do_teste_anterior[-1] if _fim_do_teste_anterior else None, time.monotonic()
    )
    if espera:
        time.sleep(espera)
    try:
        yield
    finally:
        _fim_do_teste_anterior.append(time.monotonic())


@pytest.fixture
def settings_teste(planilha_teste_id: str, credencial_teste: Path) -> Settings:
    return Settings(spreadsheet_id=planilha_teste_id, google_credentials_path=str(credencial_teste))


@pytest.fixture
def cliente_teste(settings_teste: Settings) -> Iterator[TestClient]:
    """O app real contra a planilha de teste: lifespan, bootstrap, cache e serviços de verdade."""
    with TestClient(criar_app(settings_teste)) as cliente:
        saude = cliente.get("/api/health").json()
        assert saude["planilha"]["ok"] is True, saude
        yield cliente


def _categoria_ativa(cliente: TestClient, tipo: str) -> str:
    categorias = cliente.get("/api/categorias").json()
    ativas = [c["id"] for c in categorias if c["tipo"] == tipo and c["ativa"]]
    assert ativas, f"A planilha de teste não tem categoria ativa de {tipo}."
    return ativas[0]


@pytest.fixture
def categoria_gasto_id(cliente_teste: TestClient) -> str:
    """Uma categoria de gasto ativa (a seed de RN-15 garante)."""
    return _categoria_ativa(cliente_teste, "GASTO")


@pytest.fixture
def categoria_receita_id(cliente_teste: TestClient) -> str:
    return _categoria_ativa(cliente_teste, "RECEITA")
