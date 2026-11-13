"""Aritmética de datas e meses (RN-03, RN-07, RN-09; F-03 §3.2)."""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.domain.datas import (
    agora,
    ajustar_dia,
    ano_e_mes,
    data_da_parcela,
    data_em_brasilia,
    dias_no_mes,
    mes_anterior,
    mes_corrente,
    mes_de,
    meses_entre,
    proximo_mes,
    somar_meses,
)


def test_data_da_parcela_parte_da_compra__RN_07() -> None:
    """CA-F03.4, borda 3: 31/01 em 3× dá 31/01, 28/02 e 31/03 — não 28/03."""
    compra = date(2026, 1, 31)

    datas = [data_da_parcela(compra, k) for k in range(1, 4)]

    assert datas == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)]


def test_data_da_parcela_cruza_o_ano__RN_07() -> None:
    compra = date(2026, 11, 30)

    datas = [data_da_parcela(compra, k) for k in range(1, 5)]

    assert datas == [date(2026, 11, 30), date(2026, 12, 30), date(2027, 1, 30), date(2027, 2, 28)]


def test_data_da_parcela_recusa_numero_menor_que_um() -> None:
    with pytest.raises(ValueError):
        data_da_parcela(date(2026, 1, 1), 0)


@pytest.mark.parametrize(
    ("ano", "mes", "dia", "esperado"),
    [
        (2100, 2, 29, date(2100, 2, 28)),  # 2100 não é bissexto
        (2024, 2, 29, date(2024, 2, 29)),
        (2024, 2, 31, date(2024, 2, 29)),
        (2026, 4, 31, date(2026, 4, 30)),
        (2026, 12, 31, date(2026, 12, 31)),
        (2026, 9, 15, date(2026, 9, 15)),
        (2026, 9, 1, date(2026, 9, 1)),
    ],
)
def test_ajustar_dia_em_fim_de_mes_e_ano_bissexto__RN_09(
    ano: int, mes: int, dia: int, esperado: date
) -> None:
    """CA-F03.5, borda 5."""
    assert ajustar_dia(ano, mes, dia) == esperado


@pytest.mark.parametrize(
    ("data", "meses", "esperado"),
    [
        (date(2024, 2, 29), 12, date(2025, 2, 28)),  # CA-F03.5, borda 4
        (date(2024, 2, 29), 48, date(2028, 2, 29)),
        (date(2026, 1, 31), 1, date(2026, 2, 28)),
        (date(2026, 12, 15), 1, date(2027, 1, 15)),
        (date(2026, 1, 15), -1, date(2025, 12, 15)),
        (date(2026, 3, 31), -1, date(2026, 2, 28)),
        (date(2026, 9, 29), 0, date(2026, 9, 29)),
    ],
)
def test_somar_meses_preserva_o_dia_quando_possivel__RN_07(
    data: date, meses: int, esperado: date
) -> None:
    assert somar_meses(data, meses) == esperado


@pytest.mark.parametrize("dia", [0, 32, -1])
def test_ajustar_dia_recusa_dia_fora_de_1_a_31(dia: int) -> None:
    with pytest.raises(ValueError):
        ajustar_dia(2026, 1, dia)


def test_meses_entre_inclusivo_e_virada_de_ano__RN_09() -> None:
    """CA-F03.6, bordas 6 e 7."""
    assert meses_entre("2026-11", "2027-02") == ["2026-11", "2026-12", "2027-01", "2027-02"]
    assert meses_entre("2026-09", "2026-09") == ["2026-09"]
    assert meses_entre("2027-02", "2026-11") == []


def test_meses_entre_doze_meses() -> None:
    meses = meses_entre("2025-10", "2026-09")

    assert len(meses) == 12
    assert meses[0] == "2025-10"
    assert meses[-1] == "2026-09"


def test_proximo_e_anterior_cruzam_o_ano() -> None:
    assert proximo_mes("2026-12") == "2027-01"
    assert proximo_mes("2026-09") == "2026-10"
    assert mes_anterior("2027-01") == "2026-12"
    assert mes_anterior("2026-10") == "2026-09"


def test_mes_de_e_mes_de_referencia__RN_03() -> None:
    assert mes_de(date(2026, 9, 29)) == "2026-09"
    assert mes_de(date(2027, 1, 1)) == "2027-01"
    assert mes_corrente(date(2026, 2, 28)) == "2026-02"
    assert mes_corrente() == mes_de(date.today())


def test_ano_e_mes_le_o_texto() -> None:
    assert ano_e_mes("2026-09") == (2026, 9)


@pytest.mark.parametrize(
    "invalido", ["2026-13", "2026-00", "2026-9", "26-09", "2026/09", "", "2026-09-01"]
)
def test_mes_invalido_e_recusado(invalido: str) -> None:
    with pytest.raises(ValueError, match="YYYY-MM"):
        ano_e_mes(invalido)
    with pytest.raises(ValueError):
        meses_entre(invalido, "2026-09")
    with pytest.raises(ValueError):
        meses_entre("2026-09", invalido)


def test_agora_sem_microssegundos_e_sem_fuso() -> None:
    """F-03 §3.2.6: hora local, ISO com segundos."""
    instante = agora()

    assert isinstance(instante, datetime)
    assert instante.microsecond == 0
    assert instante.tzinfo is None
    assert len(instante.isoformat()) == len("2026-09-29T10:15:00")


@pytest.mark.parametrize(
    ("mes", "dias"), [("2026-09", 30), ("2026-10", 31), ("2026-02", 28), ("2028-02", 29)]
)
def test_dias_no_mes(mes: str, dias: int) -> None:
    assert dias_no_mes(mes) == dias


@pytest.mark.parametrize(
    ("instante", "esperada"),
    [
        ("2026-11-12T01:30:00.000Z", date(2026, 11, 11)),  # 22:30 de 11/11 em Brasília
        ("2026-11-12T02:59:59Z", date(2026, 11, 11)),
        ("2026-11-12T03:00:00Z", date(2026, 11, 12)),
        ("2026-11-12T15:00:00Z", date(2026, 11, 12)),
        ("2027-01-01T00:10:00Z", date(2026, 12, 31)),  # vira o ano
        ("2026-11-11T23:30:00-03:00", date(2026, 11, 11)),  # já em UTC−3
    ],
)
def test_data_em_brasilia__RN_18(instante: str, esperada: date) -> None:
    """CA-F16.13, borda 1 (ADR-19): o dia é o de Brasília (UTC−3 fixo), não o de UTC."""
    assert data_em_brasilia(datetime.fromisoformat(instante)) == esperada


def test_data_em_brasilia_aceita_qualquer_fuso__RN_18() -> None:
    toquio = timezone(timedelta(hours=9))

    assert data_em_brasilia(datetime(2026, 11, 12, 10, 0, tzinfo=toquio)) == date(2026, 11, 11)


def test_data_em_brasilia_recusa_instante_sem_fuso__RN_18() -> None:
    with pytest.raises(ValueError, match="sem fuso"):
        data_em_brasilia(datetime(2026, 11, 12, 1, 30))
