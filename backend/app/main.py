"""Aplicação FastAPI (SPECS/03 §3).

Esqueleto: só CORS. Os endpoints do contrato (§6.1), os handlers de erro
e o lifespan entram em T-005.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, obter_settings

TITULO = "Planilha Financeira"
VERSAO = "0.1.0"


def criar_app(settings: Settings | None = None) -> FastAPI:
    """Cria a aplicação com CORS restrito às origens configuradas (SPECS/02 §3)."""
    config = settings or obter_settings()
    app = FastAPI(title=TITULO, version=VERSAO)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


app = criar_app()
