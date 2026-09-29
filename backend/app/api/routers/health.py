"""`GET /api/health` — estado da conexão com a planilha (REQ-16)."""

from fastapi import APIRouter

from app.api.deps import ConexaoDep
from app.api.schemas import (
    STATUS_DEGRADADO,
    STATUS_OK,
    ErroSaida,
    PlanilhaSaida,
    SaudeSaida,
)

router = APIRouter(tags=["sistema"])


@router.get("/health", response_model=SaudeSaida)
def health(conexao: ConexaoDep) -> SaudeSaida:
    """Responde **sempre 200**, mesmo com a planilha inacessível.

    É o que permite ao frontend diferenciar "backend fora do ar" de "planilha
    com problema" (`SPECS/03` §7.2). Se ainda não há conexão, tenta abrir agora
    — uma única tentativa —, e é isso que faz o botão "Tentar novamente"
    funcionar sem reiniciar o processo (CA-16.2).
    """
    planilha = conexao.conectar()
    if planilha is not None:
        return SaudeSaida(
            status=STATUS_OK,
            planilha=PlanilhaSaida(ok=True, titulo=planilha.titulo),
        )

    erro = conexao.erro
    return SaudeSaida(
        status=STATUS_DEGRADADO,
        planilha=PlanilhaSaida(
            ok=False,
            titulo=None,
            erro=ErroSaida(codigo=erro.codigo, mensagem=erro.mensagem) if erro else None,
        ),
    )
