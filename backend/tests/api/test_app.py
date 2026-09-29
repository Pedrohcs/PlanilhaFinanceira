"""Testes da aplicação vazia (CA-F01.5)."""

from fastapi.testclient import TestClient

from app.main import TITULO


def test_openapi_responde__CA_F01_5(cliente: TestClient) -> None:
    """A aplicação sobe e documenta a si mesma."""
    resposta = cliente.get("/openapi.json")

    assert resposta.status_code == 200
    assert resposta.json()["info"]["title"] == TITULO


def test_health_e_a_unica_rota_da_api__CA_F02_8(cliente: TestClient) -> None:
    """Guarda de fronteira: endpoints de negócio só entram em M1.

    Em T-002 este teste exigia nenhuma rota sob `/api`; T-005 acrescentou
    `/api/health`, e ele passa a garantir que nada além dela apareceu.
    """
    caminhos = cliente.get("/openapi.json").json().get("paths", {})

    assert [caminho for caminho in caminhos if caminho.startswith("/api")] == ["/api/health"]


def test_app_sobe_com_planilha_inacessivel__CA_F02_10(cliente: TestClient) -> None:
    """A credencial de teste não existe, então a conexão falha na subida.

    O servidor tem de continuar atendendo (`SPECS/03` §4.5).
    """
    assert cliente.get("/openapi.json").status_code == 200
    saude = cliente.get("/api/health")
    assert saude.status_code == 200
    assert saude.json()["planilha"]["ok"] is False
