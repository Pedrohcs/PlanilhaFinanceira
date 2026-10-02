"""`/api/sistema` — ações sobre o próprio app (RN-14; F-14)."""

from fastapi import APIRouter, status

from app.api.deps import CacheDep

router = APIRouter(prefix="/sistema", tags=["sistema"])


@router.post("/recarregar", status_code=status.HTTP_204_NO_CONTENT)
def recarregar(cache: CacheDep) -> None:
    """Esvazia o cache de todas as abas: edições manuais aparecem na próxima leitura.

    Não fala com o Google (F-14 §3.3.1), então responde 204 mesmo com a
    planilha inacessível (CA-F14.11).
    """
    cache.invalidar_tudo()
