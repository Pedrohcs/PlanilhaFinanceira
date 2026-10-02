"""`POST /api/sistema/recarregar` (RN-14; F-14 §3.3.1)."""

import pytest
from fastapi.testclient import TestClient

from app.infra import sheets_client
from app.infra.sheets_client import PlanilhaAberta
from app.main import criar_app
from tests.planilha_falsa import PlanilhaFalsa


def test_recarregar_204_invalida_cache__CA_F14_10(monkeypatch: pytest.MonkeyPatch) -> None:
    """Borda 2: edição manual aparece logo depois, sem esperar o TTL de 30 s."""
    documento = PlanilhaFalsa()
    monkeypatch.setattr(
        sheets_client,
        "abrir_planilha",
        lambda *_a, **_k: PlanilhaAberta(titulo="Planilha", documento=documento),
    )

    with TestClient(criar_app()) as cliente:
        cliente.get("/api/lancamentos?mes=2026-09")
        cliente.get("/api/lancamentos?mes=2026-09")  # dentro do TTL: do cache
        assert documento.leituras == {"Lancamentos": 1, "Categorias": 1}
        escritas_antes = len(documento.escritas)

        resposta = cliente.post("/api/sistema/recarregar")

        assert resposta.status_code == 204
        assert resposta.content == b""
        # Só esvaziou o cache: nenhuma leitura nem escrita no Google.
        assert documento.leituras == {"Lancamentos": 1, "Categorias": 1}
        assert len(documento.escritas) == escritas_antes

        cliente.get("/api/lancamentos?mes=2026-09")

    assert documento.leituras == {"Lancamentos": 2, "Categorias": 2}


def test_recarregar_sem_planilha_204__CA_F14_11(cliente: TestClient) -> None:
    """Borda 5: a credencial de teste não existe, a planilha está inacessível."""
    assert cliente.get("/api/health").json()["planilha"]["ok"] is False

    assert cliente.post("/api/sistema/recarregar").status_code == 204
