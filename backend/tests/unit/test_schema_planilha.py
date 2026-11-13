"""Abas e colunas da planilha (`SPECS/03` §5; F-03 §3.3)."""

import pytest
from pydantic import BaseModel

from app.domain.modelos import Cartao, Categoria, Importacao, Lancamento, Recorrencia
from app.infra.schema_planilha import (
    ABA_CARTOES,
    ABA_CATEGORIAS,
    ABA_CONFIG,
    ABA_IMPORTACOES,
    ABA_LANCAMENTOS,
    ABA_RECORRENCIAS,
    ABAS,
    CHAVE_VERSAO_SCHEMA,
    VERSAO_SCHEMA,
    Aba,
)


def test_colunas_iguais_a_03_secao_5() -> None:
    """Transcrição literal de `03` §5.1–5.4, §5.7 e §5.8: nomes e ordem (versão 2, F-16)."""
    assert [aba.nome for aba in ABAS] == [
        "Lancamentos", "Categorias", "Recorrencias", "Config", "Cartoes", "Importacoes",
    ]  # fmt: skip
    assert ABA_LANCAMENTOS.colunas == (
        "id", "data", "tipo", "descricao", "valor", "categoria_id", "forma_pagamento",
        "observacao", "parcelamento_id", "parcela_numero", "parcela_total", "recorrencia_id",
        "criado_em", "atualizado_em",
    )  # fmt: skip
    assert ABA_CATEGORIAS.colunas == ("id", "nome", "tipo", "cor", "ativa", "criado_em")
    assert ABA_RECORRENCIAS.colunas == (
        "id", "tipo", "descricao", "valor", "categoria_id", "forma_pagamento", "dia_do_mes",
        "mes_inicio", "mes_fim", "status", "ultimo_mes_gerado", "criado_em", "atualizado_em",
    )  # fmt: skip
    assert ABA_CONFIG.colunas == ("chave", "valor")
    assert ABA_CARTOES.colunas == (
        "id", "item_id", "banco", "nome", "final", "ultima_importacao", "criado_em",
        "atualizado_em",
    )  # fmt: skip
    assert ABA_IMPORTACOES.colunas == (
        "id", "transacao_id", "provider_id", "cartao_id", "lancamento_id", "situacao", "data",
        "tipo", "valor", "descricao", "status_pluggy", "criado_em", "atualizado_em",
    )  # fmt: skip
    assert [len(aba.colunas) for aba in ABAS] == [14, 6, 13, 2, 8, 13]
    assert (CHAVE_VERSAO_SCHEMA, VERSAO_SCHEMA) == ("versao_schema", 2)


@pytest.mark.parametrize(
    ("aba", "modelo"),
    [
        (ABA_LANCAMENTOS, Lancamento),
        (ABA_CATEGORIAS, Categoria),
        (ABA_RECORRENCIAS, Recorrencia),
        (ABA_CARTOES, Cartao),
        (ABA_IMPORTACOES, Importacao),
    ],
)
def test_colunas_na_ordem_dos_modelos(aba: Aba, modelo: type[BaseModel]) -> None:
    """Modelo e aba descrevem a mesma linha: nenhum campo sobra ou falta (T-009 depende disso)."""
    assert tuple(modelo.model_fields) == aba.colunas
