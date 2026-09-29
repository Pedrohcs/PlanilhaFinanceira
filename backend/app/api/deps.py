"""Composição: é aqui (e em `main.py`) que a API conhece a infraestrutura.

Os routers importam só o alias `ConexaoDep` — assim nenhum arquivo de router
importa `app.infra` nem `gspread` (regra de camadas, `SPECS/03` §4.2).
"""

from typing import Annotated

from fastapi import Depends, Request

from app.infra.sheets_client import ConexaoPlanilha


def obter_conexao(request: Request) -> ConexaoPlanilha:
    """Conexão criada no lifespan e guardada no estado da aplicação."""
    return request.app.state.conexao


ConexaoDep = Annotated[ConexaoPlanilha, Depends(obter_conexao)]
