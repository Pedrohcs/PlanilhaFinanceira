"""`/api/recorrencias` — cadastro, edição e status (REQ-09, RN-09, RN-11; `SPECS/03` §6; F-13)."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.deps import Repositorios, obter_repositorios
from app.domain.datas import mes_anterior, mes_corrente
from app.infra import sheets_client
from app.infra.schema_planilha import ABA_RECORRENCIAS
from app.infra.sheets_client import PlanilhaAberta
from app.main import criar_app
from app.repositories.memoria import (
    CategoriaRepositoryMemoria,
    LancamentoRepositoryMemoria,
    RecorrenciaRepositoryMemoria,
)
from tests.api.test_lancamentos import campos_com_erro, categoria
from tests.planilha_falsa import PlanilhaFalsa

CABECALHO = list(ABA_RECORRENCIAS.colunas)


def entrada(**alteracoes: Any) -> dict[str, Any]:
    dados: dict[str, Any] = {
        "tipo": "GASTO",
        "descricao": "Streaming",
        "valor": 39.9,
        "categoria_id": "assinaturas",
        "forma_pagamento": "CREDITO",
        "dia_do_mes": 10,
        "mes_inicio": "2026-07",
        "mes_fim": None,
    }
    dados.update(alteracoes)
    return dados


def linha(id_: str, descricao: str, **campos: Any) -> list[Any]:
    dados: dict[str, Any] = {
        "id": id_, "tipo": "GASTO", "descricao": descricao, "valor": 39.9,
        "categoria_id": "assinaturas", "forma_pagamento": "CREDITO", "dia_do_mes": 10,
        "mes_inicio": "2026-07", "mes_fim": "", "status": "ATIVA", "ultimo_mes_gerado": "",
        "criado_em": "2026-07-01T09:00:00", "atualizado_em": "2026-07-01T09:00:00",
    }  # fmt: skip
    dados.update(campos)
    return [dados[coluna] for coluna in CABECALHO]


def cliente_com_planilha(
    monkeypatch: pytest.MonkeyPatch, *linhas: list[Any]
) -> tuple[TestClient, PlanilhaFalsa]:
    """Composição real + planilha falsa; o bootstrap cria as outras abas e as categorias."""
    documento = PlanilhaFalsa({ABA_RECORRENCIAS.nome: [CABECALHO, *linhas]})
    monkeypatch.setattr(
        sheets_client,
        "abrir_planilha",
        lambda *_a, **_k: PlanilhaAberta(titulo="Planilha", documento=documento),
    )
    return TestClient(criar_app()), documento


@pytest.fixture
def cliente_memoria() -> Iterator[TestClient]:
    app = criar_app()
    repositorios = Repositorios(
        categorias=CategoriaRepositoryMemoria(
            [
                categoria("assinaturas", "Assinaturas", "GASTO"),
                categoria("velha", "Velha", "GASTO", ativa=False),
                categoria("salario", "Salário", "RECEITA"),
            ]
        ),
        lancamentos=LancamentoRepositoryMemoria(),
        recorrencias=RecorrenciaRepositoryMemoria(),
    )
    app.dependency_overrides[obter_repositorios] = lambda: repositorios
    with TestClient(app) as cliente:
        yield cliente


def test_post_201_formato_e_linha__CA_F13_1(monkeypatch: pytest.MonkeyPatch) -> None:
    """Contrato de `03` §6.3 e uma linha nova na aba `Recorrencias` (`03` §5.3)."""
    cliente, documento = cliente_com_planilha(monkeypatch)

    with cliente:
        resposta = cliente.post("/api/recorrencias", json=entrada(mes_fim="2026-12"))

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert len(corpo["id"]) == 32
    assert corpo | {"id": None, "criado_em": None, "atualizado_em": None} == {
        "id": None,
        "tipo": "GASTO",
        "descricao": "Streaming",
        "valor": 39.9,
        "categoria_id": "assinaturas",
        "forma_pagamento": "CREDITO",
        "dia_do_mes": 10,
        "mes_inicio": "2026-07",
        "mes_fim": "2026-12",
        "status": "ATIVA",
        "ultimo_mes_gerado": None,
        "proximo_mes": "2026-07",
        "criado_em": None,
        "atualizado_em": None,
    }
    assert corpo["criado_em"] == corpo["atualizado_em"]

    linhas = documento.worksheet(ABA_RECORRENCIAS.nome).valores
    assert len(linhas) == 2  # cabeçalho + uma linha
    assert linhas[1] == [
        corpo["id"], "GASTO", "Streaming", 39.9, "assinaturas", "CREDITO", 10, "2026-07",
        "2026-12", "ATIVA", "", corpo["criado_em"], corpo["atualizado_em"],
    ]  # fmt: skip


@pytest.mark.parametrize(
    ("alteracoes", "status", "codigo", "campos"),
    [
        ({"descricao": ""}, 422, "VALIDACAO", ["descricao"]),
        ({"descricao": "x" * 101}, 422, "VALIDACAO", ["descricao"]),
        ({"valor": 0}, 422, "VALIDACAO", ["valor"]),
        ({"valor": 1.234}, 422, "VALIDACAO", ["valor"]),
        ({"dia_do_mes": 0}, 422, "VALIDACAO", ["dia_do_mes"]),
        ({"dia_do_mes": 32}, 422, "VALIDACAO", ["dia_do_mes"]),
        ({"mes_inicio": "2026-13"}, 422, "VALIDACAO", ["mes_inicio"]),
        ({"mes_fim": "julho"}, 422, "VALIDACAO", ["mes_fim"]),
        ({"mes_inicio": "2026-09", "mes_fim": "2026-08"}, 422, "VALIDACAO", ["mes_fim"]),
        ({"forma_pagamento": None}, 422, "VALIDACAO", ["forma_pagamento"]),
        ({"categoria_id": "sumiu"}, 422, "VALIDACAO", ["categoria_id"]),
        ({"categoria_id": "salario"}, 409, "CATEGORIA_TIPO_INCOMPATIVEL", None),
        ({"categoria_id": "velha"}, 409, "CATEGORIA_INATIVA", None),
    ],
)
def test_422_409__CA_F13_2(
    cliente_memoria: TestClient,
    alteracoes: dict[str, Any],
    status: int,
    codigo: str,
    campos: list[str] | None,
) -> None:
    resposta = cliente_memoria.post("/api/recorrencias", json=entrada(**alteracoes))

    assert resposta.status_code == status
    assert resposta.json()["erro"]["codigo"] == codigo
    if campos is not None:
        assert campos_com_erro(resposta) == campos
    assert cliente_memoria.get("/api/recorrencias").json() == []


def test_put_edita_e_404__CA_09_2(cliente_memoria: TestClient) -> None:
    criada = cliente_memoria.post("/api/recorrencias", json=entrada()).json()

    resposta = cliente_memoria.put(
        f"/api/recorrencias/{criada['id']}", json=entrada(valor=44.9, dia_do_mes=31)
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert (corpo["valor"], corpo["dia_do_mes"], corpo["status"]) == (44.9, 31, "ATIVA")
    assert corpo["criado_em"] == criada["criado_em"]

    sumiu = cliente_memoria.put("/api/recorrencias/sumiu", json=entrada())
    assert sumiu.status_code == 404
    assert sumiu.json()["erro"] == {
        "codigo": "NAO_ENCONTRADO",
        "mensagem": "Recorrência não encontrada.",
        "detalhes": [],
    }


def test_patch_status__CA_F13_5(cliente_memoria: TestClient) -> None:
    """Pausar → reativar → encerrar; transições inválidas → 422 no campo `status` (Q3)."""
    id_ = cliente_memoria.post("/api/recorrencias", json=entrada()).json()["id"]
    url = f"/api/recorrencias/{id_}/status"

    pausada = cliente_memoria.patch(url, json={"status": "PAUSADA"})
    assert pausada.status_code == 200
    assert (pausada.json()["status"], pausada.json()["proximo_mes"]) == ("PAUSADA", None)

    repetida = cliente_memoria.patch(url, json={"status": "PAUSADA"})
    assert repetida.status_code == 422
    assert repetida.json()["erro"]["detalhes"] == [
        {"campo": "status", "mensagem": "Não é possível mudar de Pausada para Pausada."}
    ]

    reativada = cliente_memoria.patch(url, json={"status": "ATIVA"})
    assert reativada.status_code == 200
    assert reativada.json()["ultimo_mes_gerado"] is not None  # sem retroativos (RN-11)

    assert cliente_memoria.patch(url, json={"status": "ENCERRADA"}).status_code == 200
    reabrir = cliente_memoria.patch(url, json={"status": "ATIVA"})
    assert reabrir.status_code == 422
    editar = cliente_memoria.put(f"/api/recorrencias/{id_}", json=entrada())
    assert editar.status_code == 422
    assert campos_com_erro(editar) == ["status"]

    invalido = cliente_memoria.patch(url, json={"status": "APAGADA"})
    assert invalido.status_code == 422
    assert campos_com_erro(invalido) == ["status"]

    sumiu = cliente_memoria.patch("/api/recorrencias/sumiu/status", json={"status": "PAUSADA"})
    assert sumiu.status_code == 404


def test_get_ordem_e_linha_invalida_ignorada__CA_09_1(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ordem de F-13 §3.1.6; linha com dia 40 ignorada (RN-14, borda 20)."""
    cliente, _ = cliente_com_planilha(
        monkeypatch,
        linha("enc", "Academia", status="ENCERRADA", ultimo_mes_gerado="2026-03"),
        linha("pau", "Água", status="PAUSADA"),
        linha("ruim", "Quebrada", dia_do_mes=40),
        linha("b", "Streaming", ultimo_mes_gerado="2026-08"),
        linha("a", "aluguel", mes_fim="2026-08", ultimo_mes_gerado="2026-08"),
    )

    with cliente:
        corpo = cliente.get("/api/recorrencias").json()

    assert [(item["id"], item["status"], item["proximo_mes"]) for item in corpo] == [
        ("a", "ATIVA", None),  # vigência terminou (Q4)
        ("b", "ATIVA", "2026-09"),
        ("pau", "PAUSADA", None),
        ("enc", "ENCERRADA", None),
    ]


def test_get_503(cliente: TestClient) -> None:
    resposta = cliente.get("/api/recorrencias")

    assert resposta.status_code == 503
    assert resposta.json()["erro"]["codigo"] == "CREDENCIAIS_INVALIDAS"


# Sincronização (T-029) ----------------------------------------------------------------


def test_sincronizar_uma_insercao_e_sem_escrita_na_repeticao__CA_10_2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CA-F13.9/.10: um `append_rows` com os meses devidos e a marca d'água; repetir não escreve."""
    corrente = mes_corrente()
    anterior = mes_anterior(corrente)
    cliente, documento = cliente_com_planilha(
        monkeypatch,
        linha("r", "Streaming", mes_inicio=anterior, dia_do_mes=31),
        linha("p", "Pausada", mes_inicio=anterior, status="PAUSADA"),
    )

    with cliente:
        escritas_antes = len(documento.escritas)
        resposta = cliente.post("/api/recorrencias/sincronizar")
        primeira = documento.escritas[escritas_antes:]
        repetida = cliente.post("/api/recorrencias/sincronizar")
        lista = cliente.get(f"/api/lancamentos?mes={corrente}").json()
        recorrencias = cliente.get("/api/recorrencias").json()
        escritas_depois = len(documento.escritas)

    assert resposta.status_code == 200
    assert resposta.json() == {
        "lancamentos_gerados": 2,
        "detalhes": [{"recorrencia_id": "r", "meses": [anterior, corrente]}],
    }
    assert [(escrita[0], escrita[1]) for escrita in primeira] == [
        ("append_rows", "Lancamentos"),  # uma única inserção, com os dois meses
        ("update", "Recorrencias"),  # só a recorrência que avançou
    ]
    assert len(primeira[0][2]) == 2
    assert repetida.json() == {"lancamentos_gerados": 0, "detalhes": []}
    assert escritas_depois == escritas_antes + 2  # a repetição não escreveu nada
    [gerado] = lista["itens"]
    assert gerado["recorrencia_id"] == "r"
    assert gerado["data"].startswith(corrente)
    assert {item["id"]: item["ultimo_mes_gerado"] for item in recorrencias} == {
        "r": corrente,
        "p": None,
    }


def test_sincronizar_linha_invalida_ignorada__CA_F13_19(monkeypatch: pytest.MonkeyPatch) -> None:
    """Borda 20: a linha quebrada não derruba a sincronização das outras."""
    cliente, _ = cliente_com_planilha(
        monkeypatch,
        linha("ruim", "Quebrada", dia_do_mes=40, mes_inicio=mes_corrente()),
        linha("boa", "Aluguel", mes_inicio=mes_corrente()),
    )

    with cliente:
        corpo = cliente.post("/api/recorrencias/sincronizar").json()

    assert corpo == {
        "lancamentos_gerados": 1,
        "detalhes": [{"recorrencia_id": "boa", "meses": [mes_corrente()]}],
    }


def test_sincronizar_503__CA_F13_19(cliente: TestClient) -> None:
    resposta = cliente.post("/api/recorrencias/sincronizar")

    assert resposta.status_code == 503
    assert resposta.json()["erro"]["codigo"] == "CREDENCIAIS_INVALIDAS"
