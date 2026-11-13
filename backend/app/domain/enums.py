"""Enums do domínio (`SPECS/03` §5.5).

O valor de cada membro é o código que vai para a planilha e para o JSON
(MAIÚSCULAS, `SPECS/02` §7); `rotulo`, onde a spec define um, é o texto
exibido ao usuário.
"""

from enum import StrEnum


class TipoLancamento(StrEnum):
    GASTO = "GASTO"
    RECEITA = "RECEITA"

    @property
    def rotulo(self) -> str:
        return _ROTULOS_TIPO[self]


class FormaPagamento(StrEnum):
    """Lista fixa de RN-05 (P-01)."""

    PIX = "PIX"
    CREDITO = "CREDITO"
    DEBITO = "DEBITO"
    DINHEIRO = "DINHEIRO"
    BOLETO = "BOLETO"
    TRANSFERENCIA = "TRANSFERENCIA"

    @property
    def rotulo(self) -> str:
        return _ROTULOS_FORMA[self]


class StatusRecorrencia(StrEnum):
    ATIVA = "ATIVA"
    PAUSADA = "PAUSADA"
    ENCERRADA = "ENCERRADA"

    @property
    def rotulo(self) -> str:
        return _ROTULOS_STATUS[self]


class SituacaoImportacao(StrEnum):
    """Situação de uma linha do livro-razão `Importacoes` (`03` §5.8; F-16)."""

    IMPORTADA = "IMPORTADA"  # criou o lançamento
    CONCILIADA = "CONCILIADA"  # vinculou um lançamento que já existia
    REMOVIDA_NA_ORIGEM = "REMOVIDA_NA_ORIGEM"  # a transação sumiu do banco
    EXCLUIDA = "EXCLUIDA"  # o usuário excluiu o lançamento (RN-22)

    @property
    def vincula(self) -> bool:
        """Só `IMPORTADA` e `CONCILIADA` ligam a transação a um lançamento."""
        return self in (SituacaoImportacao.IMPORTADA, SituacaoImportacao.CONCILIADA)


class SituacaoConexao(StrEnum):
    """Situação de uma conexão (item) do Meu Pluggy (`02` §11.4; F-16)."""

    OK = "OK"
    PARCIAL = "PARCIAL"
    ATUALIZANDO = "ATUALIZANDO"
    DESATUALIZADA = "DESATUALIZADA"
    ERRO_LOGIN = "ERRO_LOGIN"
    AUTORIZACAO_VENCIDA = "AUTORIZACAO_VENCIDA"
    NAO_ENCONTRADA = "NAO_ENCONTRADA"

    @property
    def rotulo(self) -> str:
        return _ROTULOS_CONEXAO[self]

    @property
    def importa(self) -> bool:
        """Conexão que não importa é pulada; as outras seguem (RN-24)."""
        return self not in _CONEXOES_QUE_NAO_IMPORTAM


_ROTULOS_TIPO = {
    TipoLancamento.GASTO: "Gasto",
    TipoLancamento.RECEITA: "Receita",
}

_ROTULOS_FORMA = {
    FormaPagamento.PIX: "Pix",
    FormaPagamento.CREDITO: "Cartão de crédito",
    FormaPagamento.DEBITO: "Cartão de débito",
    FormaPagamento.DINHEIRO: "Dinheiro",
    FormaPagamento.BOLETO: "Boleto",
    FormaPagamento.TRANSFERENCIA: "Transferência",
}

_ROTULOS_STATUS = {
    StatusRecorrencia.ATIVA: "Ativa",
    StatusRecorrencia.PAUSADA: "Pausada",
    StatusRecorrencia.ENCERRADA: "Encerrada",
}

_ROTULOS_CONEXAO = {
    SituacaoConexao.OK: "Atualizada",
    SituacaoConexao.PARCIAL: "Atualizada parcialmente",
    SituacaoConexao.ATUALIZANDO: "Atualização em andamento na Pluggy.",
    SituacaoConexao.DESATUALIZADA: "A última atualização falhou; usando os dados anteriores.",
    SituacaoConexao.ERRO_LOGIN: "O banco recusou o acesso. Renove a autorização no Meu Pluggy.",
    SituacaoConexao.AUTORIZACAO_VENCIDA: "Autorização vencida. Renove no Dashboard da Pluggy.",
    SituacaoConexao.NAO_ENCONTRADA: "Conexão não encontrada. Confira PLUGGY_ITEM_IDS.",
}

_CONEXOES_QUE_NAO_IMPORTAM = frozenset(
    {
        SituacaoConexao.ERRO_LOGIN,
        SituacaoConexao.AUTORIZACAO_VENCIDA,
        SituacaoConexao.NAO_ENCONTRADA,
    }
)
