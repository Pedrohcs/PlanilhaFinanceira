"""Resumo do mês (REQ-12, dados de REQ-13, RN-03, RN-13, RN-16; F-09 §3.1).

Tudo em `Decimal` sobre uma leitura de cada aba (pelo cache). Os totais vêm
da mesma `totalizar` da listagem, para as duas telas nunca divergirem
(CA-12.1). Depende só de `domain`, `repositories.base` e dos serviços de
categorias e lançamentos (chave de nome e totais).
"""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from itertools import accumulate

from app.domain.datas import dias_no_mes, mes_de
from app.domain.enums import FormaPagamento, TipoLancamento
from app.domain.modelos import Categoria, Lancamento
from app.repositories.base import CategoriaRepository, LancamentoRepository
from app.services.categoria_service import chave_do_nome
from app.services.lancamento_service import (
    COR_CATEGORIA_AUSENTE,
    NOME_CATEGORIA_AUSENTE,
    ZERO,
    Totais,
    totalizar,
)

CEM = Decimal(100)
UMA_CASA = Decimal("0.1")
_ORDEM_DAS_FORMAS = {forma: posicao for posicao, forma in enumerate(FormaPagamento)}


@dataclass(frozen=True)
class GastoPorCategoria:
    categoria_id: str
    nome: str
    cor: str
    total: Decimal
    percentual: Decimal


@dataclass(frozen=True)
class GastoPorForma:
    forma_pagamento: FormaPagamento
    nome: str
    total: Decimal
    percentual: Decimal


@dataclass(frozen=True)
class ResumoDoMes:
    mes: str
    totais: Totais
    por_categoria: list[GastoPorCategoria]
    por_forma_pagamento: list[GastoPorForma]
    gasto_acumulado_diario: list[Decimal]  # índice 0 = dia 1
    linhas_ignoradas: int


class ResumoService:
    def __init__(self, categorias: CategoriaRepository, lancamentos: LancamentoRepository) -> None:
        self._categorias = categorias
        self._lancamentos = lancamentos

    def mensal(self, mes: str) -> ResumoDoMes:
        """Totais, gastos por categoria e por forma (com %) e acumulado diário."""
        leitura = self._lancamentos.listar()
        categorias = {c.id: c for c in self._categorias.listar().itens}
        do_mes = [item for item in leitura.itens if mes_de(item.data) == mes]  # RN-03
        gastos = [item for item in do_mes if item.tipo is TipoLancamento.GASTO]
        totais = totalizar(do_mes)
        return ResumoDoMes(
            mes=mes,
            totais=totais,
            por_categoria=_por_categoria(gastos, categorias, totais.gastos),
            por_forma_pagamento=_por_forma(gastos, totais.gastos),
            gasto_acumulado_diario=_acumulado_diario(gastos, dias_no_mes(mes)),
            linhas_ignoradas=leitura.linhas_ignoradas,
        )


def percentual(parte: Decimal, total: Decimal) -> Decimal:
    """0 a 100 com 1 casa, cada linha arredondada sozinha (F-09 Q1)."""
    return (parte / total * CEM).quantize(UMA_CASA, rounding=ROUND_HALF_UP)


def _somar_por[C](gastos: list[Lancamento], chave: Callable[[Lancamento], C]) -> dict[C, Decimal]:
    somas: dict[C, Decimal] = {}
    for gasto in gastos:
        somas[chave(gasto)] = somas.get(chave(gasto), ZERO) + gasto.valor
    return somas


def _por_categoria(
    gastos: list[Lancamento], categorias: dict[str, Categoria], total: Decimal
) -> list[GastoPorCategoria]:
    itens = []
    for categoria_id, soma in _somar_por(gastos, lambda gasto: gasto.categoria_id).items():
        categoria = categorias.get(categoria_id)  # nome e cor atuais (CA-11.2)
        nome = categoria.nome if categoria else NOME_CATEGORIA_AUSENTE
        cor = categoria.cor if categoria else COR_CATEGORIA_AUSENTE
        itens.append(GastoPorCategoria(categoria_id, nome, cor, soma, percentual(soma, total)))
    # Maior primeiro; empate pelo nome sem acento/caixa (F-09 §3.1.4).
    return sorted(itens, key=lambda item: (-item.total, chave_do_nome(item.nome)))


def _por_forma(gastos: list[Lancamento], total: Decimal) -> list[GastoPorForma]:
    # Todo gasto tem forma (RN-05; o modelo recusa gasto sem ela).
    somas = _somar_por(gastos, lambda gasto: gasto.forma_pagamento)
    itens = [
        GastoPorForma(forma, forma.rotulo, soma, percentual(soma, total))
        for forma, soma in somas.items()
        if forma is not None
    ]
    # Maior primeiro; empate na ordem de RN-05 (F-09 §3.1.5).
    return sorted(itens, key=lambda item: (-item.total, _ORDEM_DAS_FORMAS[item.forma_pagamento]))


def _acumulado_diario(gastos: list[Lancamento], dias: int) -> list[Decimal]:
    """Todos os dias do mês (F-09 Q2): soma dos gastos com data até o dia, inclusive."""
    por_dia = [ZERO] * dias
    for gasto in gastos:
        por_dia[gasto.data.day - 1] += gasto.valor
    return list(accumulate(por_dia))
