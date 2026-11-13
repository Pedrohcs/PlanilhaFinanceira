"""O que o app lê do Meu Pluggy (`SPECS/02` §11.3–11.4; F-16).

Tipos trocados entre o cliente da Pluggy (`infra/pluggy_client.py`) e a
importação (`services/importacao_service.py`). Ficam no domínio porque `infra`
e `services` não se importam (`SPECS/03` §4.2). São leituras já interpretadas —
nada aqui conhece HTTP nem JSON.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain.enums import SituacaoConexao


@dataclass(frozen=True)
class ConexaoPluggy:
    """Situação de uma conexão (item), já pela tabela de `02` §11.4."""

    item_id: str
    situacao: SituacaoConexao
    banco: str | None = None  # `connector.name`; `None` quando a conexão não foi encontrada
    ultima_atualizacao: datetime | None = None  # `lastUpdatedAt` em UTC−3, sem fuso
    autorizacao_expira_em: date | None = None  # `consentExpiresAt`, dia em UTC−3
    aviso_validade: bool = False  # vence em 30 dias ou menos, ou já venceu (CA-20.1)


@dataclass(frozen=True)
class CartaoPluggy:
    """Conta `CREDIT_CARD` de uma conexão."""

    id: str
    nome: str
    final: str | None = None  # 4 últimos dígitos de `number`


@dataclass(frozen=True)
class TransacaoPluggy:
    """Transação de um cartão, como veio do banco: o mapeamento de RN-17/RN-18 é do serviço."""

    id: str  # pode mudar quando o banco reapresenta a transação
    instante: datetime  # `date`, com fuso (UTC)
    valor: Decimal  # `amount`: > 0 débito no cartão, < 0 crédito
    descricao: str = ""
    provider_id: str | None = None  # id estável do Open Finance
    valor_na_moeda_da_conta: Decimal | None = None  # `amountInAccountCurrency`
    moeda: str | None = None  # `currencyCode`
    tipo_operacao: str | None = None  # `operationType` (ESTORNO, CASHBACK, PAGAMENTO_FATURA…)
    status: str = "POSTED"  # `PENDING` ou `POSTED`
    parcela_numero: int | None = None  # `creditCardMetadata.installmentNumber`
    parcela_total: int | None = None  # `creditCardMetadata.totalInstallments`
