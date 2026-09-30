"""`GET /api/formas-pagamento` — a lista fixa de RN-05 (P-01; F-06 §3.6).

Não depende da planilha: responde mesmo com ela inacessível. Os rótulos vêm
do enum do domínio, a única fonte (F-04 §10).
"""

from fastapi import APIRouter

from app.api.schemas import FormaPagamentoSaida
from app.domain.enums import FormaPagamento

router = APIRouter(tags=["formas de pagamento"])


@router.get("/formas-pagamento", response_model=list[FormaPagamentoSaida])
def listar() -> list[FormaPagamentoSaida]:
    """Na ordem de RN-05: Pix, Cartão de crédito, Cartão de débito, Dinheiro, Boleto,
    Transferência."""
    return [FormaPagamentoSaida(codigo=forma, nome=forma.rotulo) for forma in FormaPagamento]
