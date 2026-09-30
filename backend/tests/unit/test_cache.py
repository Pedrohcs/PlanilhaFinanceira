"""Cache por aba com TTL e invalidação (`SPECS/02` §5.5; F-03 §3.5)."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.domain.enums import FormaPagamento, TipoLancamento
from app.domain.modelos import Lancamento
from app.infra.cache import CacheAbas
from app.infra.schema_planilha import ABA_LANCAMENTOS
from app.repositories.planilha import LancamentoRepositoryPlanilha
from tests.planilha_falsa import FonteFalsa, PlanilhaFalsa


class Relogio:
    def __init__(self) -> None:
        self.agora = 1000.0

    def __call__(self) -> float:
        return self.agora


class Contador:
    def __init__(self) -> None:
        self.chamadas = 0

    def __call__(self) -> int:
        self.chamadas += 1
        return self.chamadas


def novo_lancamento() -> Lancamento:
    return Lancamento(
        id="novo",
        data=date(2026, 9, 29),
        tipo=TipoLancamento.GASTO,
        descricao="Almoço",
        valor=Decimal("42.50"),
        categoria_id="alimentacao",
        forma_pagamento=FormaPagamento.PIX,
        criado_em=datetime(2026, 9, 29, 10, 15),
        atualizado_em=datetime(2026, 9, 29, 10, 15),
    )


def test_segunda_leitura_no_ttl_nao_chama_o_google__CA_F03_18() -> None:
    """Dentro do TTL, uma chamada; passado o TTL, duas."""
    relogio = Relogio()
    planilha = PlanilhaFalsa({"Lancamentos": [list(ABA_LANCAMENTOS.colunas)]})
    repositorio = LancamentoRepositoryPlanilha(FonteFalsa(planilha), CacheAbas(30, relogio=relogio))

    repositorio.listar()
    relogio.agora += 29.9
    repositorio.listar()
    assert planilha.leituras["Lancamentos"] == 1

    relogio.agora += 0.1
    repositorio.listar()
    assert planilha.leituras["Lancamentos"] == 2


def test_escrita_invalida_o_cache_da_aba__CA_F03_17() -> None:
    """A leitura seguinte a uma escrita vai ao Google e já vê o item novo."""
    planilha = PlanilhaFalsa({"Lancamentos": [list(ABA_LANCAMENTOS.colunas)]})
    repositorio = LancamentoRepositoryPlanilha(FonteFalsa(planilha), CacheAbas(30))
    assert repositorio.listar().itens == []

    repositorio.inserir([novo_lancamento()])

    assert [item.id for item in repositorio.listar().itens] == ["novo"]
    assert planilha.leituras["Lancamentos"] == 2


def test_escrita_que_falha_tambem_invalida() -> None:
    """Se a escrita falhar no meio, o cache não pode continuar servindo o "antes"."""
    planilha = PlanilhaFalsa({"Lancamentos": [list(ABA_LANCAMENTOS.colunas)]})
    repositorio = LancamentoRepositoryPlanilha(FonteFalsa(planilha), CacheAbas(30))
    repositorio.listar()

    planilha.falhar_em = "append_rows"
    with pytest.raises(RuntimeError):
        repositorio.inserir([novo_lancamento()])

    repositorio.listar()
    assert planilha.leituras["Lancamentos"] == 2


def test_carrega_uma_vez_dentro_do_ttl() -> None:
    cache = CacheAbas(30, relogio=Relogio())
    carregar = Contador()

    assert cache.obter("Lancamentos", carregar) == 1
    assert cache.obter("Lancamentos", carregar) == 1
    assert carregar.chamadas == 1


def test_abas_tem_entradas_independentes() -> None:
    cache = CacheAbas(30, relogio=Relogio())
    cache.obter("Lancamentos", lambda: "lancamentos")
    cache.obter("Categorias", lambda: "categorias")

    cache.invalidar("Lancamentos")

    assert cache.obter("Lancamentos", lambda: "relido") == "relido"
    assert cache.obter("Categorias", lambda: "relido") == "categorias"


def test_invalidar_tudo__F03_3_5_3() -> None:
    """O "recarregar" de T-032: todas as abas voltam a ser lidas."""
    cache = CacheAbas(30, relogio=Relogio())
    cache.obter("Lancamentos", lambda: "velho")
    cache.obter("Categorias", lambda: "velho")

    cache.invalidar_tudo()

    assert cache.obter("Lancamentos", lambda: "novo") == "novo"
    assert cache.obter("Categorias", lambda: "novo") == "novo"


def test_leitura_iniciada_antes_da_escrita_nao_fica_no_cache__F03_3_5_4() -> None:
    """Corrida: a escrita invalida enquanto uma leitura lenta está em curso."""
    cache = CacheAbas(30, relogio=Relogio())

    def carregar_lento() -> str:
        cache.invalidar("Lancamentos")  # uma escrita acontece durante a leitura
        return "velho"

    assert cache.obter("Lancamentos", carregar_lento) == "velho"
    assert cache.obter("Lancamentos", lambda: "novo") == "novo"
