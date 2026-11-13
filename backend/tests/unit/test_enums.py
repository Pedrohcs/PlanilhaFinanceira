"""Enums da importação dos cartões (`SPECS/03` §5.5; `02` §11.4; F-16)."""

from app.domain.enums import SituacaoConexao, SituacaoImportacao


def test_situacao_importacao_codigos_e_vinculo() -> None:
    """Só `IMPORTADA` e `CONCILIADA` ligam a transação a um lançamento (CA-F16.36)."""
    assert [situacao.value for situacao in SituacaoImportacao] == [
        "IMPORTADA",
        "CONCILIADA",
        "REMOVIDA_NA_ORIGEM",
        "EXCLUIDA",
    ]
    assert [situacao for situacao in SituacaoImportacao if situacao.vincula] == [
        SituacaoImportacao.IMPORTADA,
        SituacaoImportacao.CONCILIADA,
    ]


def test_situacao_conexao_rotulos_e_quem_importa__RN_24() -> None:
    """Tabela de `02` §11.4: erro de login, autorização vencida e inexistente são puladas."""
    assert {
        situacao.value: (situacao.rotulo, situacao.importa) for situacao in SituacaoConexao
    } == {
        "OK": ("Atualizada", True),
        "PARCIAL": ("Atualizada parcialmente", True),
        "ATUALIZANDO": ("Atualização em andamento na Pluggy.", True),
        "DESATUALIZADA": ("A última atualização falhou; usando os dados anteriores.", True),
        "ERRO_LOGIN": ("O banco recusou o acesso. Renove a autorização no Meu Pluggy.", False),
        "AUTORIZACAO_VENCIDA": ("Autorização vencida. Renove no Dashboard da Pluggy.", False),
        "NAO_ENCONTRADA": ("Conexão não encontrada. Confira PLUGGY_ITEM_IDS.", False),
    }
