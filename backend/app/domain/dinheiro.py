"""Dinheiro em centavos exatos (RN-01, RN-07, RN-16; `SPECS/02` §3).

Todo cálculo é em `Decimal`. A conversão para `float` só acontece na borda:
no JSON (serializer do tipo `Dinheiro`) e na escrita da planilha.
"""

from decimal import Decimal
from typing import Annotated

from pydantic import Field, PlainSerializer

from app.domain.erros import ErroValidacao

Dinheiro = Annotated[
    Decimal,
    Field(gt=0, max_digits=12, decimal_places=2),
    PlainSerializer(float, return_type=float, when_used="json"),
]
"""Valor monetário positivo com até 2 casas; sai no JSON como número."""

CENTAVO = Decimal("0.01")
PARCELAS_MIN = 2
PARCELAS_MAX = 48


def valor_da_planilha(valor: float | int | Decimal) -> Decimal:
    """Número lido da planilha → `Decimal` de 2 casas, sem herdar erro binário.

    O Sheets pode devolver `42.500000000000004`; o resultado é `Decimal("42.50")`.
    """
    return Decimal(str(round(valor, 2))).quantize(CENTAVO)


def dividir_em_parcelas(total: Decimal, parcelas: int) -> list[Decimal]:
    """Divide `total` em `parcelas` valores cuja soma é exatamente `total` (RN-07).

    Cada parcela é o total ÷ N truncado no centavo; os centavos que sobram vão
    todos para a 1ª parcela. Levanta `ErroValidacao` se N estiver fora de
    2..48, se o total tiver mais de 2 casas ou se não couber R$ 0,01 por parcela.
    """
    if not PARCELAS_MIN <= parcelas <= PARCELAS_MAX:
        raise ErroValidacao(f"O parcelamento deve ter de {PARCELAS_MIN} a {PARCELAS_MAX} parcelas.")
    if total != total.quantize(CENTAVO):
        raise ErroValidacao("O valor deve ter no máximo 2 casas decimais.")
    minimo = CENTAVO * parcelas
    if total < minimo:
        raise ErroValidacao(
            f"{parcelas} parcelas exigem um valor total de no mínimo {_formatar_reais(minimo)}."
        )

    base, resto = divmod(int(total / CENTAVO), parcelas)
    valor_base = base * CENTAVO
    return [valor_base + resto * CENTAVO] + [valor_base] * (parcelas - 1)


def _formatar_reais(valor: Decimal) -> str:
    """`Decimal("1234.5")` → `"R$ 1.234,50"`, para mensagens ao usuário."""
    texto = f"{valor.quantize(CENTAVO):,.2f}"
    return "R$ " + texto.replace(",", "_").replace(".", ",").replace("_", ".")
