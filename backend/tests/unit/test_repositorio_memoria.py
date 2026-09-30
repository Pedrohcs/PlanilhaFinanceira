"""Repositório em memória (F-03 §3.7)."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.domain.enums import FormaPagamento, TipoLancamento
from app.domain.erros import NaoEncontrado
from app.domain.modelos import Lancamento
from app.repositories.memoria import LancamentoRepositoryMemoria


def lancamento(id_: str, descricao: str = "Almoço") -> Lancamento:
    return Lancamento(
        id=id_,
        data=date(2026, 9, 29),
        tipo=TipoLancamento.GASTO,
        descricao=descricao,
        valor=Decimal("42.50"),
        categoria_id="alimentacao",
        forma_pagamento=FormaPagamento.PIX,
        criado_em=datetime(2026, 9, 29, 10, 15),
        atualizado_em=datetime(2026, 9, 29, 10, 15),
    )


def test_obter_inexistente_levanta_nao_encontrado__CA_F03_21() -> None:
    repositorio = LancamentoRepositoryMemoria([lancamento("a")])

    with pytest.raises(NaoEncontrado) as erro:
        repositorio.obter("nao-existe")

    assert erro.value.codigo == "NAO_ENCONTRADO"
    with pytest.raises(NaoEncontrado):
        repositorio.atualizar(lancamento("nao-existe"))


def test_linhas_ignoradas_sempre_zero() -> None:
    assert LancamentoRepositoryMemoria([lancamento("a")]).listar().linhas_ignoradas == 0


def test_remover_tudo_ou_nada() -> None:
    repositorio = LancamentoRepositoryMemoria([lancamento("a"), lancamento("b")])

    with pytest.raises(NaoEncontrado):
        repositorio.remover(["a", "nao-existe"])

    assert [item.id for item in repositorio.listar().itens] == ["a", "b"]


def test_atualizar_mantem_a_posicao() -> None:
    repositorio = LancamentoRepositoryMemoria([lancamento("a"), lancamento("b")])

    repositorio.atualizar(lancamento("a", descricao="Alterado"))

    assert [item.descricao for item in repositorio.listar().itens] == ["Alterado", "Almoço"]


def test_listar_devolve_copia_da_lista() -> None:
    repositorio = LancamentoRepositoryMemoria([lancamento("a")])

    repositorio.listar().itens.clear()

    assert len(repositorio.listar().itens) == 1
