"""`/api/lancamentos` — registro, listagem, edição e exclusão (REQ-01..06; F-06..F-08)."""

from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import LancamentoServiceDep
from app.api.schemas import LancamentoEntrada, LancamentoSaida, ListaLancamentosSaida
from app.domain.datas import MES_PADRAO
from app.domain.enums import FormaPagamento, TipoLancamento

router = APIRouter(prefix="/lancamentos", tags=["lancamentos"])


@router.get("", response_model=ListaLancamentosSaida)
def listar(
    servico: LancamentoServiceDep,
    mes: Annotated[str, Query(pattern=MES_PADRAO)],
    tipo: TipoLancamento | None = None,
    categoria_id: str | None = None,
    forma_pagamento: FormaPagamento | None = None,
) -> ListaLancamentosSaida:
    """Lançamentos do mês (RN-03), filtros combinados, totais do que foi filtrado (CA-03.2)."""
    return ListaLancamentosSaida.de(
        servico.listar(mes, tipo=tipo, categoria_id=categoria_id, forma_pagamento=forma_pagamento)
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=LancamentoSaida)
def criar(entrada: LancamentoEntrada, servico: LancamentoServiceDep) -> LancamentoSaida:
    return LancamentoSaida.de(servico.criar(**entrada.model_dump()))


@router.put("/{id}", response_model=LancamentoSaida)
def editar(id: str, entrada: LancamentoEntrada, servico: LancamentoServiceDep) -> LancamentoSaida:
    """Qualquer campo (REQ-05); só a linha do `id` muda (CA-05.2)."""
    return LancamentoSaida.de(servico.editar(id, **entrada.model_dump()))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(id: str, servico: LancamentoServiceDep) -> Response:
    servico.excluir(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
