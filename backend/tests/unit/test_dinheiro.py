"""Dinheiro em centavos exatos e divisão em parcelas (RN-01, RN-07, RN-16; F-03 §3.1)."""

from decimal import Decimal

import pytest
from pydantic import TypeAdapter, ValidationError

from app.domain.dinheiro import (
    PARCELAS_MAX,
    PARCELAS_MIN,
    Dinheiro,
    dividir_em_parcelas,
    valor_da_planilha,
)
from app.domain.erros import ErroValidacao

DINHEIRO = TypeAdapter(Dinheiro)

EXEMPLOS_DA_SPEC = [
    ("100.00", 3, ["33.34", "33.33", "33.33"]),
    ("10.00", 3, ["3.34", "3.33", "3.33"]),
    ("99.99", 48, ["2.23"] + ["2.08"] * 47),
    ("0.48", 48, ["0.01"] * 48),
    ("2.00", 2, ["1.00", "1.00"]),
]


@pytest.mark.parametrize(("total", "n", "esperado"), EXEMPLOS_DA_SPEC)
def test_parcelas_dos_exemplos_da_spec__RN_07(total: str, n: int, esperado: list[str]) -> None:
    parcelas = dividir_em_parcelas(Decimal(total), n)

    assert parcelas == [Decimal(valor) for valor in esperado]
    assert sum(parcelas) == Decimal(total)


@pytest.mark.parametrize("n", range(PARCELAS_MIN, PARCELAS_MAX + 1))
@pytest.mark.parametrize("total", ["0.48", "1.00", "99.99", "100.00", "1234.57", "999999999.99"])
def test_parcelas_somam_o_total__RN_07(total: str, n: int) -> None:
    """CA-F03.1: a soma é exatamente o total, para todo N de 2 a 48."""
    parcelas = dividir_em_parcelas(Decimal(total), n)

    assert len(parcelas) == n
    assert sum(parcelas) == Decimal(total)
    assert all(parcela >= Decimal("0.01") for parcela in parcelas)


@pytest.mark.parametrize("n", range(PARCELAS_MIN, PARCELAS_MAX + 1))
def test_parcelas_centavos_na_primeira__RN_07(n: int) -> None:
    """CA-F03.2: só a 1ª recebe o resto; as demais são iguais e truncadas."""
    total = Decimal("1234.57")
    primeira, *demais = dividir_em_parcelas(total, n)

    base = (total / n).quantize(Decimal("0.01"), rounding="ROUND_DOWN")
    assert set(demais) == {base}
    assert Decimal("0") <= primeira - base < n * Decimal("0.01")


@pytest.mark.parametrize("n", [-1, 0, 1, 49, 100])
def test_parcelas_recusa_n_fora_da_faixa__RN_07(n: int) -> None:
    """CA-F03.3."""
    with pytest.raises(ErroValidacao, match="de 2 a 48 parcelas") as erro:
        dividir_em_parcelas(Decimal("100.00"), n)

    assert erro.value.codigo == "VALIDACAO"


@pytest.mark.parametrize(
    ("total", "n", "minimo"),
    [
        ("0.47", 48, "R$ 0,48"),
        ("0.01", 2, "R$ 0,02"),
        ("0.00", 3, "R$ 0,03"),
        ("-5.00", 2, "R$ 0,02"),
    ],
)
def test_parcelas_recusa_total_menor_que_um_centavo_por_parcela__RN_07(
    total: str, n: int, minimo: str
) -> None:
    """CA-F03.3, borda 1: parcela de R$ 0,00 violaria RN-01; a mensagem diz o mínimo."""
    with pytest.raises(ErroValidacao) as erro:
        dividir_em_parcelas(Decimal(total), n)

    assert erro.value.mensagem == f"{n} parcelas exigem um valor total de no mínimo {minimo}."


def test_parcelas_recusa_total_com_mais_de_duas_casas__RN_01() -> None:
    with pytest.raises(ErroValidacao, match="2 casas decimais"):
        dividir_em_parcelas(Decimal("100.001"), 3)


def test_soma_em_decimal_sem_erro_de_ponto_flutuante__RN_16() -> None:
    """CA-F03.7: `0.1 + 0.2` como `Dinheiro` dá exatamente `0.30`."""
    assert 0.1 + 0.2 != 0.3  # o problema que o tipo evita

    soma = DINHEIRO.validate_json("0.1") + DINHEIRO.validate_json("0.2")

    assert soma == Decimal("0.30")
    assert DINHEIRO.dump_json(soma) == b"0.3"

    muitos = sum([DINHEIRO.validate_python("0.10")] * 1000, Decimal("0"))
    assert muitos == Decimal("100.00")


@pytest.mark.parametrize(
    ("lido", "esperado"),
    [
        (42.500000000000004, "42.50"),
        (42.5, "42.50"),
        (0.30000000000000004, "0.30"),
        (10, "10.00"),
        (1234.56, "1234.56"),
        (Decimal("7.1"), "7.10"),
    ],
)
def test_valor_lido_da_planilha_vira_decimal_de_2_casas__RN_16(
    lido: float | int | Decimal, esperado: str
) -> None:
    """CA-F03.7, borda 17."""
    valor = valor_da_planilha(lido)

    assert isinstance(valor, Decimal)
    assert valor == Decimal(esperado)
    assert str(valor) == esperado


@pytest.mark.parametrize("invalido", ["0", "0.00", "-5", "1.005", "1234567890123.45"])
def test_dinheiro_recusa_zero_negativo_e_mais_de_2_casas__RN_01(invalido: str) -> None:
    with pytest.raises(ValidationError):
        DINHEIRO.validate_python(Decimal(invalido))


def test_dinheiro_sai_no_json_como_numero__CA_F03_8() -> None:
    assert DINHEIRO.dump_json(Decimal("42.50")) == b"42.5"
    assert DINHEIRO.dump_python(Decimal("42.50")) == Decimal("42.50")
