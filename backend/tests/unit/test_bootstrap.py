"""Preparação idempotente da planilha (REQ-15, RN-15; F-03 §3.4) e migração 1 → 2 (F-16).

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
    ABA_CARTOES,
    ABA_CATEGORIAS,
    ABA_CONFIG,
    ABA_IMPORTACOES,
    ABA_LANCAMENTOS,
    ABA_RECORRENCIAS,
    ABAS,
)
from tests.planilha_falsa import PlanilhaFalsa

CABECALHO_LANCAMENTOS = list(ABA_LANCAMENTOS.colunas)
CABECALHO_CATEGORIAS = list(ABA_CATEGORIAS.colunas)
CABECALHO_RECORRENCIAS = list(ABA_RECORRENCIAS.colunas)
CABECALHO_CONFIG = list(ABA_CONFIG.colunas)
CABECALHO_CARTOES = list(ABA_CARTOES.colunas)
CABECALHO_IMPORTACOES = list(ABA_IMPORTACOES.colunas)

LANCAMENTO = [
    "9f1c", "2026-09-29", "GASTO", "Almoço", 42.5, "alimentacao", "PIX",
    "", "", "", "", "", "2026-09-29T10:15:00", "2026-09-29T10:15:00",
]  # fmt: skip
CATEGORIA_DO_USUARIO = ["pet", "Pet", "GASTO", "#123456", True, "2026-09-29T10:15:00"]


def _montar(
    abas: dict[str, list[list[Any]]], alteracoes: dict[str, list[list[Any]] | None]
) -> PlanilhaFalsa:
    """`Aba=[...]` troca o conteúdo da aba; `Aba=None` a remove."""
    for nome, linhas in alteracoes.items():
        if linhas is None:
            del abas[nome]
        else:
            abas[nome] = linhas
    return PlanilhaFalsa(abas)


def planilha_v1(**alteracoes: list[list[Any]] | None) -> PlanilhaFalsa:
    """Planilha preparada pelo app **antes** de F-16: 4 abas, `versao_schema` 1, com dados."""
    return _montar(
        {
            "Lancamentos": [CABECALHO_LANCAMENTOS, LANCAMENTO],
            "Categorias": [CABECALHO_CATEGORIAS, CATEGORIA_DO_USUARIO],
            "Recorrencias": [CABECALHO_RECORRENCIAS],
            "Config": [CABECALHO_CONFIG, ["versao_schema", 1]],
        },
        alteracoes,
    )


def planilha_pronta(**alteracoes: list[list[Any]] | None) -> PlanilhaFalsa:
    """Planilha já na versão 2, com um dado em cada aba que o usuário edita."""
    return _montar(
        {
            "Lancamentos": [CABECALHO_LANCAMENTOS, LANCAMENTO],
            "Categorias": [CABECALHO_CATEGORIAS, CATEGORIA_DO_USUARIO],
            "Recorrencias": [CABECALHO_RECORRENCIAS],
            "Config": [CABECALHO_CONFIG, ["versao_schema", 2]],
            "Cartoes": [CABECALHO_CARTOES],
            "Importacoes": [CABECALHO_IMPORTACOES],
        },
        alteracoes,
    )


def reservada(id_: str, nome: str, tipo: str, criado_em: Any) -> list[Any]:
    return [id_, nome, tipo, "#90A4AE", True, criado_em]


def fotografia(planilha: PlanilhaFalsa) -> dict[str, list[list[Any]]]:
    return {nome: planilha.linhas(nome) for nome in planilha.nomes_das_abas()}


# Planilha nova -----------------------------------------------------------------


def test_cria_as_seis_abas_com_cabecalho__CA_15_1() -> None:
    """CA-15.1, CA-F03.9: nomes e ordem exatamente como `03` §5."""
    planilha = PlanilhaFalsa()

    preparar_planilha(planilha)

    assert planilha.nomes_das_abas() == [aba.nome for aba in ABAS]
    for aba in ABAS:
        assert planilha.linhas(aba.nome)[0] == list(aba.colunas)
        assert planilha.worksheet(aba.nome).col_count == len(aba.colunas)


def test_planilha_nova_na_v2__RN_15() -> None:
    """CA-F16.5: planilha vazia já nasce na versão 2, com 6 abas e 17 categorias."""
    planilha = PlanilhaFalsa()

    preparar_planilha(planilha)

    assert planilha.nomes_das_abas() == [
        "Lancamentos", "Categorias", "Recorrencias", "Config", "Cartoes", "Importacoes",
    ]  # fmt: skip
    assert planilha.linhas("Cartoes") == [CABECALHO_CARTOES]
    assert planilha.linhas("Importacoes") == [CABECALHO_IMPORTACOES]
    assert len(planilha.linhas("Categorias")) == 1 + 17
    assert planilha.linhas("Config") == [CABECALHO_CONFIG, ["versao_schema", 2]]


def test_semeia_as_categorias_padrao__RN_15() -> None:
    """CA-F03.12: uma única escrita; slug, tipo e `ativa = true`; "A classificar" nos dois tipos."""
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
    assert len(categorias) == 17
    assert [c.nome for c in categorias if c.tipo == "GASTO"] == [
        "Alimentação", "Mercado", "Moradia", "Contas da casa", "Transporte", "Saúde",
        "Educação", "Lazer", "Vestuário", "Assinaturas", "Outros gastos", "A classificar",
    ]  # fmt: skip
    assert [c.nome for c in categorias if c.tipo == "RECEITA"] == [
        "Salário", "Freelance", "Rendimentos", "Outras receitas", "A classificar",
    ]  # fmt: skip
    assert all(c.ativa is True for c in categorias)
    assert all(linha[4] is True for linha in linhas)  # booleano de verdade, não texto
    assert {c.id for c in categorias} == {
        "alimentacao", "mercado", "moradia", "contas-da-casa", "transporte", "saude",
        "educacao", "lazer", "vestuario", "assinaturas", "outros-gastos",
        "salario", "freelance", "rendimentos", "outras-receitas",
        "a-classificar", "a-classificar-receita",
    }  # fmt: skip
    for categoria in categorias:
        assert categoria.criado_em <= datetime.now()


def test_categorias_padrao_tem_cor_unica__CA_F03_25() -> None:
    """Cores de F-03 §3.4 (Q2), `#RRGGBB`, sem repetição entre as 15 originais.

    As duas reservadas usam `#90A4AE` (`03` §5.2), a mesma de "Outros gastos".
    """
    planilha = PlanilhaFalsa()

    preparar_planilha(planilha)

    cores = {linha[0]: linha[3] for linha in planilha.linhas("Categorias")[1:]}
    assert cores == {
        "alimentacao": "#E57373", "mercado": "#FF8A65", "moradia": "#7986CB",
        "contas-da-casa": "#4FC3F7", "transporte": "#4DD0E1", "saude": "#F06292",
        "educacao": "#7E57C2", "lazer": "#FFB74D", "vestuario": "#A1887F",
        "assinaturas": "#BA68C8", "outros-gastos": "#90A4AE", "salario": "#66BB6A",
        "freelance": "#9CCC65", "rendimentos": "#26A69A", "outras-receitas": "#AED581",
        "a-classificar": "#90A4AE", "a-classificar-receita": "#90A4AE",
    }  # fmt: skip
    assert all(re.fullmatch(r"#[0-9A-F]{6}", cor) for cor in cores.values())
    assert len(cores) == len(CATEGORIAS_PADRAO) == 17
    originais = [cor for id_, cor in cores.items() if not id_.startswith("a-classificar")]
    assert len(set(originais)) == len(originais) == 15


def test_grava_versao_schema__CA_F03_15() -> None:
    planilha = PlanilhaFalsa()

    preparar_planilha(planilha)

    assert planilha.linhas("Config") == [CABECALHO_CONFIG, ["versao_schema", 2]]


def test_grava_versao_schema_se_so_ela_faltar__CA_F03_15() -> None:
    """Dados sem `versao_schema` contam como versão 1: entram as reservadas e a versão 2."""
    planilha = planilha_pronta(Config=[CABECALHO_CONFIG, ["outra_chave", "x"]])

    preparar_planilha(planilha)

    assert planilha.linhas("Config") == [
        CABECALHO_CONFIG, ["outra_chave", "x"], ["versao_schema", 2],
    ]  # fmt: skip
    assert [linha[0] for linha in planilha.linhas("Categorias")[1:]] == [
        "pet", "a-classificar", "a-classificar-receita",
    ]  # fmt: skip
    assert [(escrita[0], escrita[1]) for escrita in planilha.escritas] == [
        ("append_rows", "Categorias"),
        ("append_rows", "Config"),
    ]


# Planilha já preparada ---------------------------------------------------------


def test_nao_semeia_se_ja_houver_categoria__CA_15_2() -> None:
    """CA-F03.13: basta uma linha, mesmo que o usuário tenha apagado as padrão."""
    planilha = planilha_pronta()

    preparar_planilha(planilha)

    assert planilha.linhas("Categorias") == [CABECALHO_CATEGORIAS, CATEGORIA_DO_USUARIO]


def test_resemeia_se_categorias_esvaziada__RN_15() -> None:
    """Borda 21: aba esvaziada de propósito volta a ter as 17 padrão no próximo início."""
    planilha = planilha_pronta(Categorias=[CABECALHO_CATEGORIAS, ["", "", ""], []])

    preparar_planilha(planilha)

    assert len(planilha.linhas("Categorias")) == 1 + 17


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
    """Na versão 2 a migração não roda: reservada apagada à mão não volta sozinha."""
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
    """Borda 8: a aba que não é do app não é lida, alterada nem apagada."""
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
        (3, "versao_schema 3 é de uma versão mais nova do aplicativo (esta lê até a 2)"),
        ("3", "versao_schema 3 é de uma versão mais nova do aplicativo (esta lê até a 2)"),
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


@pytest.mark.parametrize("valor", [2, 2.0, "2", " 2 "])
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


# Migração 1 → 2 (F-16; `03` §5.4) ----------------------------------------------


def test_migracao_v1_para_v2_preserva_dados__CA_F16_3() -> None:
    """Abas novas, as duas "A classificar" e a versão 2; nenhuma outra linha muda."""
    planilha = planilha_v1()
    antes = fotografia(planilha)

    preparar_planilha(planilha)

    depois = fotografia(planilha)
    criado_em = depois["Categorias"][-1][5]
    assert depois == {
        "Lancamentos": antes["Lancamentos"],
        "Categorias": [
            *antes["Categorias"],
            reservada("a-classificar", "A classificar", "GASTO", criado_em),
            reservada("a-classificar-receita", "A classificar", "RECEITA", criado_em),
        ],
        "Recorrencias": antes["Recorrencias"],
        "Config": [CABECALHO_CONFIG, ["versao_schema", 2]],
        "Cartoes": [CABECALHO_CARTOES],
        "Importacoes": [CABECALHO_IMPORTACOES],
    }
    for linha in depois["Categorias"][-2:]:
        Categoria.model_validate(dict(zip(CABECALHO_CATEGORIAS, linha, strict=True)))
    # A versão é a última escrita: só é marcada depois de tudo o que ela exige.
    assert [escrita[:2] for escrita in planilha.escritas] == [
        ("add_worksheet", "Cartoes"),
        ("update", "Cartoes"),
        ("add_worksheet", "Importacoes"),
        ("update", "Importacoes"),
        ("append_rows", "Categorias"),
        ("update", "Config"),
    ]
    assert planilha.escritas[-1] == ("update", "Config", "B2", [[2]])


def test_migracao_rodar_de_novo_nao_muda_nada__CA_F16_3() -> None:
    planilha = planilha_v1()
    preparar_planilha(planilha)
    antes = fotografia(planilha)
    escritas = len(planilha.escritas)

    preparar_planilha(planilha)

    assert fotografia(planilha) == antes
    assert len(planilha.escritas) == escritas


def test_migracao_atualiza_a_celula_da_versao_onde_ela_estiver__CA_F16_3() -> None:
    """`versao_schema` como texto e fora da linha 2: só a célula dela muda."""
    planilha = planilha_v1(Config=[CABECALHO_CONFIG, ["outra_chave", "x"], ["versao_schema", "1"]])

    preparar_planilha(planilha)

    assert planilha.linhas("Config") == [
        CABECALHO_CONFIG, ["outra_chave", "x"], ["versao_schema", 2],
    ]  # fmt: skip
    assert planilha.escritas[-1] == ("update", "Config", "B3", [[2]])


def test_reservada_com_nome_em_uso__CA_F16_4() -> None:
    """RN-12: o nome já é de outra categoria de gasto → "(importados)"; a de receita não muda."""
    do_usuario = ["pendentes", "A Classificar", "GASTO", "#123456", True, "2026-09-29T10:15:00"]
    planilha = planilha_v1(Categorias=[CABECALHO_CATEGORIAS, do_usuario])

    preparar_planilha(planilha)

    linhas = planilha.linhas("Categorias")
    assert linhas[1] == do_usuario
    assert [linha[:3] for linha in linhas[2:]] == [
        ["a-classificar", "A classificar (importados)", "GASTO"],
        ["a-classificar-receita", "A classificar", "RECEITA"],
    ]


def test_reservada_que_ja_existe_pelo_id_nao_e_duplicada__RN_24() -> None:
    """Categoria criada pelo app na v1 com o slug `a-classificar` vira a reservada, como está."""
    do_usuario = ["a-classificar", "Revisar", "GASTO", "#123456", False, "2026-09-29T10:15:00"]
    planilha = planilha_v1(Categorias=[CABECALHO_CATEGORIAS, do_usuario])

    preparar_planilha(planilha)

    linhas = planilha.linhas("Categorias")
    assert linhas[1] == do_usuario
    assert [linha[0] for linha in linhas[2:]] == ["a-classificar-receita"]


@pytest.mark.parametrize("planilha_de", [planilha_v1, planilha_pronta])
@pytest.mark.parametrize(
    ("id_", "tipo", "trecho"),
    [
        ("a-classificar", "RECEITA", "deveria ter o tipo 'GASTO', mas está 'RECEITA'"),
        ("a-classificar-receita", "GASTO", "deveria ter o tipo 'RECEITA', mas está 'GASTO'"),
        ("a-classificar", "", "deveria ter o tipo 'GASTO', mas está vazio"),
    ],
)
def test_id_reservado_com_outro_tipo_da_erro__RN_24(
    planilha_de: Any, id_: str, tipo: str, trecho: str
) -> None:
    """A importação lançaria gasto em categoria de receita: para antes de escrever."""
    do_usuario = [id_, "A classificar", tipo, "#123456", True, "2026-09-29T10:15:00"]
    planilha = planilha_de(Categorias=[CABECALHO_CATEGORIAS, do_usuario])

    with pytest.raises(SchemaPlanilhaInvalido) as erro:
        preparar_planilha(planilha)

    assert erro.value.mensagem == (
        "A estrutura da planilha não corresponde ao esperado: Categorias, a categoria "
        f"'{id_}' é reservada à importação dos cartões e {trecho}."
    )
    assert planilha.escritas == []


def test_migracao_interrompida_e_retomada_sem_duplicar__CA_F16_3() -> None:
    """Falha depois de gravar as reservadas: a versão segue 1 e a nova execução só a atualiza."""
    planilha = planilha_v1()
    planilha.falhar_em = "append_rows"

    with pytest.raises(RuntimeError):
        preparar_planilha(planilha)

    assert planilha.linhas("Config") == [CABECALHO_CONFIG, ["versao_schema", 1]]
    planilha.falhar_em = None
    escritas = len(planilha.escritas)

    preparar_planilha(planilha)

    assert [linha[0] for linha in planilha.linhas("Categorias")[1:]] == [
        "pet", "a-classificar", "a-classificar-receita",
    ]  # fmt: skip
    assert planilha.linhas("Config") == [CABECALHO_CONFIG, ["versao_schema", 2]]
    assert planilha.escritas[escritas:] == [("update", "Config", "B2", [[2]])]
