"""Modelos de domínio: serialização e linha válida (`SPECS/03` §5; F-03 §3.1, §3.2)."""

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from app.api.erros import status_de
from app.domain.enums import FormaPagamento, StatusRecorrencia, TipoLancamento
from app.domain.erros import ErroDominio, ErroValidacao, NaoEncontrado
from app.domain.modelos import (
    Cartao,
    Categoria,
    Importacao,
    Lancamento,
    ListagemComAvisos,
    Recorrencia,
)


def dados_lancamento(**alteracoes: Any) -> dict[str, Any]:
    dados: dict[str, Any] = {
        "id": "9f1c2e",
        "data": "2026-09-29",
        "tipo": "GASTO",
        "descricao": "Almoço",
        "valor": 42.5,
        "categoria_id": "alimentacao",
        "forma_pagamento": "PIX",
        "criado_em": "2026-09-29T10:15:00",
        "atualizado_em": "2026-09-29T10:15:00",
    }
    dados.update(alteracoes)
    return dados


def dados_recorrencia(**alteracoes: Any) -> dict[str, Any]:
    dados: dict[str, Any] = {
        "id": "c02d",
        "tipo": "GASTO",
        "descricao": "Streaming",
        "valor": "39.90",
        "categoria_id": "assinaturas",
        "forma_pagamento": "CREDITO",
        "dia_do_mes": 10,
        "mes_inicio": "2026-07",
        "status": "ATIVA",
        "criado_em": "2026-07-01T08:00:00",
        "atualizado_em": "2026-07-01T08:00:00",
    }
    dados.update(alteracoes)
    return dados


def test_json_com_valor_numerico_e_enum_maiusculo__CA_F03_8() -> None:
    lancamento = Lancamento.model_validate(dados_lancamento())

    corpo = json.loads(lancamento.model_dump_json())

    assert corpo["valor"] == 42.5
    assert isinstance(corpo["valor"], float)
    assert corpo["data"] == "2026-09-29"
    assert corpo["tipo"] == "GASTO"
    assert corpo["forma_pagamento"] == "PIX"
    assert corpo["criado_em"] == "2026-09-29T10:15:00"
    assert corpo["parcelamento_id"] is None


def test_lancamento_guarda_tipos_de_dominio() -> None:
    lancamento = Lancamento.model_validate(dados_lancamento())

    assert lancamento.data == date(2026, 9, 29)
    assert lancamento.valor == Decimal("42.50")
    assert isinstance(lancamento.valor, Decimal)
    assert lancamento.tipo is TipoLancamento.GASTO
    assert lancamento.forma_pagamento is FormaPagamento.PIX


def test_data_hora_perde_microssegundos_e_recusa_fuso() -> None:
    """F-03 §3.2.6: local, sem fuso, ISO com segundos."""
    lancamento = Lancamento.model_validate(
        dados_lancamento(criado_em=datetime(2026, 9, 29, 10, 15, 0, 123456))
    )
    assert lancamento.criado_em == datetime(2026, 9, 29, 10, 15, 0)

    with pytest.raises(ValidationError, match="sem fuso"):
        Lancamento.model_validate(dados_lancamento(criado_em="2026-09-29T10:15:00Z"))


@pytest.mark.parametrize(
    "data_invalida",
    [46294, 46294.0, "29/09/2026", "2026-9-29", "2026-02-30", datetime(2026, 9, 29)],
)
def test_data_so_aceita_texto_iso__CA_16_3(data_invalida: Any) -> None:
    """Data digitada à mão (número serial, formato brasileiro) não é linha válida."""
    with pytest.raises(ValidationError):
        Lancamento.model_validate(dados_lancamento(data=data_invalida))


def test_gasto_exige_forma_de_pagamento__RN_05() -> None:
    """Borda 15."""
    with pytest.raises(ValidationError, match="forma_pagamento é obrigatória para gasto"):
        Lancamento.model_validate(dados_lancamento(forma_pagamento=None))
    with pytest.raises(ValidationError, match="forma_pagamento é obrigatória para gasto"):
        Recorrencia.model_validate(dados_recorrencia(forma_pagamento=None))


def test_receita_sem_forma_e_valida__RN_05() -> None:
    """Borda 16."""
    receita = Lancamento.model_validate(
        dados_lancamento(tipo="RECEITA", categoria_id="salario", forma_pagamento=None)
    )
    recorrencia = Recorrencia.model_validate(
        dados_recorrencia(tipo="RECEITA", categoria_id="salario", forma_pagamento=None)
    )

    assert receita.forma_pagamento is None
    assert recorrencia.forma_pagamento is None


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("id", ""),
        ("tipo", "gasto"),
        ("tipo", "DESPESA"),
        ("forma_pagamento", "CARTAO"),
        ("valor", 0),
        ("valor", -5),
        ("valor", "abc"),
        ("valor", "1.005"),
        ("descricao", ""),
        ("descricao", "x" * 101),
        ("observacao", "x" * 501),
        ("categoria_id", "Alimentação"),
        ("categoria_id", ""),
    ],
)
def test_lancamento_recusa_campo_invalido__RN_01_RN_06(campo: str, valor: Any) -> None:
    with pytest.raises(ValidationError):
        Lancamento.model_validate(dados_lancamento(**{campo: valor}))


def test_lancamento_aceita_limites_de_texto__RN_06() -> None:
    lancamento = Lancamento.model_validate(
        dados_lancamento(descricao="x" * 100, observacao="y" * 500)
    )

    assert len(lancamento.descricao) == 100
    assert lancamento.observacao is not None
    assert len(lancamento.observacao) == 500


def test_parcela_completa_e_valida__RN_08() -> None:
    parcela = Lancamento.model_validate(
        dados_lancamento(parcelamento_id="a71b", parcela_numero=3, parcela_total=10)
    )

    assert (parcela.parcela_numero, parcela.parcela_total) == (3, 10)


@pytest.mark.parametrize(
    "parcela",
    [
        {"parcelamento_id": "a71b"},
        {"parcelamento_id": "a71b", "parcela_numero": 1},
        {"parcela_numero": 1},
        {"parcela_total": 3},
        {"parcelamento_id": "a71b", "parcela_numero": 0, "parcela_total": 3},
        {"parcela_numero": 4, "parcela_total": 3},
        {"parcela_numero": 1, "parcela_total": 49},
        {"parcelamento_id": "a71b", "parcela_numero": 4, "parcela_total": 3},
        {"parcelamento_id": "a71b", "parcela_numero": 1, "parcela_total": 1},
        {"parcelamento_id": "a71b", "parcela_numero": 1, "parcela_total": 49},
        {"parcelamento_id": "", "parcela_numero": 1, "parcela_total": 3},
    ],
)
def test_parcela_incompleta_ou_fora_da_faixa_e_invalida__RN_07(parcela: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Lancamento.model_validate(dados_lancamento(**parcela))


def test_parcela_importada_sem_parcelamento__RN_08() -> None:
    """CA-08.3: "k/N" sem `parcelamento_id` — o banco não diz quais parcelas são da mesma compra."""
    parcela = Lancamento.model_validate(dados_lancamento(parcela_numero=3, parcela_total=10))

    assert parcela.parcelamento_id is None
    assert (parcela.parcela_numero, parcela.parcela_total) == (3, 10)


def test_modelo_e_imutavel_e_recusa_campo_extra() -> None:
    lancamento = Lancamento.model_validate(dados_lancamento())

    with pytest.raises(ValidationError):
        lancamento.valor = Decimal("1.00")  # type: ignore[misc]
    with pytest.raises(ValidationError):
        Lancamento.model_validate(dados_lancamento(categoria_nome="Alimentação"))


def test_categoria_valida_slug_e_cor() -> None:
    categoria = Categoria.model_validate(
        {
            "id": "contas-da-casa",
            "nome": "Contas da casa",
            "tipo": "GASTO",
            "cor": "#4FC3F7",
            "ativa": True,
            "criado_em": "2026-09-29T10:15:00",
        }
    )
    assert categoria.tipo is TipoLancamento.GASTO

    for campo, invalido in [
        ("id", "contas da casa"),
        ("id", "-casa"),
        ("cor", "4FC3F7"),
        ("cor", "#4FC3F"),
    ]:
        with pytest.raises(ValidationError):
            Categoria.model_validate({**categoria.model_dump(), campo: invalido})


def test_recorrencia_valida_dia_e_meses__RN_09() -> None:
    recorrencia = Recorrencia.model_validate(
        dados_recorrencia(mes_fim="2027-06", ultimo_mes_gerado="2026-09")
    )
    assert recorrencia.status is StatusRecorrencia.ATIVA
    assert recorrencia.valor == Decimal("39.90")

    invalidos = [
        ("dia_do_mes", 0),
        ("dia_do_mes", 32),
        ("mes_inicio", "2026-13"),
        ("mes_fim", "2027/06"),
        ("ultimo_mes_gerado", "set/2026"),
        ("status", "SUSPENSA"),
    ]
    for campo, invalido in invalidos:
        with pytest.raises(ValidationError):
            Recorrencia.model_validate(dados_recorrencia(**{campo: invalido}))


def test_listagem_com_avisos_leva_itens_e_contagem__CA_16_3() -> None:
    lancamento = Lancamento.model_validate(dados_lancamento())

    listagem = ListagemComAvisos[Lancamento](itens=[lancamento], linhas_ignoradas=2)

    assert listagem.itens == [lancamento]
    assert listagem.linhas_ignoradas == 2
    assert ListagemComAvisos[Lancamento](itens=[]).linhas_ignoradas == 0
    with pytest.raises(ValidationError):
        ListagemComAvisos[Lancamento](itens=[], linhas_ignoradas=-1)


def test_rotulos_das_formas_de_pagamento__RN_05() -> None:
    """Os seis valores de RN-05, com os códigos de `03` §5.5."""
    assert {forma.value: forma.rotulo for forma in FormaPagamento} == {
        "PIX": "Pix",
        "CREDITO": "Cartão de crédito",
        "DEBITO": "Cartão de débito",
        "DINHEIRO": "Dinheiro",
        "BOLETO": "Boleto",
        "TRANSFERENCIA": "Transferência",
    }
    assert TipoLancamento.GASTO.rotulo == "Gasto"
    assert TipoLancamento.RECEITA.rotulo == "Receita"
    assert [status.value for status in StatusRecorrencia] == ["ATIVA", "PAUSADA", "ENCERRADA"]


@pytest.mark.parametrize(
    ("erro", "codigo", "http"),
    [(NaoEncontrado, "NAO_ENCONTRADO", 404), (ErroValidacao, "VALIDACAO", 422)],
)
def test_novos_erros_mapeiam_para_404_e_422(
    erro: type[ErroDominio], codigo: str, http: int
) -> None:
    """`03` §6.2: o código do domínio já tem status no mapa da API."""
    assert erro.codigo == codigo
    assert status_de(erro.codigo) == http
    assert erro().mensagem


# Cartões e livro-razão das importações (F-16; `03` §5.7, §5.8) -------------------


def dados_cartao(**alteracoes: Any) -> dict[str, Any]:
    dados: dict[str, Any] = {
        "id": "acc-123",
        "item_id": "itm-9",
        "banco": "Nubank",
        "nome": "Ultravioleta",
        "final": "1234",
        "ultima_importacao": "2026-11-12T08:01:00",
        "criado_em": "2026-11-12T08:01:00",
        "atualizado_em": "2026-11-12T08:01:00",
    }
    dados.update(alteracoes)
    return dados


def dados_importacao(**alteracoes: Any) -> dict[str, Any]:
    dados: dict[str, Any] = {
        "id": "7a1b",
        "transacao_id": "tx-1",
        "provider_id": "prov-1",
        "cartao_id": "acc-123",
        "lancamento_id": "9f1c2e",
        "situacao": "IMPORTADA",
        "data": "2026-11-11",
        "tipo": "GASTO",
        "valor": 59.9,
        "descricao": "Uber Trip",
        "status_pluggy": "POSTED",
        "criado_em": "2026-11-12T08:01:00",
        "atualizado_em": "2026-11-12T08:01:00",
    }
    dados.update(alteracoes)
    return dados


def test_cartao_valido_e_campos_opcionais() -> None:
    cartao = Cartao.model_validate(dados_cartao())
    novo = Cartao.model_validate(dados_cartao(final=None, ultima_importacao=None))

    assert cartao.ultima_importacao == datetime(2026, 11, 12, 8, 1)
    assert (novo.final, novo.ultima_importacao) == (None, None)  # ainda não importado (RN-23)


@pytest.mark.parametrize("campo", ["id", "item_id", "banco", "nome"])
def test_cartao_exige_identificacao(campo: str) -> None:
    for vazio in ("", None):
        with pytest.raises(ValidationError):
            Cartao.model_validate(dados_cartao(**{campo: vazio}))


def test_importacao_valida_guarda_tipos_de_dominio() -> None:
    linha = Importacao.model_validate(dados_importacao(provider_id=None))

    assert linha.situacao.value == "IMPORTADA"
    assert linha.data == date(2026, 11, 11)
    assert linha.valor == Decimal("59.90")
    assert linha.provider_id is None
    assert json.loads(linha.model_dump_json())["valor"] == 59.9


@pytest.mark.parametrize(
    "alteracao",
    [
        {"transacao_id": ""},
        {"cartao_id": None},
        {"lancamento_id": ""},
        {"situacao": "PENDENTE"},
        {"data": "11/11/2026"},
        {"tipo": "DESPESA"},
        {"valor": 0},
        {"descricao": ""},
        {"descricao": "x" * 101},
        {"status_pluggy": "pending"},
        {"status_pluggy": None},
    ],
)
def test_importacao_invalida(alteracao: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Importacao.model_validate(dados_importacao(**alteracao))
