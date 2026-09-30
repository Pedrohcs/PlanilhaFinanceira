"""Aplicação FastAPI (`SPECS/03` §3).

Junto com `api/deps.py`, é o único lugar que conhece a infraestrutura
concreta (`SPECS/03` §4.2).
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import criar_repositorios_planilha
from app.api.erros import registrar_handlers
from app.api.routers import categorias, health
from app.config import Settings, obter_settings
from app.infra.bootstrap import preparar_planilha
from app.infra.cache import CacheAbas
from app.infra.sheets_client import ConexaoPlanilha

TITULO = "Planilha Financeira"
VERSAO = "0.1.0"
PREFIXO_API = "/api"

logger = logging.getLogger(__name__)


def configurar_logs() -> None:
    """Log padrão em nível INFO (`SPECS/02` §3). Não repete configuração."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def criar_app(settings: Settings | None = None, conexao: ConexaoPlanilha | None = None) -> FastAPI:
    """Cria a aplicação com CORS, handlers de erro e as rotas (`SPECS/02` §3).

    `conexao` permite injetar um dublê nos testes: o estado da conexão nasce no
    lifespan, onde `dependency_overrides` não alcança.
    """
    configurar_logs()
    config = settings or obter_settings()
    conexao_planilha = conexao or ConexaoPlanilha(
        config.google_credentials_path, config.spreadsheet_id, preparar=preparar_planilha
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Tenta conectar **uma vez**; falha não derruba o servidor (§4.5).

        Conectar inclui o `bootstrap` das abas (`preparar_planilha`), que volta
        a rodar se a conexão só for estabelecida depois, pelo health.

        Cache e repositórios são únicos no processo (`02` §5.5; T-009).
        """
        app.state.conexao = conexao_planilha
        app.state.repositorios = criar_repositorios_planilha(
            conexao_planilha, CacheAbas(config.cache_ttl_segundos)
        )
        conexao_planilha.conectar()
        yield

    app = FastAPI(title=TITULO, version=VERSAO, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    registrar_handlers(app)
    app.include_router(health.router, prefix=PREFIXO_API)
    app.include_router(categorias.router, prefix=PREFIXO_API)
    return app


app = criar_app()
