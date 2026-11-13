"""Contrato com a API da Pluggy, só leitura, contra o item **Sandbox** (`SPECS/02` §8, §11.3–11.4).

Roda só com `pytest -m pluggy` e com `PLUGGY_CLIENT_ID`, `PLUGGY_CLIENT_SECRET`
e `PLUGGY_ITEM_ID_TESTE` definidas (terminal ou `backend/.env`); sem elas, o
`conftest` raiz pula. Não toca a planilha. Confere que o cliente autentica, lê a
conexão, os cartões e as transações paginadas, e que cada campo chega no tipo
esperado — nenhum valor é impresso.
"""

from collections.abc import Iterator
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from app.domain.enums import SituacaoConexao
from app.infra.pluggy_client import PluggyClient
from tests.integracao.ambiente import PluggyDeContrato, ler_pluggy_de_contrato

pytestmark = pytest.mark.pluggy

ITEM_INEXISTENTE = "00000000-0000-4000-8000-000000000000"
DIAS_DE_HISTORICO = 365


@pytest.fixture(scope="module")
def contrato() -> PluggyDeContrato:
    configuracao = ler_pluggy_de_contrato()
    assert configuracao, "o conftest raiz pula o teste de contrato sem as variáveis"
    return configuracao


@pytest.fixture(scope="module")
def cliente(contrato: PluggyDeContrato) -> Iterator[PluggyClient]:
    cliente = PluggyClient(contrato.client_id, contrato.client_secret.get_secret_value())
    yield cliente
    cliente.fechar()


def test_conexao_do_item_sandbox(cliente: PluggyClient, contrato: PluggyDeContrato) -> None:
    conexao = cliente.obter_conexao(contrato.item_id)

    assert conexao.situacao is not SituacaoConexao.NAO_ENCONTRADA, "confira PLUGGY_ITEM_ID_TESTE"
    assert conexao.banco
    assert conexao.ultima_atualizacao is None or conexao.ultima_atualizacao.tzinfo is None


def test_item_inexistente_vem_como_nao_encontrada(cliente: PluggyClient) -> None:
    """`GET /items/{id}` → 404 (ou 400 para id inválido) não pode virar exceção de rede."""
    conexao = cliente.obter_conexao(ITEM_INEXISTENTE)

    assert conexao.situacao is SituacaoConexao.NAO_ENCONTRADA


def test_cartoes_e_transacoes_paginadas(cliente: PluggyClient, contrato: PluggyDeContrato) -> None:
    cartoes = cliente.listar_cartoes(contrato.item_id)
    assert cartoes, "o item Sandbox deveria ter ao menos um cartão de crédito"

    desde = date.today() - timedelta(days=DIAS_DE_HISTORICO)
    total = 0
    for cartao in cartoes:
        assert cartao.id and cartao.nome
        assert cartao.final is None or (cartao.final.isdigit() and len(cartao.final) <= 4)
        transacoes = cliente.listar_transacoes(cartao.id, desde)
        total += len(transacoes)
        assert len({t.id for t in transacoes}) == len(transacoes)  # páginas sem repetição
        for transacao in transacoes:
            assert transacao.id
            assert isinstance(transacao.instante, datetime) and transacao.instante.tzinfo
            assert isinstance(transacao.valor, Decimal)
            assert transacao.status in ("PENDING", "POSTED")
            assert transacao.instante.date() >= desde - timedelta(days=1)  # `dateFrom` vale
    assert total > 0, "o item Sandbox deveria ter transações no último ano"
