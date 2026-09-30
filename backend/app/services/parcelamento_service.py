"""Compras parceladas (REQ-07, REQ-08, RN-07, RN-08; F-12 §3.1–3.2).

Cada parcela é um `Lancamento` comum; o `parcelamento_id` só serve para o
"k/N" e para excluir o parcelamento inteiro (RN-08). Valores e datas vêm das
funções de domínio (`dividir_em_parcelas`, `data_da_parcela`). Depende só de
`domain`, `repositories.base` e da validação compartilhada de `lancamento_service`.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain.datas import agora, data_da_parcela
from app.domain.dinheiro import PARCELAS_MAX, PARCELAS_MIN, dividir_em_parcelas
from app.domain.enums import FormaPagamento, TipoLancamento
from app.domain.erros import ErroValidacao, NaoEncontrado
from app.domain.modelos import Lancamento
from app.repositories.base import CategoriaRepository, LancamentoRepository
from app.services.lancamento_service import (
    LancamentoComCategoria,
    gerar_id,
    validar_categoria_e_forma,
)

MENSAGEM_PARCELAS_FORA_DO_LIMITE = f"Informe de {PARCELAS_MIN} a {PARCELAS_MAX} parcelas."
MENSAGEM_PARCELAMENTO_INEXISTENTE = "Parcelamento não encontrado."


@dataclass(frozen=True)
class ParcelamentoCriado:
    parcelamento_id: str
    lancamentos: list[LancamentoComCategoria]  # em ordem de parcela_numero


class ParcelamentoService:
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
        descricao: str,
        valor_total: Decimal,
        parcelas: int,
        categoria_id: str,
        forma_pagamento: FormaPagamento | None,
        observacao: str | None,
    ) -> ParcelamentoCriado:
        """Uma parcela por mês a partir da compra, gravadas numa única escrita (RN-07).

        Os limites de parcelas e de valor vêm antes da categoria: não precisam
        ler a planilha (F-12 §10).
        """
        valores = _dividir(valor_total, parcelas)
        categoria = validar_categoria_e_forma(
            self._categorias, categoria_id, TipoLancamento.GASTO, forma_pagamento
        )

        parcelamento_id = self._novo_id()
        instante = self._relogio()
        lancamentos = [
            Lancamento(
                id=self._novo_id(),
                data=data_da_parcela(data, numero),
                tipo=TipoLancamento.GASTO,
                descricao=descricao,  # a original, sem "(k/N)" (CA-07.3)
                valor=valor,
                categoria_id=categoria.id,
                forma_pagamento=forma_pagamento,
                observacao=observacao,
                parcelamento_id=parcelamento_id,
                parcela_numero=numero,
                parcela_total=parcelas,
                criado_em=instante,
                atualizado_em=instante,
            )
            for numero, valor in enumerate(valores, start=1)
        ]
        self._lancamentos.inserir(lancamentos)  # uma chamada à API do Google (`02` §5.5)
        return ParcelamentoCriado(
            parcelamento_id,
            [LancamentoComCategoria(item, categoria.nome, categoria.cor) for item in lancamentos],
        )

    def excluir(self, parcelamento_id: str) -> None:
        """Remove as parcelas **restantes**, em qualquer mês (REQ-08, CA-08.2).

        Se a planilha mudou desde a última leitura (parcela apagada à mão dentro
        do TTL do cache), o `remover` falha sem apagar nada e invalida o cache;
        uma nova tentativa, com a aba relida, resolve (F-12 §3.2.4).
        """
        ids = self._ids_das_parcelas(parcelamento_id)
        try:
            self._lancamentos.remover(ids)
        except NaoEncontrado:
            ids = self._ids_das_parcelas(parcelamento_id)  # cache invalidado: aba relida
            try:
                self._lancamentos.remover(ids)
            except NaoEncontrado as erro:
                raise NaoEncontrado(MENSAGEM_PARCELAMENTO_INEXISTENTE) from erro

    def _ids_das_parcelas(self, parcelamento_id: str) -> list[str]:
        ids = [
            item.id
            for item in self._lancamentos.listar().itens
            if item.parcelamento_id == parcelamento_id
        ]
        if not ids:
            raise NaoEncontrado(MENSAGEM_PARCELAMENTO_INEXISTENTE)
        return ids


def _dividir(valor_total: Decimal, parcelas: int) -> list[Decimal]:
    """RN-07 com o erro no campo certo: `parcelas` ou `valor_total` (F-12 §3.1)."""
    if not PARCELAS_MIN <= parcelas <= PARCELAS_MAX:
        raise ErroValidacao.no_campo("parcelas", MENSAGEM_PARCELAS_FORA_DO_LIMITE)
    try:
        return dividir_em_parcelas(valor_total, parcelas)
    except ErroValidacao as erro:
        raise ErroValidacao.no_campo("valor_total", erro.mensagem) from erro
