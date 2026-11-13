"""Preparação idempotente da planilha (REQ-15; `SPECS/03` §4.5, F-03 §3.4).

Roda a cada conexão estabelecida, em duas fases:

1. **Validação** (só leitura): cabeçalhos das abas e `versao_schema`. Qualquer
   divergência levanta `SchemaPlanilhaInvalido` antes de escrever uma célula.
2. **Escrita** do que falta: abas, colunas no fim, o seed das categorias
   padrão (RN-15) quando a aba `Categorias` está vazia e `versao_schema`.

**Migração 1 → 2** (F-16; `03` §5.4): planilha na versão 1 — ou com dados e sem
`versao_schema` — ganha as abas `Cartoes` e `Importacoes` (como qualquer aba
ausente), as categorias reservadas "A classificar" que faltarem e, por último,
`versao_schema = 2`. A versão vai por último: se uma escrita falhar no meio, a
próxima execução refaz só o que faltou.

Rodar de novo numa planilha pronta não escreve nada (CA-15.2).
"""

import logging
import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

import gspread
from gspread.utils import InsertDataOption, ValueInputOption, ValueRenderOption, rowcol_to_a1

from app.domain.datas import agora
from app.domain.enums import TipoLancamento
from app.domain.erros import SchemaPlanilhaInvalido
from app.domain.modelos import (
    ID_A_CLASSIFICAR,
    ID_A_CLASSIFICAR_RECEITA,
    TIPO_DA_CATEGORIA_RESERVADA,
)
from app.domain.textos import chave_sem_acento_e_caixa
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

# Categorias reservadas da importação dos cartões (RN-15, RN-24; `03` §5.2).
NOME_RESERVADA = "A classificar"
NOME_RESERVADA_SE_EM_USO = "A classificar (importados)"
COR_RESERVADA = "#90A4AE"

# RN-15, com `id` e cor de F-03 §3.4 (Q2); as "A classificar" fecham cada tipo (F-16).
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
    (ID_A_CLASSIFICAR, NOME_RESERVADA, GASTO, COR_RESERVADA),
    ("salario", "Salário", RECEITA, "#66BB6A"),
    ("freelance", "Freelance", RECEITA, "#9CCC65"),
    ("rendimentos", "Rendimentos", RECEITA, "#26A69A"),
    ("outras-receitas", "Outras receitas", RECEITA, "#AED581"),
    (ID_A_CLASSIFICAR_RECEITA, NOME_RESERVADA, RECEITA, COR_RESERVADA),
)

_COLUNA_ID, _COLUNA_NOME, _COLUNA_TIPO = (
    ABA_CATEGORIAS.colunas.index(coluna) for coluna in ("id", "nome", "tipo")
)
_COLUNA_VALOR_CONFIG = ABA_CONFIG.colunas.index("valor") + 1

logger = logging.getLogger(__name__)


@dataclass
class _Plano:
    """O que a fase de escrita precisa fazer; montado só por leituras."""

    abas: dict[str, gspread.Worksheet] = field(default_factory=dict)
    abas_a_criar: list[Aba] = field(default_factory=list)
    colunas_a_acrescentar: list[tuple[gspread.Worksheet, Aba, int]] = field(default_factory=list)
    semear_categorias: bool = False
    # Migração 1 → 2: (id, nome, tipo, cor) das reservadas que faltam.
    reservadas_a_acrescentar: list[tuple[str, str, TipoLancamento, str]] = field(
        default_factory=list
    )
    gravar_versao: bool = False  # não há linha `versao_schema`: acrescenta
    linha_da_versao_antiga: int | None = None  # há, com versão anterior: atualiza a célula


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
    gravada = _versao_gravada(config) if config is not None else None
    if gravada is None:
        plano.gravar_versao = True
    elif gravada[1] < VERSAO_SCHEMA:
        plano.linha_da_versao_antiga = gravada[0]

    categorias = existentes.get(ABA_CATEGORIAS.nome)
    linhas_de_categorias = _linhas_de_dados(categorias) if categorias is not None else []
    if not linhas_de_categorias:
        plano.semear_categorias = True  # o seed já traz as reservadas
        return plano
    _conferir_reservadas(linhas_de_categorias)
    if plano.gravar_versao or plano.linha_da_versao_antiga is not None:
        plano.reservadas_a_acrescentar = _reservadas_que_faltam(linhas_de_categorias)
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

    if plano.semear_categorias:
        _acrescentar_categorias(plano.abas[ABA_CATEGORIAS.nome], CATEGORIAS_PADRAO)
        logger.info("Categorias padrão inseridas: %d", len(CATEGORIAS_PADRAO))
    elif plano.reservadas_a_acrescentar:
        _acrescentar_categorias(plano.abas[ABA_CATEGORIAS.nome], plano.reservadas_a_acrescentar)
        logger.info(
            "Categorias reservadas inseridas: %s",
            ", ".join(id_ for id_, *_ in plano.reservadas_a_acrescentar),
        )

    # Por último: só marca a versão nova depois que tudo o que ela exige foi gravado.
    config = plano.abas[ABA_CONFIG.nome]
    if plano.gravar_versao:
        config.append_rows(
            values=[[CHAVE_VERSAO_SCHEMA, VERSAO_SCHEMA]],
            value_input_option=ValueInputOption.raw,
            insert_data_option=InsertDataOption.insert_rows,
        )
        logger.info("versao_schema gravada: %d", VERSAO_SCHEMA)
    elif plano.linha_da_versao_antiga is not None:
        config.update(
            values=[[VERSAO_SCHEMA]],
            range_name=rowcol_to_a1(plano.linha_da_versao_antiga, _COLUNA_VALOR_CONFIG),
            value_input_option=ValueInputOption.raw,
        )
        logger.info("Planilha migrada para a versao_schema %d", VERSAO_SCHEMA)


def _acrescentar_categorias(
    planilha_aba: gspread.Worksheet,
    categorias: Iterable[tuple[str, str, TipoLancamento, str]],
) -> None:
    """Uma única escrita, com `ativa = true` e o mesmo `criado_em`."""
    criado_em = agora().isoformat()
    planilha_aba.append_rows(
        values=[
            [id_, nome, tipo.value, cor, True, criado_em] for id_, nome, tipo, cor in categorias
        ],
        value_input_option=ValueInputOption.raw,
        insert_data_option=InsertDataOption.insert_rows,
    )


def _celula(linha: list[str], coluna: int) -> str:
    return linha[coluna] if coluna < len(linha) else ""


def _conferir_reservadas(linhas_de_categorias: list[list[str]]) -> None:
    """Id reservado ocupado por categoria do outro tipo: a importação lançaria no tipo errado."""
    for linha in linhas_de_categorias:
        esperado = TIPO_DA_CATEGORIA_RESERVADA.get(_celula(linha, _COLUNA_ID))
        tipo = _celula(linha, _COLUNA_TIPO)
        if esperado is not None and tipo != esperado.value:
            encontrado = f"'{tipo}'" if tipo else "vazio"
            raise SchemaPlanilhaInvalido.para(
                ABA_CATEGORIAS.nome,
                f"a categoria '{_celula(linha, _COLUNA_ID)}' é reservada à importação dos "
                f"cartões e deveria ter o tipo '{esperado.value}', mas está {encontrado}",
            )


def _reservadas_que_faltam(
    linhas_de_categorias: list[list[str]],
) -> list[tuple[str, str, TipoLancamento, str]]:
    """Reservadas cujo **id** não existe; nome alternativo se "A classificar" já é de outra."""
    ids = {_celula(linha, _COLUNA_ID) for linha in linhas_de_categorias}
    chave = chave_sem_acento_e_caixa(NOME_RESERVADA)
    faltam = []
    for id_, tipo in TIPO_DA_CATEGORIA_RESERVADA.items():
        if id_ in ids:
            continue
        nome_em_uso = any(
            _celula(linha, _COLUNA_TIPO) == tipo.value
            and chave_sem_acento_e_caixa(_celula(linha, _COLUNA_NOME)) == chave
            for linha in linhas_de_categorias
        )  # RN-12: nome único por tipo
        nome = NOME_RESERVADA_SE_EM_USO if nome_em_uso else NOME_RESERVADA
        faltam.append((id_, nome, tipo, COR_RESERVADA))
    return faltam


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


def _versao_gravada(config: gspread.Worksheet) -> tuple[int, int] | None:
    """(linha, versão) de `versao_schema`, se existe; levanta se este app não sabe lê-la."""
    linhas = config.get_all_values(value_render_option=ValueRenderOption.unformatted)
    for numero, linha in enumerate(linhas[1:], start=2):
        normalizada = _normalizar(linha)
        if normalizada and normalizada[0] == CHAVE_VERSAO_SCHEMA:
            return numero, _conferir_versao(normalizada[1] if len(normalizada) > 1 else "")
    return None


def _conferir_versao(valor: str) -> int:
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
    return versao


def _letra(coluna: int) -> str:
    """1 → `A`, 14 → `N`, 27 → `AA`."""
    return rowcol_to_a1(1, coluna).removesuffix("1")
