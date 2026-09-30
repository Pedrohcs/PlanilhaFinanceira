"""Abas e colunas da planilha (`SPECS/03` §5) — fonte única.

Nenhum outro módulo escreve nome de aba ou de coluna literal: todos leem
daqui. Colunas novas só podem ser acrescentadas **no fim** de uma aba, e toda
mudança de schema incrementa `VERSAO_SCHEMA` (`03` §5.4).
"""

from dataclasses import dataclass

VERSAO_SCHEMA = 1
CHAVE_VERSAO_SCHEMA = "versao_schema"


@dataclass(frozen=True)
class Aba:
    nome: str
    colunas: tuple[str, ...]


ABA_LANCAMENTOS = Aba(
    "Lancamentos",
    (
        "id",
        "data",
        "tipo",
        "descricao",
        "valor",
        "categoria_id",
        "forma_pagamento",
        "observacao",
        "parcelamento_id",
        "parcela_numero",
        "parcela_total",
        "recorrencia_id",
        "criado_em",
        "atualizado_em",
    ),
)

ABA_CATEGORIAS = Aba(
    "Categorias",
    ("id", "nome", "tipo", "cor", "ativa", "criado_em"),
)

ABA_RECORRENCIAS = Aba(
    "Recorrencias",
    (
        "id",
        "tipo",
        "descricao",
        "valor",
        "categoria_id",
        "forma_pagamento",
        "dia_do_mes",
        "mes_inicio",
        "mes_fim",
        "status",
        "ultimo_mes_gerado",
        "criado_em",
        "atualizado_em",
    ),
)

ABA_CONFIG = Aba("Config", ("chave", "valor"))

ABAS = (ABA_LANCAMENTOS, ABA_CATEGORIAS, ABA_RECORRENCIAS, ABA_CONFIG)
