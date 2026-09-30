"""Composição: é aqui (e em `main.py`) que a API conhece a infraestrutura.

Os routers importam só os aliases `...Dep` — assim nenhum arquivo de router
importa `app.infra` nem `gspread` (regra de camadas, `SPECS/03` §4.2).
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from app.infra.cache import CacheAbas
from app.infra.sheets_client import ConexaoPlanilha
from app.repositories.base import (
    CategoriaRepository,
    LancamentoRepository,
    RecorrenciaRepository,
)
from app.repositories.planilha import (
    CategoriaRepositoryPlanilha,
    LancamentoRepositoryPlanilha,
    RecorrenciaRepositoryPlanilha,
)
from app.services.categoria_service import CategoriaService
from app.services.lancamento_service import LancamentoService
from app.services.parcelamento_service import ParcelamentoService


@dataclass(frozen=True)
class Repositorios:
    """Os repositórios do app. Testes de API trocam por `repositories.memoria` (`02` §8)."""

    categorias: CategoriaRepository
    lancamentos: LancamentoRepository
    recorrencias: RecorrenciaRepository


def criar_repositorios_planilha(conexao: ConexaoPlanilha, cache: CacheAbas) -> Repositorios:
    """Uma instância de cada, para o processo inteiro: preserva o cache e as
    referências de aba (T-009) entre requisições."""
    return Repositorios(
        categorias=CategoriaRepositoryPlanilha(conexao, cache),
        lancamentos=LancamentoRepositoryPlanilha(conexao, cache),
        recorrencias=RecorrenciaRepositoryPlanilha(conexao, cache),
    )


def obter_conexao(request: Request) -> ConexaoPlanilha:
    """Conexão criada no lifespan e guardada no estado da aplicação."""
    return request.app.state.conexao


def obter_repositorios(request: Request) -> Repositorios:
    """Repositórios criados no lifespan (`main.py`)."""
    return request.app.state.repositorios


def obter_categoria_service(
    repositorios: Annotated[Repositorios, Depends(obter_repositorios)],
) -> CategoriaService:
    return CategoriaService(
        repositorios.categorias, repositorios.lancamentos, repositorios.recorrencias
    )


def obter_lancamento_service(
    repositorios: Annotated[Repositorios, Depends(obter_repositorios)],
) -> LancamentoService:
    return LancamentoService(repositorios.categorias, repositorios.lancamentos)


def obter_parcelamento_service(
    repositorios: Annotated[Repositorios, Depends(obter_repositorios)],
) -> ParcelamentoService:
    return ParcelamentoService(repositorios.categorias, repositorios.lancamentos)


ConexaoDep = Annotated[ConexaoPlanilha, Depends(obter_conexao)]
CategoriaServiceDep = Annotated[CategoriaService, Depends(obter_categoria_service)]
LancamentoServiceDep = Annotated[LancamentoService, Depends(obter_lancamento_service)]
ParcelamentoServiceDep = Annotated[ParcelamentoService, Depends(obter_parcelamento_service)]
