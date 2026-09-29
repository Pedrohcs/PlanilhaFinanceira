"""Testes de CORS: só o frontend local é aceito (CA-F01.11, RNF-05)."""

from fastapi.testclient import TestClient

CABECALHO = "access-control-allow-origin"


def test_cors_permite_localhost_4200__CA_F01_11(cliente: TestClient) -> None:
    """A origem do `ng serve` é liberada."""
    resposta = cliente.get("/openapi.json", headers={"Origin": "http://localhost:4200"})

    assert resposta.headers[CABECALHO] == "http://localhost:4200"


def test_cors_rejeita_outra_origem__CA_F01_11(cliente: TestClient) -> None:
    """Qualquer outra origem não recebe a liberação."""
    resposta = cliente.get("/openapi.json", headers={"Origin": "http://exemplo.com"})

    assert CABECALHO not in resposta.headers
