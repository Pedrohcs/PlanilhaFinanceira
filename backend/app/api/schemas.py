"""DTOs de entrada e saída da API (`SPECS/03` §6.3)."""

from typing import Literal

from pydantic import BaseModel

STATUS_OK = "ok"
STATUS_DEGRADADO = "degradado"


class ErroSaida(BaseModel):
    """Erro resumido, no mesmo vocabulário de códigos de `SPECS/03` §6.2."""

    codigo: str
    mensagem: str


class PlanilhaSaida(BaseModel):
    ok: bool
    titulo: str | None = None
    erro: ErroSaida | None = None


class SaudeSaida(BaseModel):
    """Resposta de `GET /api/health` — sempre HTTP 200 (`SPECS/03` §6.3)."""

    status: Literal["ok", "degradado"]
    planilha: PlanilhaSaida
