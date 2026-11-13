"""Textos comparáveis sem acento e sem caixa (RN-12, RN-19; F-16 §3.4.1)."""

import pytest

from app.domain.textos import (
    chave_sem_acento_e_caixa,
    colapsar_espacos,
    normalizar_descricao,
    sem_acento,
)


@pytest.mark.parametrize(
    ("descricao", "esperada"),
    [
        ("LOJA X PARC 03/10", "loja x"),
        ("Ifood *Restaurante 1/2", "ifood *restaurante"),
        ("Uber   Trip", "uber trip"),
        ("  UBER  TRIP ", "uber trip"),
        ("Pão de Açúcar", "pao de acucar"),
        ("Loja X Parcela 3/10", "loja x"),
        ("Loja X PARC. 03 / 10", "loja x"),
        ("LOJA X PARC03/10", "loja x"),
        ("Loja X 12/12", "loja x"),
        ("Posto 24/7 Centro", "posto 24/7 centro"),  # só o sufixo conta
        ("Mercado 2024", "mercado 2024"),
        ("Compra 100/200", "compra 100/200"),  # parcela tem até 2 dígitos
    ],
)
def test_normalizar_descricao__RN_19(descricao: str, esperada: str) -> None:
    """CA-F16.17, CA-F16.18: a parcela importada casa com a compra lançada à mão."""
    assert normalizar_descricao(descricao) == esperada


def test_normalizar_descricao_tira_o_sufixo_uma_vez_so__RN_19() -> None:
    assert normalizar_descricao("Loja 1/2 3/10") == "loja 1/2"


def test_normalizar_descricao_iguala_o_que_o_usuario_ve_como_igual__RN_19() -> None:
    assert (
        normalizar_descricao("Uber Trip")
        == normalizar_descricao("UBER  TRIP")
        == normalizar_descricao("uber trip 2/3")
    )


def test_chave_sem_acento_e_caixa__RN_12() -> None:
    assert chave_sem_acento_e_caixa("  SAÚDE   e Bem-estar ") == "saude e bem-estar"
    assert chave_sem_acento_e_caixa("A Classificar") == chave_sem_acento_e_caixa("a classificar")


def test_sem_acento_e_colapsar_espacos() -> None:
    assert sem_acento("Alimentação") == "Alimentacao"
    assert colapsar_espacos("  Pet \t  Shop\n") == "Pet Shop"
