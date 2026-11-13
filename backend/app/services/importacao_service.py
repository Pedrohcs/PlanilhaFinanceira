"""Importação dos cartões de crédito pelo Meu Pluggy (REQ-17 a REQ-20; F-16).

Por enquanto só o contrato `FontePluggy` (T-037): é por ele que a importação
enxerga a Pluggy, sem conhecer o `httpx` nem o cliente concreto (`SPECS/03`
§4.2). O `importacao_service` em si — algoritmo de `03` §4.4 — entra na T-038.
"""

from datetime import date
from typing import Protocol

from app.domain.pluggy import CartaoPluggy, ConexaoPluggy, TransacaoPluggy


class FontePluggy(Protocol):
    """Leituras da Pluggy que a importação usa (`SPECS/02` §11.3).

    Implementado por `infra/pluggy_client.py` e, nos testes, por um dublê em
    memória. Falhas saem como `PluggyCredenciaisInvalidas` ou `PluggyIndisponivel`.
    """

    def obter_conexao(self, item_id: str) -> ConexaoPluggy:
        """Situação da conexão; inexistente vem como `NAO_ENCONTRADA`, sem exceção."""
        ...

    def listar_cartoes(self, item_id: str) -> list[CartaoPluggy]:
        """Cartões de crédito da conexão."""
        ...

    def listar_transacoes(self, conta_id: str, desde: date) -> list[TransacaoPluggy]:
        """Todas as transações do cartão com data a partir de `desde`, sem data final."""
        ...
