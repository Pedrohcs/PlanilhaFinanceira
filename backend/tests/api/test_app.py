"""Testes da aplicação vazia (CA-F01.5)."""

import pytest
from fastapi.testclient import TestClient

from app.infra import sheets_client
from app.infra.sheets_client import PlanilhaAberta
from app.main import TITULO, criar_app
from tests.planilha_falsa import PlanilhaFalsa


def test_openapi_responde__CA_F01_5(cliente: TestClient) -> None:
    """A aplicação sobe e documenta a si mesma."""
    resposta = cliente.get("/openapi.json")

    assert resposta.status_code == 200
    assert resposta.json()["info"]["title"] == TITULO


def test_rotas_da_api_sao_as_do_contrato__CA_F02_8(cliente: TestClient) -> None:
    """Guarda de fronteira: sob `/api` só existe o que `SPECS/03` §6.1 já implementou.

    Em T-002 este teste exigia nenhuma rota sob `/api`; T-005 aceitou só
    `/api/health`; T-013 acrescentou as de categorias; T-015, lançamentos e formas
    de pagamento; T-026, parcelamentos; T-021, resumo mensal; T-024, histórico; T-028,
    recorrências; T-029, sincronização; T-032, recarregar. Cada tarefa que criar endpoint
    atualiza esta lista junto com o contrato.
    """
    esquema = cliente.get("/openapi.json").json().get("paths", {})
    rotas = {
        (metodo.upper(), caminho)
        for caminho, operacoes in esquema.items()
        if caminho.startswith("/api")
        for metodo in operacoes
    }

    assert rotas == {
        ("GET", "/api/health"),
        ("POST", "/api/sistema/recarregar"),
        ("GET", "/api/categorias"),
        ("POST", "/api/categorias"),
        ("PUT", "/api/categorias/{id}"),
        ("DELETE", "/api/categorias/{id}"),
        ("GET", "/api/formas-pagamento"),
        ("GET", "/api/lancamentos"),
        ("POST", "/api/lancamentos"),
        ("PUT", "/api/lancamentos/{id}"),
        ("DELETE", "/api/lancamentos/{id}"),
        ("POST", "/api/parcelamentos"),
        ("DELETE", "/api/parcelamentos/{parcelamento_id}"),
        ("GET", "/api/recorrencias"),
        ("POST", "/api/recorrencias"),
        ("PUT", "/api/recorrencias/{id}"),
        ("PATCH", "/api/recorrencias/{id}/status"),
        ("POST", "/api/recorrencias/sincronizar"),
        ("GET", "/api/resumo/mensal"),
        ("GET", "/api/resumo/historico"),
    }


def test_app_sobe_com_planilha_inacessivel__CA_F02_10(cliente: TestClient) -> None:
    """A credencial de teste não existe, então a conexão falha na subida.

    O servidor tem de continuar atendendo (`SPECS/03` §4.5).
    """
    assert cliente.get("/openapi.json").status_code == 200
    saude = cliente.get("/api/health")
    assert saude.status_code == 200
    assert saude.json()["planilha"]["ok"] is False


def test_lifespan_prepara_planilha_nova__CA_15_1(monkeypatch: pytest.MonkeyPatch) -> None:
    """A aplicação real liga o `bootstrap` à conexão: subir já cria as abas (T-008)."""
    documento = PlanilhaFalsa()
    monkeypatch.setattr(
        sheets_client,
        "abrir_planilha",
        lambda *_a, **_k: PlanilhaAberta(titulo="Planilha", documento=documento),
    )

    with TestClient(criar_app()) as cliente:
        saude = cliente.get("/api/health").json()

    assert saude["status"] == "ok"
    assert documento.nomes_das_abas() == ["Lancamentos", "Categorias", "Recorrencias", "Config"]
    assert len(documento.linhas("Categorias")) == 1 + 15
