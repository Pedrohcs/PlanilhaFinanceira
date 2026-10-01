"""`/api/resumo` — resumo do mês (REQ-12, dados de REQ-13; F-09) e histórico (REQ-14; F-11)."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import ResumoServiceDep
from app.api.schemas import ResumoHistoricoSaida, ResumoMensalSaida
from app.domain.datas import MES_PADRAO

router = APIRouter(prefix="/resumo", tags=["resumo"])


@router.get("/mensal", response_model=ResumoMensalSaida)
def mensal(
    servico: ResumoServiceDep, mes: Annotated[str, Query(pattern=MES_PADRAO)]
) -> ResumoMensalSaida:
    """Totais, gastos por categoria e por forma (com %) e acumulado diário do mês (RN-03)."""
    return ResumoMensalSaida.de(servico.mensal(mes))


@router.get("/historico", response_model=ResumoHistoricoSaida)
def historico(
    servico: ResumoServiceDep,
    inicio: Annotated[str | None, Query(pattern=MES_PADRAO)] = None,
    fim: Annotated[str | None, Query(pattern=MES_PADRAO)] = None,
) -> ResumoHistoricoSaida:
    """Totais mês a mês e gastos por categoria; sem período, os 12 meses até o corrente."""
    return ResumoHistoricoSaida.de(servico.historico(inicio, fim))
