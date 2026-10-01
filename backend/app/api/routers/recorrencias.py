"""`/api/recorrencias` — cadastro, edição e status (REQ-09; F-13 §3.1).

A sincronização (`POST /api/recorrencias/sincronizar`, REQ-10) chega em T-029.
"""

from fastapi import APIRouter, status

from app.api.deps import RecorrenciaServiceDep
from app.api.schemas import RecorrenciaEntrada, RecorrenciaSaida, StatusEntrada

router = APIRouter(prefix="/recorrencias", tags=["recorrencias"])


@router.get("", response_model=list[RecorrenciaSaida])
def listar(servico: RecorrenciaServiceDep) -> list[RecorrenciaSaida]:
    """Ativas, pausadas e encerradas, com o próximo mês a gerar (CA-09.1)."""
    return [RecorrenciaSaida.de(item) for item in servico.listar()]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=RecorrenciaSaida)
def criar(entrada: RecorrenciaEntrada, servico: RecorrenciaServiceDep) -> RecorrenciaSaida:
    return RecorrenciaSaida.de(servico.criar(**entrada.model_dump()))


@router.put("/{id}", response_model=RecorrenciaSaida)
def editar(
    id: str, entrada: RecorrenciaEntrada, servico: RecorrenciaServiceDep
) -> RecorrenciaSaida:
    """Vale só para os lançamentos gerados depois (CA-09.2)."""
    return RecorrenciaSaida.de(servico.editar(id, **entrada.model_dump()))


@router.patch("/{id}/status", response_model=RecorrenciaSaida)
def mudar_status(
    id: str, entrada: StatusEntrada, servico: RecorrenciaServiceDep
) -> RecorrenciaSaida:
    """Pausar, reativar (sem retroativos — RN-11) ou encerrar (definitivo)."""
    return RecorrenciaSaida.de(servico.mudar_status(id, entrada.status))
