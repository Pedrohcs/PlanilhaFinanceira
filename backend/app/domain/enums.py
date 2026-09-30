"""Enums do domínio (`SPECS/03` §5.5).

O valor de cada membro é o código que vai para a planilha e para o JSON
(MAIÚSCULAS, `SPECS/02` §7); `rotulo`, onde a spec define um, é o texto
exibido ao usuário.
"""

from enum import StrEnum


class TipoLancamento(StrEnum):
    GASTO = "GASTO"
    RECEITA = "RECEITA"

    @property
    def rotulo(self) -> str:
        return _ROTULOS_TIPO[self]


class FormaPagamento(StrEnum):
    """Lista fixa de RN-05 (P-01)."""

    PIX = "PIX"
    CREDITO = "CREDITO"
    DEBITO = "DEBITO"
    DINHEIRO = "DINHEIRO"
    BOLETO = "BOLETO"
    TRANSFERENCIA = "TRANSFERENCIA"

    @property
    def rotulo(self) -> str:
        return _ROTULOS_FORMA[self]


class StatusRecorrencia(StrEnum):
    ATIVA = "ATIVA"
    PAUSADA = "PAUSADA"
    ENCERRADA = "ENCERRADA"


_ROTULOS_TIPO = {
    TipoLancamento.GASTO: "Gasto",
    TipoLancamento.RECEITA: "Receita",
}

_ROTULOS_FORMA = {
    FormaPagamento.PIX: "Pix",
    FormaPagamento.CREDITO: "Cartão de crédito",
    FormaPagamento.DEBITO: "Cartão de débito",
    FormaPagamento.DINHEIRO: "Dinheiro",
    FormaPagamento.BOLETO: "Boleto",
    FormaPagamento.TRANSFERENCIA: "Transferência",
}
