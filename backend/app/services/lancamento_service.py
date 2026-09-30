"""Regras de lançamentos (REQ-01, REQ-02, RN-01..06; F-06 §3.5).

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

from app.domain.datas import agora
from app.domain.enums import FormaPagamento, TipoLancamento
from app.domain.erros import CategoriaInativa, CategoriaTipoIncompativel, ErroValidacao
from app.domain.modelos import Categoria, Lancamento
from app.repositories.base import CategoriaRepository, LancamentoRepository

MENSAGEM_CATEGORIA_INEXISTENTE = "Categoria não encontrada."
MENSAGEM_FORMA_OBRIGATORIA = "Informe a forma de pagamento."


@dataclass(frozen=True)
class LancamentoComCategoria:
    """Lançamento e a categoria dele — a resposta leva nome e cor (`03` §6.3)."""

    lancamento: Lancamento
    categoria: Categoria


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
        return LancamentoComCategoria(lancamento, categoria)

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
