"""Regras de lançamentos (REQ-01..03, RN-01..06, RN-13; F-06 §3.5, F-07 §3.1).

Os formatos de campo (valor com 2 casas, descrição de 1 a 100…) são
garantidos na entrada da API e no modelo de domínio; aqui ficam as regras que
dependem de outros dados — a categoria (RN-04) — e a obrigatoriedade da forma
de pagamento no gasto (RN-05). Depende só de `domain` e `repositories.base`.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from app.domain.datas import agora, mes_de
from app.domain.dinheiro import CENTAVO
from app.domain.enums import FormaPagamento, TipoLancamento
from app.domain.erros import CategoriaInativa, CategoriaTipoIncompativel, ErroValidacao
from app.domain.modelos import Categoria, Lancamento
from app.repositories.base import CategoriaRepository, LancamentoRepository

MENSAGEM_CATEGORIA_INEXISTENTE = "Categoria não encontrada."
MENSAGEM_FORMA_OBRIGATORIA = "Informe a forma de pagamento."
# Lançamento cuja categoria foi apagada à mão na planilha (F-07 §3.1.6, RN-14).
NOME_CATEGORIA_AUSENTE = "Categoria não encontrada"
COR_CATEGORIA_AUSENTE = "#9E9E9E"
ZERO = Decimal("0.00")


@dataclass(frozen=True)
class LancamentoComCategoria:
    """Lançamento com o nome e a cor **atuais** da categoria (`03` §6.3, CA-11.2)."""

    lancamento: Lancamento
    categoria_nome: str
    categoria_cor: str


@dataclass(frozen=True)
class Totais:
    """Somas do que foi listado, em centavos exatos (RN-13, RN-16)."""

    gastos: Decimal
    receitas: Decimal
    saldo: Decimal


@dataclass(frozen=True)
class ListaDoMes:
    mes: str
    itens: list[LancamentoComCategoria]
    totais: Totais
    linhas_ignoradas: int


def totalizar(lancamentos: list[Lancamento]) -> Totais:
    """Gastos, receitas e saldo = receitas − gastos (RN-13), em `Decimal` (RN-16)."""
    gastos = sum((item.valor for item in lancamentos if item.tipo is TipoLancamento.GASTO), ZERO)
    receitas = sum(
        (item.valor for item in lancamentos if item.tipo is TipoLancamento.RECEITA), ZERO
    )
    return Totais(
        gastos=gastos.quantize(CENTAVO),
        receitas=receitas.quantize(CENTAVO),
        saldo=(receitas - gastos).quantize(CENTAVO),
    )


def gerar_id() -> str:
    """`uuid4().hex` para lançamentos (`SPECS/02` §3)."""
    return uuid4().hex


class LancamentoService:
    def __init__(
        self,
        categorias: CategoriaRepository,
        lancamentos: LancamentoRepository,
        *,
        relogio: Callable[[], datetime] = agora,
        novo_id: Callable[[], str] = gerar_id,
    ) -> None:
        self._categorias = categorias
        self._lancamentos = lancamentos
        self._relogio = relogio
        self._novo_id = novo_id

    def criar(
        self,
        *,
        data: date,
        tipo: TipoLancamento,
        descricao: str,
        valor: Decimal,
        categoria_id: str,
        forma_pagamento: FormaPagamento | None,
        observacao: str | None,
    ) -> LancamentoComCategoria:
        categoria = self._categoria_para(categoria_id, tipo)
        if tipo is TipoLancamento.GASTO and forma_pagamento is None:
            raise ErroValidacao.no_campo("forma_pagamento", MENSAGEM_FORMA_OBRIGATORIA)

        instante = self._relogio()
        lancamento = Lancamento(
            id=self._novo_id(),
            data=data,
            tipo=tipo,
            descricao=descricao,
            valor=valor,
            categoria_id=categoria.id,
            forma_pagamento=forma_pagamento,
            observacao=observacao,
            criado_em=instante,
            atualizado_em=instante,
        )
        self._lancamentos.inserir([lancamento])
        return LancamentoComCategoria(lancamento, categoria.nome, categoria.cor)

    def listar(
        self,
        mes: str,
        *,
        tipo: TipoLancamento | None = None,
        categoria_id: str | None = None,
        forma_pagamento: FormaPagamento | None = None,
    ) -> ListaDoMes:
        """Lançamentos do mês de referência (RN-03), filtrados (E) e totalizados.

        Uma leitura de cada aba, pelo cache; o resto é memória (`02` §5.5).
        """
        leitura = self._lancamentos.listar()
        categorias = {c.id: c for c in self._categorias.listar().itens}
        selecionados = [
            lancamento
            for lancamento in leitura.itens
            if mes_de(lancamento.data) == mes
            and (tipo is None or lancamento.tipo == tipo)
            and (categoria_id is None or lancamento.categoria_id == categoria_id)
            and (forma_pagamento is None or lancamento.forma_pagamento == forma_pagamento)
        ]
        # Mais recente primeiro; na mesma data, o registrado por último (F-07 §3.1.4).
        selecionados.sort(key=lambda item: (item.data, item.criado_em, item.id), reverse=True)
        return ListaDoMes(
            mes=mes,
            itens=[_com_categoria(lancamento, categorias) for lancamento in selecionados],
            totais=totalizar(selecionados),
            linhas_ignoradas=leitura.linhas_ignoradas,
        )

    def _categoria_para(self, categoria_id: str, tipo: TipoLancamento) -> Categoria:
        """A categoria existe, é do mesmo tipo e está ativa (RN-04)."""
        for categoria in self._categorias.listar().itens:
            if categoria.id == categoria_id:
                break
        else:
            raise ErroValidacao.no_campo("categoria_id", MENSAGEM_CATEGORIA_INEXISTENTE)
        if categoria.tipo != tipo:
            raise CategoriaTipoIncompativel.para(categoria.nome, categoria.tipo, tipo)
        if not categoria.ativa:
            raise CategoriaInativa.para(categoria.nome)
        return categoria


def _com_categoria(
    lancamento: Lancamento, categorias: dict[str, Categoria]
) -> LancamentoComCategoria:
    categoria = categorias.get(lancamento.categoria_id)
    if categoria is None:
        return LancamentoComCategoria(lancamento, NOME_CATEGORIA_AUSENTE, COR_CATEGORIA_AUSENTE)
    return LancamentoComCategoria(lancamento, categoria.nome, categoria.cor)
