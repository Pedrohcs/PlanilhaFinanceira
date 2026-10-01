"""Resumo do mês e histórico (REQ-12, dados de REQ-13, REQ-14, RN-03, RN-13, RN-16).

Tudo em `Decimal` sobre uma leitura de cada aba (pelo cache). Os totais vêm
da mesma `totalizar` da listagem, para as telas nunca divergirem (CA-12.1):
o mês do histórico tem os mesmos números do resumo mensal (F-11 §3.1.3).
Depende só de `domain`, `repositories.base` e dos serviços de categorias e
lançamentos (chave de nome e totais).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from itertools import accumulate

from app.domain.datas import ano_e_mes, dias_no_mes, mes_corrente, mes_de, meses_entre, somar_meses
from app.domain.dinheiro import CENTAVO
from app.domain.enums import FormaPagamento, TipoLancamento
from app.domain.erros import ErroValidacao
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

MESES_DO_HISTORICO_PADRAO = 12  # REQ-14
MESES_DO_HISTORICO_MAX = 36  # F-11 Q2
MENSAGEM_PERIODO_INCOMPLETO = "Informe o início e o fim do período."
MENSAGEM_PERIODO_INVERTIDO = "O fim do período deve ser igual ou posterior ao início."
MENSAGEM_PERIODO_LONGO = f"O período pode ter no máximo {MESES_DO_HISTORICO_MAX} meses."


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


@dataclass(frozen=True)
class TotaisDoMes:
    mes: str
    totais: Totais


@dataclass(frozen=True)
class CategoriaNoHistorico:
    categoria_id: str
    nome: str
    cor: str
    valores: list[Decimal]  # um por mês, na ordem de `HistoricoDoPeriodo.meses`


@dataclass(frozen=True)
class HistoricoDoPeriodo:
    inicio: str
    fim: str
    meses: list[TotaisDoMes]
    por_categoria: list[CategoriaNoHistorico]
    total_gastos_periodo: Decimal
    media_mensal_gastos: Decimal
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

    def historico(
        self, inicio: str | None = None, fim: str | None = None, hoje: date | None = None
    ) -> HistoricoDoPeriodo:
        """Totais mês a mês, gastos por categoria alinhados aos meses, total e média (F-11)."""
        inicio, fim = periodo_do_historico(inicio, fim, hoje)
        meses = meses_entre(inicio, fim)
        leitura = self._lancamentos.listar()
        categorias = {c.id: c for c in self._categorias.listar().itens}
        por_mes: dict[str, list[Lancamento]] = {mes: [] for mes in meses}
        for item in leitura.itens:
            do_mes = por_mes.get(mes_de(item.data))  # RN-03
            if do_mes is not None:
                do_mes.append(item)
        totais = [TotaisDoMes(mes, totalizar(por_mes[mes])) for mes in meses]
        total_gastos = sum((item.totais.gastos for item in totais), ZERO)
        return HistoricoDoPeriodo(
            inicio=inicio,
            fim=fim,
            meses=totais,
            por_categoria=_por_categoria_no_periodo(por_mes, categorias),
            total_gastos_periodo=total_gastos,
            # Todos os meses do período no divisor, inclusive zerados e futuros (F-11 Q3).
            media_mensal_gastos=(total_gastos / len(meses)).quantize(CENTAVO, ROUND_HALF_UP),
            linhas_ignoradas=leitura.linhas_ignoradas,
        )


def periodo_do_historico(
    inicio: str | None, fim: str | None, hoje: date | None = None
) -> tuple[str, str]:
    """Período pedido, ou os 12 meses até o corrente; as duas pontas ou nenhuma (F-11 Q2)."""
    if inicio is None and fim is None:
        fim = mes_corrente(hoje)
        ano, numero = ano_e_mes(fim)
        return mes_de(somar_meses(date(ano, numero, 1), 1 - MESES_DO_HISTORICO_PADRAO)), fim
    if inicio is None:
        raise ErroValidacao.no_campo("inicio", MENSAGEM_PERIODO_INCOMPLETO)
    if fim is None:
        raise ErroValidacao.no_campo("fim", MENSAGEM_PERIODO_INCOMPLETO)
    if fim < inicio:
        raise ErroValidacao.no_campo("fim", MENSAGEM_PERIODO_INVERTIDO)
    if len(meses_entre(inicio, fim)) > MESES_DO_HISTORICO_MAX:
        raise ErroValidacao.no_campo("fim", MENSAGEM_PERIODO_LONGO)
    return inicio, fim


def percentual(parte: Decimal, total: Decimal) -> Decimal:
    """0 a 100 com 1 casa, cada linha arredondada sozinha (F-09 Q1)."""
    return (parte / total * CEM).quantize(UMA_CASA, rounding=ROUND_HALF_UP)


def _somar_por[C](gastos: list[Lancamento], chave: Callable[[Lancamento], C]) -> dict[C, Decimal]:
    somas: dict[C, Decimal] = {}
    for gasto in gastos:
        somas[chave(gasto)] = somas.get(chave(gasto), ZERO) + gasto.valor
    return somas


def _nome_e_cor(categoria_id: str, categorias: dict[str, Categoria]) -> tuple[str, str]:
    """Nome e cor atuais (CA-11.2); categoria apagada à mão fica cinza (F-07 §3.1.6)."""
    categoria = categorias.get(categoria_id)
    if categoria is None:
        return NOME_CATEGORIA_AUSENTE, COR_CATEGORIA_AUSENTE
    return categoria.nome, categoria.cor


def _por_categoria(
    gastos: list[Lancamento], categorias: dict[str, Categoria], total: Decimal
) -> list[GastoPorCategoria]:
    itens = []
    for categoria_id, soma in _somar_por(gastos, lambda gasto: gasto.categoria_id).items():
        nome, cor = _nome_e_cor(categoria_id, categorias)
        itens.append(GastoPorCategoria(categoria_id, nome, cor, soma, percentual(soma, total)))
    # Maior primeiro; empate pelo nome sem acento/caixa (F-09 §3.1.4).
    return sorted(itens, key=lambda item: (-item.total, chave_do_nome(item.nome)))


def _por_categoria_no_periodo(
    por_mes: dict[str, list[Lancamento]], categorias: dict[str, Categoria]
) -> list[CategoriaNoHistorico]:
    """Só gastos; um valor por mês, 0 onde a categoria não teve gasto (F-11 §3.1.4)."""
    valores: dict[str, list[Decimal]] = {}
    for posicao, lancamentos in enumerate(por_mes.values()):
        for gasto in lancamentos:
            if gasto.tipo is TipoLancamento.GASTO:
                da_categoria = valores.setdefault(gasto.categoria_id, [ZERO] * len(por_mes))
                da_categoria[posicao] += gasto.valor
    itens = [
        CategoriaNoHistorico(categoria_id, *_nome_e_cor(categoria_id, categorias), serie)
        for categoria_id, serie in valores.items()
    ]
    # Maior total no período primeiro; empate pelo nome sem acento/caixa (F-11 §3.1.4).
    return sorted(itens, key=lambda item: (-sum(item.valores), chave_do_nome(item.nome)))


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
