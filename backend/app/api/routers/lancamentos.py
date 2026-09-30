"""`/api/lancamentos` — registro de gastos e receitas (REQ-01, REQ-02; F-06).

Listar, editar e excluir entram em F-07 e F-08.
"""

from fastapi import APIRouter, status

from app.api.deps import LancamentoServiceDep
from app.api.schemas import LancamentoEntrada, LancamentoSaida

router = APIRouter(prefix="/lancamentos", tags=["lancamentos"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=LancamentoSaida)
def criar(entrada: LancamentoEntrada, servico: LancamentoServiceDep) -> LancamentoSaida:
    return LancamentoSaida.de(servico.criar(**entrada.model_dump()))
