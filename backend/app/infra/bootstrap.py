"""Preparação idempotente da planilha (REQ-15; `SPECS/03` §4.5, F-03 §3.4).

Roda a cada conexão estabelecida, em duas fases:

1. **Validação** (só leitura): cabeçalhos das abas e `versao_schema`. Qualquer
   divergência levanta `SchemaPlanilhaInvalido` antes de escrever uma célula.
2. **Escrita** do que falta: abas, colunas no fim, `versao_schema` e o seed
   das categorias padrão (RN-15) quando a aba `Categorias` está vazia.

Rodar de novo numa planilha pronta não escreve nada (CA-15.2).
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Any

import gspread
from gspread.utils import ValueInputOption, ValueRenderOption, rowcol_to_a1

from app.domain.datas import agora
from app.domain.enums import TipoLancamento
from app.domain.erros import SchemaPlanilhaInvalido
from app.infra.schema_planilha import (
    ABA_CATEGORIAS,
    ABA_CONFIG,
    ABAS,
    CHAVE_VERSAO_SCHEMA,
    VERSAO_SCHEMA,
    Aba,
)

LINHAS_ABA_NOVA = 1000

GASTO = TipoLancamento.GASTO
RECEITA = TipoLancamento.RECEITA

# RN-15, com `id` e cor de F-03 §3.4 (Q2).
CATEGORIAS_PADRAO: tuple[tuple[str, str, TipoLancamento, str], ...] = (
    ("alimentacao", "Alimentação", GASTO, "#E57373"),
    ("mercado", "Mercado", GASTO, "#FF8A65"),
    ("moradia", "Moradia", GASTO, "#7986CB"),
    ("contas-da-casa", "Contas da casa", GASTO, "#4FC3F7"),
    ("transporte", "Transporte", GASTO, "#4DD0E1"),
    ("saude", "Saúde", GASTO, "#F06292"),
    ("educacao", "Educação", GASTO, "#7E57C2"),
    ("lazer", "Lazer", GASTO, "#FFB74D"),
    ("vestuario", "Vestuário", GASTO, "#A1887F"),
    ("assinaturas", "Assinaturas", GASTO, "#BA68C8"),
    ("outros-gastos", "Outros gastos", GASTO, "#90A4AE"),
    ("salario", "Salário", RECEITA, "#66BB6A"),
    ("freelance", "Freelance", RECEITA, "#9CCC65"),
    ("rendimentos", "Rendimentos", RECEITA, "#26A69A"),
    ("outras-receitas", "Outras receitas", RECEITA, "#AED581"),
)

logger = logging.getLogger(__name__)


@dataclass
class _Plano:
    """O que a fase de escrita precisa fazer; montado só por leituras."""

    abas: dict[str, gspread.Worksheet] = field(default_factory=dict)
    abas_a_criar: list[Aba] = field(default_factory=list)
    colunas_a_acrescentar: list[tuple[gspread.Worksheet, Aba, int]] = field(default_factory=list)
    gravar_versao: bool = False
    semear_categorias: bool = False


def preparar_planilha(documento: gspread.Spreadsheet) -> None:
    """Valida a estrutura e cria o que falta. Idempotente (CA-15.2)."""
    plano = _validar(documento)
    _aplicar(documento, plano)


def _validar(documento: gspread.Spreadsheet) -> _Plano:
    existentes = {aba.title: aba for aba in documento.worksheets()}
    plano = _Plano(abas=existentes)

    for aba in ABAS:
        planilha_aba = existentes.get(aba.nome)
        if planilha_aba is None:
            plano.abas_a_criar.append(aba)
            continue
        cabecalho = _normalizar(
            planilha_aba.row_values(1, value_render_option=ValueRenderOption.unformatted)
        )
        _conferir_cabecalho(aba, cabecalho)
        if len(cabecalho) < len(aba.colunas):
            plano.colunas_a_acrescentar.append((planilha_aba, aba, len(cabecalho)))
        elif len(cabecalho) > len(aba.colunas):
            logger.info(
                "Aba %s tem colunas extras após a última do schema; serão ignoradas: %s",
                aba.nome,
                ", ".join(cabecalho[len(aba.colunas) :]),
            )

    config = existentes.get(ABA_CONFIG.nome)
    plano.gravar_versao = config is None or not _versao_gravada(_linhas_de_dados(config))

    categorias = existentes.get(ABA_CATEGORIAS.nome)
    plano.semear_categorias = categorias is None or not _linhas_de_dados(categorias)
    return plano


def _aplicar(documento: gspread.Spreadsheet, plano: _Plano) -> None:
    for aba in plano.abas_a_criar:
        nova = documento.add_worksheet(title=aba.nome, rows=LINHAS_ABA_NOVA, cols=len(aba.colunas))
        _escrever_cabecalho(nova, list(aba.colunas), coluna_inicial=1)
        plano.abas[aba.nome] = nova
        logger.info("Aba %s criada com cabeçalho", aba.nome)

    for planilha_aba, aba, existentes in plano.colunas_a_acrescentar:
        faltam = list(aba.colunas[existentes:])
        if planilha_aba.col_count < len(aba.colunas):
            planilha_aba.add_cols(len(aba.colunas) - planilha_aba.col_count)
        _escrever_cabecalho(planilha_aba, faltam, coluna_inicial=existentes + 1)
        logger.info("Aba %s: colunas acrescentadas no fim: %s", aba.nome, ", ".join(faltam))

    if plano.gravar_versao:
        plano.abas[ABA_CONFIG.nome].append_rows(
            values=[[CHAVE_VERSAO_SCHEMA, VERSAO_SCHEMA]],
            value_input_option=ValueInputOption.raw,
        )
        logger.info("versao_schema gravada: %d", VERSAO_SCHEMA)

    if plano.semear_categorias:
        criado_em = agora().isoformat()
        plano.abas[ABA_CATEGORIAS.nome].append_rows(
            values=[
                [id_, nome, tipo.value, cor, True, criado_em]
                for id_, nome, tipo, cor in CATEGORIAS_PADRAO
            ],
            value_input_option=ValueInputOption.raw,
        )
        logger.info("Categorias padrão inseridas: %d", len(CATEGORIAS_PADRAO))


def _escrever_cabecalho(
    planilha_aba: gspread.Worksheet, nomes: list[str], *, coluna_inicial: int
) -> None:
    planilha_aba.update(
        values=[nomes],
        range_name=rowcol_to_a1(1, coluna_inicial),
        value_input_option=ValueInputOption.raw,
    )


def _normalizar(linha: list[Any]) -> list[str]:
    """Células como texto, sem espaços em volta e sem vazias no fim."""
    valores = [str(celula).strip() for celula in linha]
    while valores and not valores[-1]:
        valores.pop()
    return valores


def _conferir_cabecalho(aba: Aba, cabecalho: list[str]) -> None:
    """O cabeçalho tem de começar pelas colunas do schema, na ordem."""
    for posicao, (esperado, atual) in enumerate(zip(aba.colunas, cabecalho, strict=False), 1):
        if atual != esperado:
            encontrado = f"'{atual}'" if atual else "vazia"
            raise SchemaPlanilhaInvalido.para(
                aba.nome,
                f"coluna {_letra(posicao)} deveria ser '{esperado}', mas está {encontrado}",
            )


def _linhas_de_dados(planilha_aba: gspread.Worksheet) -> list[list[str]]:
    """Linhas após o cabeçalho com ao menos uma célula preenchida."""
    linhas = planilha_aba.get_all_values(value_render_option=ValueRenderOption.unformatted)
    return [normalizada for linha in linhas[1:] if (normalizada := _normalizar(linha))]


def _versao_gravada(linhas_config: list[list[str]]) -> bool:
    """Se `versao_schema` existe e é legível por este app; levanta se não for."""
    for linha in linhas_config:
        if linha[0] == CHAVE_VERSAO_SCHEMA:
            _conferir_versao(linha[1] if len(linha) > 1 else "")
            return True
    return False


def _conferir_versao(valor: str) -> None:
    try:
        numero = float(valor)
    except ValueError:
        numero = math.nan
    if not math.isfinite(numero) or numero != int(numero):
        raise SchemaPlanilhaInvalido.para(
            ABA_CONFIG.nome, f"{CHAVE_VERSAO_SCHEMA} '{valor}' não é um número inteiro"
        )
    versao = int(numero)
    if versao > VERSAO_SCHEMA:
        raise SchemaPlanilhaInvalido.para(
            ABA_CONFIG.nome,
            f"{CHAVE_VERSAO_SCHEMA} {versao} é de uma versão mais nova do aplicativo "
            f"(esta lê até a {VERSAO_SCHEMA})",
        )
    if versao < 1:
        raise SchemaPlanilhaInvalido.para(
            ABA_CONFIG.nome, f"{CHAVE_VERSAO_SCHEMA} {versao} não é uma versão válida"
        )


def _letra(coluna: int) -> str:
    """1 → `A`, 14 → `N`, 27 → `AA`."""
    return rowcol_to_a1(1, coluna).removesuffix("1")
