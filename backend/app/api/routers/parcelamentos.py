"""`/api/parcelamentos` — compra parcelada e exclusão do parcelamento (REQ-07, REQ-08; F-12)."""

from fastapi import APIRouter, Response, status

from app.api.deps import ParcelamentoServiceDep
from app.api.schemas import ParcelamentoEntrada, ParcelamentoSaida

router = APIRouter(prefix="/parcelamentos", tags=["parcelamentos"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ParcelamentoSaida)
def criar(entrada: ParcelamentoEntrada, servico: ParcelamentoServiceDep) -> ParcelamentoSaida:
    """Uma parcela por mês (RN-07), todas gravadas numa única escrita."""
    return ParcelamentoSaida.de(servico.criar(**entrada.model_dump()))


@router.delete("/{parcelamento_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(parcelamento_id: str, servico: ParcelamentoServiceDep) -> Response:
    """Todas as parcelas restantes, em qualquer mês (CA-08.2)."""
    servico.excluir(parcelamento_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
