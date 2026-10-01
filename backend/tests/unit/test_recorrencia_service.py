"""Recorrências: cadastro, edição e status (REQ-09, RN-04..06, RN-09, RN-11; F-13 §3.1)."""

from datetime import date, datetime
from decimal import Decimal
from itertools import count
from typing import Any

import pytest

from app.domain.enums import FormaPagamento, StatusRecorrencia, TipoLancamento
from app.domain.erros import (
    CategoriaInativa,
    CategoriaTipoIncompativel,
    ErroValidacao,
    NaoEncontrado,
)
from app.domain.modelos import Categoria, Lancamento, Recorrencia
from app.repositories.memoria import (
    CategoriaRepositoryMemoria,
    LancamentoRepositoryMemoria,
    RecorrenciaRepositoryMemoria,
)
from app.services.recorrencia_service import RecorrenciaService

CRIADO = datetime(2026, 7, 1, 9, 0)
AGORA = datetime(2026, 9, 15, 10, 30)  # mês corrente: 2026-09
GASTO = TipoLancamento.GASTO
RECEITA = TipoLancamento.RECEITA
ATIVA = StatusRecorrencia.ATIVA
PAUSADA = StatusRecorrencia.PAUSADA
ENCERRADA = StatusRecorrencia.ENCERRADA
_ids = count()


def categoria(id_: str, nome: str, tipo: TipoLancamento, *, ativa: bool = True) -> Categoria:
    return Categoria(id=id_, nome=nome, tipo=tipo, cor="#E57373", ativa=ativa, criado_em=CRIADO)


def recorrencia(**campos: Any) -> Recorrencia:
    dados: dict[str, Any] = {
        "id": f"r{next(_ids)}",
        "tipo": GASTO,
        "descricao": "Streaming",
        "valor": Decimal("39.90"),
        "categoria_id": "assinaturas",
        "forma_pagamento": FormaPagamento.CREDITO,
        "dia_do_mes": 10,
        "mes_inicio": "2026-07",
        "mes_fim": None,
        "status": ATIVA,
        "ultimo_mes_gerado": None,
        "criado_em": CRIADO,
        "atualizado_em": CRIADO,
    }
    dados.update(campos)
    return Recorrencia(**dados)


def entrada(**alteracoes: Any) -> dict[str, Any]:
    dados: dict[str, Any] = {
        "tipo": GASTO,
        "descricao": "Streaming",
        "valor": Decimal("39.90"),
        "categoria_id": "assinaturas",
        "forma_pagamento": FormaPagamento.CREDITO,
        "dia_do_mes": 10,
        "mes_inicio": "2026-07",
        "mes_fim": None,
    }
    dados.update(alteracoes)
    return dados


class Cenario:
    def __init__(self, *itens: Recorrencia, agora: datetime = AGORA) -> None:
        self.categorias = CategoriaRepositoryMemoria(
            [
                categoria("assinaturas", "Assinaturas", GASTO),
                categoria("moradia", "Moradia", GASTO),
                categoria("velha", "Velha", GASTO, ativa=False),
                categoria("outra-velha", "Outra velha", GASTO, ativa=False),
                categoria("salario", "Salário", RECEITA),
            ]
        )
        self.recorrencias = RecorrenciaRepositoryMemoria(list(itens))
        self.servico = RecorrenciaService(
            self.categorias,
            self.recorrencias,
            LancamentoRepositoryMemoria(),
            relogio=lambda: agora,
            novo_id=lambda: "nova",
        )

    def gravada(self, id_: str) -> Recorrencia:
        return self.recorrencias.obter(id_)


def test_criar__CA_F13_1() -> None:
    """Nasce ATIVA, nunca gerada, próximo mês = início; uma linha nova."""
    cenario = Cenario()

    criada = cenario.servico.criar(**entrada())

    assert criada.proximo_mes == "2026-07"
    assert cenario.recorrencias.listar().itens == [criada.recorrencia]
    gravada = cenario.gravada("nova")
    assert (gravada.status, gravada.ultimo_mes_gerado) == (ATIVA, None)
    assert gravada.criado_em == gravada.atualizado_em == AGORA
    assert gravada.valor == Decimal("39.90")


def test_criar_receita_sem_forma_e_inicio_no_passado__RN_05() -> None:
    """Borda 21 e Q6: receita sem forma; `mes_inicio` em 2020 é aceito."""
    cenario = Cenario()

    criada = cenario.servico.criar(
        **entrada(tipo=RECEITA, categoria_id="salario", forma_pagamento=None, mes_inicio="2020-01")
    )

    assert criada.recorrencia.forma_pagamento is None
    assert criada.proximo_mes == "2020-01"


@pytest.mark.parametrize(
    ("alteracoes", "erro", "campo"),
    [
        ({"mes_inicio": "2026-09", "mes_fim": "2026-08"}, ErroValidacao, "mes_fim"),
        ({"categoria_id": "sumiu"}, ErroValidacao, "categoria_id"),
        ({"forma_pagamento": None}, ErroValidacao, "forma_pagamento"),
        ({"categoria_id": "salario"}, CategoriaTipoIncompativel, None),
        ({"categoria_id": "velha"}, CategoriaInativa, None),
    ],
)
def test_validacoes__CA_F13_2(alteracoes: dict[str, Any], erro: type, campo: str | None) -> None:
    """Regras que dependem de outros dados (RN-04, RN-05, F-13 §3.1.2); nada é gravado."""
    cenario = Cenario()

    with pytest.raises(erro) as capturado:
        cenario.servico.criar(**entrada(**alteracoes))

    if campo is not None:
        assert [d["campo"] for d in capturado.value.detalhes] == [campo]
    assert cenario.recorrencias.listar().itens == []


def test_mes_fim_igual_ao_inicio_e_aceito() -> None:
    criada = Cenario().servico.criar(**entrada(mes_inicio="2026-09", mes_fim="2026-09"))

    assert criada.recorrencia.mes_fim == "2026-09"


def test_editar_nao_muda_gerados__CA_09_2() -> None:
    """CA-F13.3, borda 13: dados novos; status, marca d'água e `criado_em` preservados."""
    original = recorrencia(id="r", ultimo_mes_gerado="2026-08")
    cenario = Cenario(original)
    lancamentos = LancamentoRepositoryMemoria(
        [
            Lancamento(
                id="l1",
                data=date(2026, 8, 10),
                tipo=GASTO,
                descricao="Streaming",
                valor=Decimal("39.90"),
                categoria_id="assinaturas",
                forma_pagamento=FormaPagamento.CREDITO,
                recorrencia_id="r",
                criado_em=CRIADO,
                atualizado_em=CRIADO,
            )
        ]
    )
    antes = lancamentos.listar().itens

    editada = cenario.servico.editar(
        "r",
        **entrada(
            descricao="Streaming família",
            valor=Decimal("44.90"),
            categoria_id="moradia",
            dia_do_mes=31,
            forma_pagamento=FormaPagamento.PIX,
        ),
    )

    gravada = cenario.gravada("r")
    assert editada.recorrencia == gravada
    assert (gravada.descricao, gravada.valor, gravada.categoria_id, gravada.dia_do_mes) == (
        "Streaming família",
        Decimal("44.90"),
        "moradia",
        31,
    )
    assert (gravada.status, gravada.ultimo_mes_gerado, gravada.criado_em) == (
        ATIVA,
        "2026-08",
        CRIADO,
    )
    assert gravada.atualizado_em == AGORA
    assert editada.proximo_mes == "2026-09"
    # O serviço de recorrências nem conhece lançamentos: os gerados não mudam.
    assert lancamentos.listar().itens == antes


def test_editar_muda_o_tipo() -> None:
    """Como em F-08: o tipo também muda, com categoria e forma coerentes."""
    cenario = Cenario(recorrencia(id="r"))

    editada = cenario.servico.editar(
        "r", **entrada(tipo=RECEITA, categoria_id="salario", forma_pagamento=None)
    )

    assert (editada.recorrencia.tipo, editada.recorrencia.forma_pagamento) == (RECEITA, None)


def test_editar_categoria_atual_inativa__CA_F13_4() -> None:
    """F-08 Q1: a categoria atual pode estar inativa; trocar para outra inativa, não."""
    cenario = Cenario(recorrencia(id="r", categoria_id="velha"))

    editada = cenario.servico.editar("r", **entrada(categoria_id="velha", valor=Decimal("1.00")))
    assert editada.recorrencia.valor == Decimal("1.00")

    with pytest.raises(CategoriaInativa):
        cenario.servico.editar("r", **entrada(categoria_id="outra-velha"))


def test_editar_inexistente_404_antes_das_regras() -> None:
    with pytest.raises(NaoEncontrado) as erro:
        Cenario().servico.editar("sumiu", **entrada(categoria_id="nao-existe"))

    assert erro.value.mensagem == "Recorrência não encontrada."


def test_editar_encerrada__CA_F13_8() -> None:
    """Q3: encerrada não se edita — 422 no campo `status`."""
    cenario = Cenario(recorrencia(id="r", status=ENCERRADA))

    with pytest.raises(ErroValidacao) as erro:
        cenario.servico.editar("r", **entrada(valor=Decimal("1.00")))

    assert erro.value.detalhes == [
        {"campo": "status", "mensagem": "Recorrência encerrada não pode ser editada."}
    ]
    assert cenario.gravada("r").valor == Decimal("39.90")


@pytest.mark.parametrize(
    ("de", "para", "valida"),
    [
        (ATIVA, PAUSADA, True),
        (PAUSADA, ATIVA, True),
        (ATIVA, ENCERRADA, True),
        (PAUSADA, ENCERRADA, True),
        (ATIVA, ATIVA, False),
        (PAUSADA, PAUSADA, False),
        (ENCERRADA, ENCERRADA, False),
        (ENCERRADA, ATIVA, False),
        (ENCERRADA, PAUSADA, False),
    ],
)
def test_transicoes_de_status__CA_F13_5(
    de: StatusRecorrencia, para: StatusRecorrencia, valida: bool
) -> None:
    """Q3: encerrar é definitivo; mesmo status não é transição."""
    cenario = Cenario(recorrencia(id="r", status=de, ultimo_mes_gerado="2026-09"))

    if valida:
        alterada = cenario.servico.mudar_status("r", para)
        assert cenario.gravada("r").status is para
        assert alterada.recorrencia.atualizado_em == AGORA
        assert alterada.proximo_mes == ("2026-10" if para is ATIVA else None)
    else:
        with pytest.raises(ErroValidacao) as erro:
            cenario.servico.mudar_status("r", para)
        assert erro.value.detalhes == [
            {
                "campo": "status",
                "mensagem": f"Não é possível mudar de {de.rotulo} para {para.rotulo}.",
            }
        ]
        assert cenario.gravada("r").status is de


def test_mudar_status_inexistente_404() -> None:
    with pytest.raises(NaoEncontrado) as erro:
        Cenario().servico.mudar_status("sumiu", PAUSADA)

    assert erro.value.mensagem == "Recorrência não encontrada."


@pytest.mark.parametrize(
    ("ultimo_mes_gerado", "mes_inicio", "ultimo_depois", "proximo"),
    [
        # CA-F13.6, borda 9: pausada em junho (gerou até maio), reativada em setembro.
        ("2026-05", "2026-01", "2026-08", "2026-09"),
        # Borda 10: pausada e reativada no mesmo mês antes de gerá-lo — setembro ainda sai.
        ("2026-08", "2026-01", "2026-08", "2026-09"),
        # Já tinha gerado setembro: a marca d'água não recua.
        ("2026-09", "2026-01", "2026-09", "2026-10"),
        # Borda 11: pausada antes de gerar qualquer mês, início no passado.
        (None, "2026-03", "2026-08", "2026-09"),
        # Início no futuro: reativar não antecipa nada.
        (None, "2026-12", "2026-08", "2026-12"),
    ],
)
def test_reativar_sem_retroativos__RN_11(
    ultimo_mes_gerado: str | None, mes_inicio: str, ultimo_depois: str, proximo: str
) -> None:
    """Marca d'água = max(atual, mês anterior ao corrente) (`03` §4.4)."""
    cenario = Cenario(
        recorrencia(
            id="r", status=PAUSADA, ultimo_mes_gerado=ultimo_mes_gerado, mes_inicio=mes_inicio
        )
    )

    reativada = cenario.servico.mudar_status("r", ATIVA)

    assert cenario.gravada("r").ultimo_mes_gerado == ultimo_depois
    assert reativada.proximo_mes == proximo


def test_pausar_e_encerrar_nao_mexem_na_marca_dagua__RN_11() -> None:
    cenario = Cenario(recorrencia(id="r", ultimo_mes_gerado="2026-08"))

    cenario.servico.mudar_status("r", PAUSADA)
    assert cenario.gravada("r").ultimo_mes_gerado == "2026-08"
    cenario.servico.mudar_status("r", ENCERRADA)
    assert cenario.gravada("r").ultimo_mes_gerado == "2026-08"


def test_listar_ordem_e_proximo_mes__CA_09_1() -> None:
    """CA-F13.7, bordas 6–7: status, depois descrição sem acento/caixa; `proximo_mes`."""
    cenario = Cenario(
        recorrencia(id="enc", descricao="Academia", status=ENCERRADA, ultimo_mes_gerado="2026-03"),
        recorrencia(id="pau", descricao="Água", status=PAUSADA, ultimo_mes_gerado="2026-08"),
        recorrencia(id="nova", descricao="internet", mes_inicio="2026-11"),  # futuro
        recorrencia(id="emdia", descricao="Aluguel", ultimo_mes_gerado="2026-09"),
        recorrencia(id="fim", descricao="Curso", mes_fim="2026-08", ultimo_mes_gerado="2026-08"),
        recorrencia(id="atras", descricao="Streaming", ultimo_mes_gerado="2026-06"),
        recorrencia(id="nunca", descricao="água", mes_inicio="2026-07"),
    )

    lista = cenario.servico.listar()

    assert [(item.recorrencia.id, item.proximo_mes) for item in lista] == [
        ("nunca", "2026-07"),  # "água" antes de "Aluguel" (sem acento/caixa)
        ("emdia", "2026-10"),
        ("fim", None),  # vigência terminou: continua ATIVA (Q4)
        ("nova", "2026-11"),
        ("atras", "2026-07"),
        ("pau", None),
        ("enc", None),
    ]
    assert [item.recorrencia.status for item in lista][2] is ATIVA
