"""Repositórios sobre a planilha Google (`SPECS/03` §4.3).

Com `infra`, é o único lugar que conhece o gspread (`03` §4.2).
"""

from app.domain.modelos import Cartao, Categoria, Importacao, Lancamento, Recorrencia
from app.infra.schema_planilha import (
    ABA_CARTOES,
    ABA_CATEGORIAS,
    ABA_IMPORTACOES,
    ABA_LANCAMENTOS,
    ABA_RECORRENCIAS,
)
from app.repositories.planilha.aba import FontePlanilha, RepositorioPlanilha


class LancamentoRepositoryPlanilha(RepositorioPlanilha[Lancamento]):
    aba = ABA_LANCAMENTOS
    modelo = Lancamento


class CategoriaRepositoryPlanilha(RepositorioPlanilha[Categoria]):
    aba = ABA_CATEGORIAS
    modelo = Categoria


class RecorrenciaRepositoryPlanilha(RepositorioPlanilha[Recorrencia]):
    aba = ABA_RECORRENCIAS
    modelo = Recorrencia


class CartaoRepositoryPlanilha(RepositorioPlanilha[Cartao]):
    aba = ABA_CARTOES
    modelo = Cartao


class ImportacaoRepositoryPlanilha(RepositorioPlanilha[Importacao]):
    aba = ABA_IMPORTACOES
    modelo = Importacao


__all__ = [
    "CartaoRepositoryPlanilha",
    "CategoriaRepositoryPlanilha",
    "FontePlanilha",
    "ImportacaoRepositoryPlanilha",
    "LancamentoRepositoryPlanilha",
    "RecorrenciaRepositoryPlanilha",
    "RepositorioPlanilha",
]
