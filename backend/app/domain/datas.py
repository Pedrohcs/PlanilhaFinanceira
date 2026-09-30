"""Aritmética de datas e meses de referência (RN-03, RN-07, RN-09).

Mês de referência é texto `YYYY-MM` (`SPECS/02` §3). Datas de parcela e de
recorrência caem no último dia do mês quando o dia pedido não existe.
"""

import calendar
import re
from datetime import date, datetime

MES_PADRAO = r"^\d{4}-(0[1-9]|1[0-2])$"
_MES = re.compile(MES_PADRAO)


def ajustar_dia(ano: int, mes: int, dia: int) -> date:
    """Data com o `dia` pedido ou, se ele não existe no mês, o último dia do mês."""
    if not 1 <= dia <= 31:
        raise ValueError(f"Dia fora de 1..31: {dia}")
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, min(dia, ultimo_dia))


def somar_meses(data: date, meses: int) -> date:
    """Avança (ou recua, se negativo) `meses`, preservando o dia quando possível."""
    indice = data.year * 12 + (data.month - 1) + meses
    ano, mes_zero = divmod(indice, 12)
    return ajustar_dia(ano, mes_zero + 1, data.day)


def data_da_parcela(data_compra: date, numero: int) -> date:
    """Data da parcela `numero` (1ª = a própria compra), RN-07.

    Sempre calculada a partir da data da compra, nunca da parcela anterior:
    31/01 em 3× dá 31/01, 28/02 e **31/03** — encadeado daria 28/03.
    """
    if numero < 1:
        raise ValueError(f"Número de parcela deve ser ≥ 1: {numero}")
    return somar_meses(data_compra, numero - 1)


def ano_e_mes(mes: str) -> tuple[int, int]:
    """`"2026-09"` → `(2026, 9)`; levanta `ValueError` fora do formato `YYYY-MM`."""
    if not _MES.fullmatch(mes):
        raise ValueError(f"Mês fora do formato YYYY-MM: {mes!r}")
    ano, numero = mes.split("-")
    return int(ano), int(numero)


def mes_de(data: date) -> str:
    """Mês de referência de uma data (RN-03)."""
    return f"{data.year:04d}-{data.month:02d}"


def proximo_mes(mes: str) -> str:
    ano, numero = ano_e_mes(mes)
    return mes_de(somar_meses(date(ano, numero, 1), 1))


def mes_anterior(mes: str) -> str:
    ano, numero = ano_e_mes(mes)
    return mes_de(somar_meses(date(ano, numero, 1), -1))


def dias_no_mes(mes: str) -> int:
    """`"2026-09"` → 30; `"2028-02"` → 29 (acumulado diário do resumo, F-09 Q2)."""
    ano, numero = ano_e_mes(mes)
    return calendar.monthrange(ano, numero)[1]


def meses_entre(inicio: str, fim: str) -> list[str]:
    """Meses de `inicio` a `fim`, inclusive nas pontas; vazio se `fim < inicio`."""
    ano_e_mes(inicio)
    ano_e_mes(fim)
    meses: list[str] = []
    atual = inicio
    while atual <= fim:
        meses.append(atual)
        atual = proximo_mes(atual)
    return meses


def mes_corrente(hoje: date | None = None) -> str:
    """Mês de referência de hoje (ou da data informada, para testes)."""
    return mes_de(hoje or date.today())


def agora() -> datetime:
    """Hora local sem fuso, com precisão de segundos (`criado_em`/`atualizado_em`)."""
    return datetime.now().replace(microsecond=0)
