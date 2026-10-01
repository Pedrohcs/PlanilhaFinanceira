"""`/api/recorrencias` — cadastro, edição, status e sincronização (REQ-09, REQ-10; F-13)."""

from fastapi import APIRouter, status

from app.api.deps import RecorrenciaServiceDep
from app.api.schemas import (
    RecorrenciaEntrada,
    RecorrenciaSaida,
    SincronizacaoSaida,
    StatusEntrada,
)

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


@router.post("/sincronizar", response_model=SincronizacaoSaida)
def sincronizar(servico: RecorrenciaServiceDep) -> SincronizacaoSaida:
    """Gera os lançamentos devidos até o mês corrente (REQ-10); repetir não duplica (CA-10.2)."""
    return SincronizacaoSaida.de(servico.sincronizar())
