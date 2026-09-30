"""`GET /api/formas-pagamento` (RN-05, P-01; F-06 §3.6)."""

from fastapi.testclient import TestClient


def test_seis_formas_na_ordem__CA_F06_7(cliente: TestClient) -> None:
    """A fixture `cliente` não tem planilha: a rota não depende dela."""
    resposta = cliente.get("/api/formas-pagamento")

    assert resposta.status_code == 200
    assert resposta.json() == [
        {"codigo": "PIX", "nome": "Pix"},
        {"codigo": "CREDITO", "nome": "Cartão de crédito"},
        {"codigo": "DEBITO", "nome": "Cartão de débito"},
        {"codigo": "DINHEIRO", "nome": "Dinheiro"},
        {"codigo": "BOLETO", "nome": "Boleto"},
        {"codigo": "TRANSFERENCIA", "nome": "Transferência"},
    ]
