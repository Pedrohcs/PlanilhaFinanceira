"""Preparação idempotente da planilha (REQ-15, RN-15; F-03 §3.4).

Tudo contra `PlanilhaFalsa`: nenhuma chamada ao Google.
"""

import logging
import re
from datetime import datetime
from typing import Any

import pytest

from app.domain.erros import SchemaPlanilhaInvalido
from app.domain.modelos import Categoria
from app.infra.bootstrap import CATEGORIAS_PADRAO, preparar_planilha
from app.infra.schema_planilha import (
    ABA_CATEGORIAS,
    ABA_CONFIG,
    ABA_LANCAMENTOS,
    ABA_RECORRENCIAS,
    ABAS,
)
from tests.planilha_falsa import PlanilhaFalsa

CABECALHO_LANCAMENTOS = list(ABA_LANCAMENTOS.colunas)
CABECALHO_CATEGORIAS = list(ABA_CATEGORIAS.colunas)
CABECALHO_RECORRENCIAS = list(ABA_RECORRENCIAS.colunas)
CABECALHO_CONFIG = list(ABA_CONFIG.colunas)

LANCAMENTO = [
    "9f1c", "2026-09-29", "GASTO", "Almoço", 42.5, "alimentacao", "PIX",
    "", "", "", "", "", "2026-09-29T10:15:00", "2026-09-29T10:15:00",
]  # fmt: skip
CATEGORIA_DO_USUARIO = ["pet", "Pet", "GASTO", "#123456", True, "2026-09-29T10:15:00"]


def planilha_pronta(**alteracoes: list[list[Any]] | None) -> PlanilhaFalsa:
    """Planilha já preparada por uma execução anterior, com um dado em cada aba.

    `Aba=[...]` troca o conteúdo da aba; `Aba=None` a remove.
    """
    abas: dict[str, list[list[Any]]] = {
        "Lancamentos": [CABECALHO_LANCAMENTOS, LANCAMENTO],
        "Categorias": [CABECALHO_CATEGORIAS, CATEGORIA_DO_USUARIO],
        "Recorrencias": [CABECALHO_RECORRENCIAS],
        "Config": [CABECALHO_CONFIG, ["versao_schema", 1]],
    }
    for nome, linhas in alteracoes.items():
        if linhas is None:
            del abas[nome]
        else:
            abas[nome] = linhas
    return PlanilhaFalsa(abas)


def fotografia(planilha: PlanilhaFalsa) -> dict[str, list[list[Any]]]:
    return {nome: planilha.linhas(nome) for nome in planilha.nomes_das_abas()}


# Planilha nova -----------------------------------------------------------------


def test_cria_as_quatro_abas_com_cabecalho__CA_15_1() -> None:
    """CA-15.1, CA-F03.9: nomes e ordem exatamente como `03` §5."""
    planilha = PlanilhaFalsa()

    preparar_planilha(planilha)

    assert planilha.nomes_das_abas() == [aba.nome for aba in ABAS]
    for aba in ABAS:
        assert planilha.linhas(aba.nome)[0] == list(aba.colunas)
        assert planilha.worksheet(aba.nome).col_count == len(aba.colunas)


def test_semeia_as_quinze_categorias_padrao__RN_15() -> None:
    """CA-F03.12: uma única escrita; slug, tipo e `ativa = true`."""
    planilha = PlanilhaFalsa()

    preparar_planilha(planilha)

    escritas_em_categorias = [
        escrita for escrita in planilha.escritas
        if escrita[0] == "append_rows" and escrita[1] == "Categorias"
    ]  # fmt: skip
    assert len(escritas_em_categorias) == 1

    linhas = planilha.linhas("Categorias")[1:]
    categorias = [Categoria.model_validate(dict(zip(CABECALHO_CATEGORIAS, linha, strict=True)))
                  for linha in linhas]  # fmt: skip
    assert len(categorias) == 15
    assert [c.nome for c in categorias if c.tipo == "GASTO"] == [
        "Alimentação", "Mercado", "Moradia", "Contas da casa", "Transporte", "Saúde",
        "Educação", "Lazer", "Vestuário", "Assinaturas", "Outros gastos",
    ]  # fmt: skip
    assert [c.nome for c in categorias if c.tipo == "RECEITA"] == [
        "Salário", "Freelance", "Rendimentos", "Outras receitas",
    ]  # fmt: skip
    assert all(c.ativa is True for c in categorias)
    assert all(linha[4] is True for linha in linhas)  # booleano de verdade, não texto
    assert {c.id for c in categorias} == {
        "alimentacao", "mercado", "moradia", "contas-da-casa", "transporte", "saude",
        "educacao", "lazer", "vestuario", "assinaturas", "outros-gastos",
        "salario", "freelance", "rendimentos", "outras-receitas",
    }  # fmt: skip
    for categoria in categorias:
        assert categoria.criado_em <= datetime.now()


def test_categorias_padrao_tem_cor_unica__CA_F03_25() -> None:
    """Cores de F-03 §3.4 (Q2), `#RRGGBB`, sem repetição."""
    planilha = PlanilhaFalsa()

    preparar_planilha(planilha)

    cores = {linha[0]: linha[3] for linha in planilha.linhas("Categorias")[1:]}
    assert cores == {
        "alimentacao": "#E57373", "mercado": "#FF8A65", "moradia": "#7986CB",
        "contas-da-casa": "#4FC3F7", "transporte": "#4DD0E1", "saude": "#F06292",
        "educacao": "#7E57C2", "lazer": "#FFB74D", "vestuario": "#A1887F",
        "assinaturas": "#BA68C8", "outros-gastos": "#90A4AE", "salario": "#66BB6A",
        "freelance": "#9CCC65", "rendimentos": "#26A69A", "outras-receitas": "#AED581",
    }  # fmt: skip
    assert all(re.fullmatch(r"#[0-9A-F]{6}", cor) for cor in cores.values())
    assert len(set(cores.values())) == len(CATEGORIAS_PADRAO)


def test_grava_versao_schema__CA_F03_15() -> None:
    planilha = PlanilhaFalsa()

    preparar_planilha(planilha)

    assert planilha.linhas("Config") == [CABECALHO_CONFIG, ["versao_schema", 1]]


def test_grava_versao_schema_se_so_ela_faltar__CA_F03_15() -> None:
    planilha = planilha_pronta(Config=[CABECALHO_CONFIG, ["outra_chave", "x"]])

    preparar_planilha(planilha)

    assert planilha.linhas("Config") == [
        CABECALHO_CONFIG, ["outra_chave", "x"], ["versao_schema", 1],
    ]  # fmt: skip
    assert len(planilha.escritas) == 1


# Planilha já preparada ---------------------------------------------------------


def test_nao_semeia_se_ja_houver_categoria__CA_15_2() -> None:
    """CA-F03.13: basta uma linha, mesmo que o usuário tenha apagado as padrão."""
    planilha = planilha_pronta()

    preparar_planilha(planilha)

    assert planilha.linhas("Categorias") == [CABECALHO_CATEGORIAS, CATEGORIA_DO_USUARIO]


def test_resemeia_se_categorias_esvaziada__RN_15() -> None:
    """Borda 21: aba esvaziada de propósito volta a ter as 15 padrão no próximo início."""
    planilha = planilha_pronta(Categorias=[CABECALHO_CATEGORIAS, ["", "", ""], []])

    preparar_planilha(planilha)

    assert len(planilha.linhas("Categorias")) == 1 + 15


def test_rodar_duas_vezes_nao_duplica__CA_15_2() -> None:
    """CA-F03.14: a segunda execução não escreve nada."""
    planilha = PlanilhaFalsa()
    preparar_planilha(planilha)
    antes = fotografia(planilha)
    escritas_da_primeira = len(planilha.escritas)

    preparar_planilha(planilha)

    assert fotografia(planilha) == antes
    assert len(planilha.escritas) == escritas_da_primeira


def test_planilha_pronta_nao_recebe_escrita__CA_15_2() -> None:
    planilha = planilha_pronta()
    antes = fotografia(planilha)

    preparar_planilha(planilha)

    assert planilha.escritas == []
    assert fotografia(planilha) == antes


def test_cria_so_a_aba_que_falta__CA_15_2() -> None:
    planilha = planilha_pronta(Recorrencias=None)

    preparar_planilha(planilha)

    assert planilha.linhas("Recorrencias") == [CABECALHO_RECORRENCIAS]
    assert planilha.linhas("Lancamentos") == [CABECALHO_LANCAMENTOS, LANCAMENTO]
    assert [escrita[0] for escrita in planilha.escritas] == ["add_worksheet", "update"]


def test_ignora_aba_extra_do_usuario__RN_14() -> None:
    """Borda 8: a 5ª aba não é lida, alterada nem apagada."""
    planilha = planilha_pronta(Rascunho=[["minhas", "anotações"]])

    preparar_planilha(planilha)

    assert planilha.linhas("Rascunho") == [["minhas", "anotações"]]
    assert planilha.escritas == []


# Cabeçalhos --------------------------------------------------------------------


def test_acrescenta_colunas_que_faltam_no_fim__CA_F03_10() -> None:
    """Borda 10: só A–H existem; I–N entram e a linha de dado continua intacta."""
    planilha = planilha_pronta(
        Lancamentos=[CABECALHO_LANCAMENTOS[:8], LANCAMENTO[:8]],
    )

    preparar_planilha(planilha)

    valores = planilha.worksheet("Lancamentos").valores
    assert valores[0] == CABECALHO_LANCAMENTOS
    assert valores[1] == LANCAMENTO[:8]
    assert planilha.escritas == [
        ("update", "Lancamentos", "I1", [CABECALHO_LANCAMENTOS[8:]]),
    ]


def test_acrescenta_colunas_alargando_a_grade__CA_F03_10() -> None:
    planilha = planilha_pronta(Categorias=[CABECALHO_CATEGORIAS[:4]])
    planilha.worksheet("Categorias").col_count = 4

    preparar_planilha(planilha)

    assert planilha.worksheet("Categorias").col_count == 6
    assert planilha.linhas("Categorias")[0] == CABECALHO_CATEGORIAS
    assert planilha.escritas[0] == ("add_cols", "Categorias", 2)


def test_aba_existente_sem_cabecalho_recebe_cabecalho__CA_F03_10() -> None:
    """Aba criada à mão, vazia: o cabeçalho inteiro entra na linha 1."""
    planilha = planilha_pronta(Recorrencias=[])

    preparar_planilha(planilha)

    assert planilha.linhas("Recorrencias") == [CABECALHO_RECORRENCIAS]


def test_colunas_extras_no_fim_sao_aceitas(caplog: pytest.LogCaptureFixture) -> None:
    """Decisão do usuário em T-008: o que vem depois da última coluna é ignorado."""
    planilha = planilha_pronta(
        Lancamentos=[CABECALHO_LANCAMENTOS + ["notas"], LANCAMENTO + ["lembrar"]],
    )

    with caplog.at_level(logging.INFO, logger="app.infra.bootstrap"):
        preparar_planilha(planilha)

    assert planilha.escritas == []
    assert "Lancamentos" in caplog.text
    assert "notas" in caplog.text


def test_espacos_em_volta_do_cabecalho_sao_tolerados__RN_14() -> None:
    cabecalho = [f" {coluna} " for coluna in CABECALHO_CATEGORIAS]
    planilha = planilha_pronta(Categorias=[cabecalho, CATEGORIA_DO_USUARIO])

    preparar_planilha(planilha)

    assert planilha.escritas == []


@pytest.mark.parametrize(
    ("aba", "cabecalho", "trecho"),
    [
        (
            "Lancamentos",
            [*CABECALHO_LANCAMENTOS[:7], "obs", *CABECALHO_LANCAMENTOS[8:]],
            "Lancamentos, coluna H deveria ser 'observacao', mas está 'obs'",
        ),
        (
            "Categorias",
            ["id", "tipo", "nome", "cor", "ativa", "criado_em"],
            "Categorias, coluna B deveria ser 'nome', mas está 'tipo'",
        ),
        (
            "Recorrencias",
            ["id", "", "descricao"],
            "Recorrencias, coluna B deveria ser 'tipo', mas está vazia",
        ),
        ("Config", ["Chave", "valor"], "Config, coluna A deveria ser 'chave', mas está 'Chave'"),
    ],
)
def test_divergencia_de_cabecalho_da_erro_claro__CA_F03_11(
    aba: str, cabecalho: list[str], trecho: str
) -> None:
    """Borda 9: nada é alterado e o erro nomeia aba e coluna."""
    outra_aba = "Recorrencias" if aba != "Recorrencias" else "Lancamentos"
    planilha = planilha_pronta(**{aba: [cabecalho], outra_aba: None})
    antes = fotografia(planilha)

    with pytest.raises(SchemaPlanilhaInvalido) as erro:
        preparar_planilha(planilha)

    assert erro.value.codigo == "SCHEMA_PLANILHA_INVALIDO"
    assert erro.value.mensagem == (
        f"A estrutura da planilha não corresponde ao esperado: {trecho}."
    )
    assert planilha.escritas == []  # nem a aba que faltava foi criada
    assert fotografia(planilha) == antes


# versao_schema -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("valor", "trecho"),
    [
        (2, "versao_schema 2 é de uma versão mais nova do aplicativo (esta lê até a 1)"),
        ("2", "versao_schema 2 é de uma versão mais nova do aplicativo (esta lê até a 1)"),
        ("abc", "versao_schema 'abc' não é um número inteiro"),
        (1.5, "versao_schema '1.5' não é um número inteiro"),
        ("", "versao_schema '' não é um número inteiro"),
        (0, "versao_schema 0 não é uma versão válida"),
        (-1, "versao_schema -1 não é uma versão válida"),
    ],
)
def test_versao_schema_a_frente_do_app_da_erro__CA_F03_24(valor: Any, trecho: str) -> None:
    """Bordas 11 e 12: nenhuma célula é escrita, nem as categorias de uma aba vazia."""
    planilha = planilha_pronta(
        Config=[CABECALHO_CONFIG, ["versao_schema", valor]],
        Categorias=[CABECALHO_CATEGORIAS],
    )

    with pytest.raises(SchemaPlanilhaInvalido) as erro:
        preparar_planilha(planilha)

    assert erro.value.mensagem == (
        f"A estrutura da planilha não corresponde ao esperado: Config, {trecho}."
    )
    assert planilha.escritas == []


@pytest.mark.parametrize("valor", [1, 1.0, "1", " 1 "])
def test_aceita_versao_schema_como_texto_ou_numero(valor: Any) -> None:
    planilha = planilha_pronta(Config=[CABECALHO_CONFIG, ["versao_schema", valor]])

    preparar_planilha(planilha)

    assert planilha.escritas == []


# Opções de leitura e escrita ---------------------------------------------------


def test_escreve_com_raw_e_le_unformatted__ADR_04() -> None:
    """`PlanilhaFalsa` recusa qualquer outra opção; basta a execução completa passar."""
    planilha = PlanilhaFalsa()

    preparar_planilha(planilha)
    preparar_planilha(planilha)

    assert planilha.escritas  # houve escrita na primeira execução, toda com RAW
