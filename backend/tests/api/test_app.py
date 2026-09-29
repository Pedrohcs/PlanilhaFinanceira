"""Testes da aplicação vazia (CA-F01.5)."""

from fastapi.testclient import TestClient

from app.main import TITULO


def test_openapi_responde__CA_F01_5(cliente: TestClient) -> None:
    """A aplicação sobe e documenta a si mesma."""
    resposta = cliente.get("/openapi.json")

    assert resposta.status_code == 200
    assert resposta.json()["info"]["title"] == TITULO


def test_sem_rotas_de_negocio__CA_F01_5(cliente: TestClient) -> None:
    """T-002 não cria endpoints sob `/api` — `/api/health` é de T-005 (F-01 §6)."""
    caminhos = cliente.get("/openapi.json").json().get("paths", {})

    assert [caminho for caminho in caminhos if caminho.startswith("/api")] == []
