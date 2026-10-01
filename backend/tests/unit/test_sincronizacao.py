"""Sincronização de recorrências (REQ-10, RN-09..11; `03` §4.4, F-13 §3.2), em memória."""

import threading
import time
from datetime import date, datetime
from decimal import Decimal
from itertools import count
from typing import Any

import pytest

from app.domain.enums import FormaPagamento, StatusRecorrencia, TipoLancamento
from app.domain.erros import NaoEncontrado
from app.domain.modelos import Lancamento, ListagemComAvisos, Recorrencia
from app.repositories.memoria import (
    CategoriaRepositoryMemoria,
    LancamentoRepositoryMemoria,
    RecorrenciaRepositoryMemoria,
)
from app.services.recorrencia_service import RecorrenciaService
from tests.unit.test_recorrencia_service import categoria, entrada, recorrencia

GASTO = TipoLancamento.GASTO
RECEITA = TipoLancamento.RECEITA


class LancamentosContados(LancamentoRepositoryMemoria):
    """Conta as chamadas de escrita (uma única inserção — `02` §5.5)."""

    def __init__(self, itens: list[Lancamento] | None = None) -> None:
        super().__init__(itens)
        self.insercoes = 0

    def inserir(self, itens: list[Lancamento]) -> None:
        self.insercoes += 1
        super().inserir(itens)


class RecorrenciasContadas(RecorrenciaRepositoryMemoria):
    def __init__(self, itens: list[Recorrencia]) -> None:
        super().__init__(itens)
        self.atualizacoes = 0

    def atualizar(self, item: Recorrencia) -> None:
        self.atualizacoes += 1
        super().atualizar(item)


class Cenario:
    def __init__(
        self, *itens: Recorrencia, hoje: datetime, lancamentos: list[Lancamento] | None = None
    ) -> None:
        self.hoje = hoje
        self.categorias = CategoriaRepositoryMemoria(
            [
                categoria("assinaturas", "Assinaturas", GASTO),
                categoria("moradia", "Moradia", GASTO),
                categoria("velha", "Velha", GASTO, ativa=False),
                categoria("salario", "Salário", RECEITA),
            ]
        )
        self.recorrencias = RecorrenciasContadas(list(itens))
        self.lancamentos = LancamentosContados(lancamentos)
        ids = count()
        self.servico = RecorrenciaService(
            self.categorias,
            self.recorrencias,
            self.lancamentos,
            relogio=lambda: self.hoje,
            novo_id=lambda: f"l{next(ids)}",
        )

    def gerados(self, recorrencia_id: str = "r") -> list[Lancamento]:
        itens = self.lancamentos.listar().itens
        return sorted(
            (item for item in itens if item.recorrencia_id == recorrencia_id),
            key=lambda item: item.data,
        )

    def datas(self, recorrencia_id: str = "r") -> list[date]:
        return [item.data for item in self.gerados(recorrencia_id)]

    def marca(self, recorrencia_id: str = "r") -> str | None:
        return self.recorrencias.obter(recorrencia_id).ultimo_mes_gerado


def test_gera_desde_o_inicio__CA_10_1() -> None:
    """CA-F13.9, bordas 3 e 8: julho a outubro, inclusive 10/10 com hoje em 01/10 (Q2)."""
    hoje = datetime(2026, 10, 1, 8, 0)
    cenario = Cenario(recorrencia(id="r", mes_inicio="2026-07", dia_do_mes=10), hoje=hoje)

    resultado = cenario.servico.sincronizar()

    assert cenario.datas() == [
        date(2026, 7, 10),
        date(2026, 8, 10),
        date(2026, 9, 10),
        date(2026, 10, 10),
    ]
    primeiro = cenario.gerados()[0]
    assert (primeiro.tipo, primeiro.descricao, primeiro.valor) == (
        GASTO,
        "Streaming",
        Decimal("39.90"),
    )
    assert (primeiro.categoria_id, primeiro.forma_pagamento, primeiro.observacao) == (
        "assinaturas",
        FormaPagamento.CREDITO,
        None,
    )
    assert primeiro.criado_em == primeiro.atualizado_em == hoje
    assert cenario.lancamentos.insercoes == 1  # uma única chamada
    assert cenario.marca() == "2026-10"
    assert cenario.recorrencias.obter("r").atualizado_em == hoje
    assert resultado.lancamentos_gerados == 4
    assert [(d.recorrencia_id, d.meses) for d in resultado.detalhes] == [
        ("r", ["2026-07", "2026-08", "2026-09", "2026-10"])
    ]


def test_idempotente__CA_10_2() -> None:
    """CA-F13.10, borda 4: repetir no mesmo mês não gera nem escreve nada."""
    cenario = Cenario(recorrencia(id="r", mes_inicio="2026-07"), hoje=datetime(2026, 9, 2))
    cenario.servico.sincronizar()
    insercoes, atualizacoes = cenario.lancamentos.insercoes, cenario.recorrencias.atualizacoes

    for _ in range(4):
        resultado = cenario.servico.sincronizar()
        assert (resultado.lancamentos_gerados, resultado.detalhes) == (0, [])

    assert len(cenario.gerados()) == 3
    assert cenario.lancamentos.insercoes == insercoes
    assert cenario.recorrencias.atualizacoes == atualizacoes


def test_excluido_nao_volta__CA_10_3__RN_10() -> None:
    """CA-F13.11, borda 5: o mês excluído está atrás da marca d'água."""
    cenario = Cenario(recorrencia(id="r", mes_inicio="2026-07"), hoje=datetime(2026, 9, 2))
    cenario.servico.sincronizar()
    agosto = next(item for item in cenario.gerados() if item.data.month == 8)

    cenario.lancamentos.remover([agosto.id])
    resultado = cenario.servico.sincronizar()

    assert resultado.lancamentos_gerados == 0
    assert [item.data.month for item in cenario.gerados()] == [7, 9]


def test_nunca_mes_futuro__CA_10_4() -> None:
    """CA-F13.12, bordas 6–7: início futuro não gera; `mes_fim` limita; nada depois do corrente."""
    cenario = Cenario(
        recorrencia(id="futura", mes_inicio="2026-11"),
        recorrencia(
            id="terminada", mes_inicio="2026-01", mes_fim="2026-08", ultimo_mes_gerado="2026-08"
        ),
        recorrencia(
            id="termina", mes_inicio="2026-01", mes_fim="2026-08", ultimo_mes_gerado="2026-06"
        ),
        recorrencia(id="sem-fim", mes_inicio="2026-09"),
        hoje=datetime(2026, 9, 30, 23, 59),
    )

    resultado = cenario.servico.sincronizar()

    assert cenario.gerados("futura") == []
    assert cenario.marca("futura") is None
    assert cenario.gerados("terminada") == []
    assert [item.data.month for item in cenario.gerados("termina")] == [7, 8]
    assert cenario.marca("termina") == "2026-08"
    assert [item.data.month for item in cenario.gerados("sem-fim")] == [9]
    todos = cenario.lancamentos.listar().itens
    assert max(item.data for item in todos) <= date(2026, 9, 30)
    assert resultado.lancamentos_gerados == 3


@pytest.mark.parametrize(
    ("hoje", "mes_inicio", "datas"),
    [
        (
            datetime(2027, 4, 15),
            "2027-01",
            [date(2027, 1, 31), date(2027, 2, 28), date(2027, 3, 31), date(2027, 4, 30)],
        ),
        (datetime(2028, 2, 10), "2028-02", [date(2028, 2, 29)]),
    ],
)
def test_dia_31__RN_09(hoje: datetime, mes_inicio: str, datas: list[date]) -> None:
    """CA-F13.13, bordas 1–2: dia que não existe no mês vira o último dia."""
    cenario = Cenario(recorrencia(id="r", mes_inicio=mes_inicio, dia_do_mes=31), hoje=hoje)

    cenario.servico.sincronizar()

    assert cenario.datas() == datas


def test_pausada_e_encerrada_nao_geram__RN_11() -> None:
    """CA-F13.14: só ATIVA gera; as outras ficam como estão."""
    cenario = Cenario(
        recorrencia(id="p", status=StatusRecorrencia.PAUSADA, ultimo_mes_gerado="2026-05"),
        recorrencia(id="e", status=StatusRecorrencia.ENCERRADA, ultimo_mes_gerado="2026-05"),
        hoje=datetime(2026, 9, 2),
    )

    resultado = cenario.servico.sincronizar()

    assert resultado.lancamentos_gerados == 0
    assert cenario.lancamentos.listar().itens == []
    assert (cenario.marca("p"), cenario.marca("e")) == ("2026-05", "2026-05")
    assert cenario.recorrencias.atualizacoes == 0


def test_edicao_vale_para_proximos__CA_09_2() -> None:
    """CA-F13.15, borda 13: julho/agosto como estavam; setembro com os dados novos."""
    cenario = Cenario(recorrencia(id="r", mes_inicio="2026-07"), hoje=datetime(2026, 8, 20))
    cenario.servico.sincronizar()

    cenario.hoje = datetime(2026, 9, 1)
    cenario.servico.editar(
        "r", **entrada(descricao="Streaming família", valor=Decimal("44.90"), dia_do_mes=5)
    )
    cenario.servico.sincronizar()

    assert [(item.data, item.descricao, item.valor) for item in cenario.gerados()] == [
        (date(2026, 7, 10), "Streaming", Decimal("39.90")),
        (date(2026, 8, 10), "Streaming", Decimal("39.90")),
        (date(2026, 9, 5), "Streaming família", Decimal("44.90")),
    ]


def test_categoria_inativa_ou_apagada_gera__CA_F13_16() -> None:
    """Q1, bordas 15–16: desativar a categoria não para a recorrência."""
    cenario = Cenario(
        recorrencia(id="inativa", categoria_id="velha", mes_inicio="2026-09"),
        recorrencia(id="apagada", categoria_id="sumiu", mes_inicio="2026-09"),
        hoje=datetime(2026, 9, 2),
    )

    cenario.servico.sincronizar()

    assert [item.categoria_id for item in cenario.gerados("inativa")] == ["velha"]
    assert [item.categoria_id for item in cenario.gerados("apagada")] == ["sumiu"]


def test_receita_sem_forma__RN_05() -> None:
    """Borda 21: receita gerada sem forma de pagamento."""
    cenario = Cenario(
        recorrencia(
            id="r", tipo=RECEITA, categoria_id="salario", forma_pagamento=None, mes_inicio="2026-09"
        ),
        hoje=datetime(2026, 9, 2),
    )

    cenario.servico.sincronizar()

    assert [(item.tipo, item.forma_pagamento) for item in cenario.gerados()] == [(RECEITA, None)]


def test_pula_mes_ja_gerado__CA_F13_17() -> None:
    """Bordas 17–18: falha parcial anterior (agosto gravado, marca em julho)."""
    agosto = Lancamento(
        id="antigo",
        data=date(2026, 8, 10),
        tipo=GASTO,
        descricao="Streaming",
        valor=Decimal("39.90"),
        categoria_id="assinaturas",
        forma_pagamento=FormaPagamento.CREDITO,
        recorrencia_id="r",
        criado_em=datetime(2026, 8, 1),
        atualizado_em=datetime(2026, 8, 1),
    )
    cenario = Cenario(
        recorrencia(id="r", ultimo_mes_gerado="2026-07"),
        hoje=datetime(2026, 9, 2),
        lancamentos=[agosto],
    )

    resultado = cenario.servico.sincronizar()

    assert [item.id for item in cenario.gerados()] == ["antigo", "l0"]
    assert cenario.datas() == [date(2026, 8, 10), date(2026, 9, 10)]
    assert cenario.marca() == "2026-09"
    assert [(d.recorrencia_id, d.meses) for d in resultado.detalhes] == [("r", ["2026-09"])]


def test_so_mes_ja_gerado_avanca_a_marca_sem_inserir() -> None:
    """Se todos os meses devidos já existem, nada é inserido, mas a marca d'água avança."""
    setembro = Lancamento(
        id="antigo",
        data=date(2026, 9, 10),
        tipo=GASTO,
        descricao="Streaming",
        valor=Decimal("39.90"),
        categoria_id="assinaturas",
        forma_pagamento=FormaPagamento.CREDITO,
        recorrencia_id="r",
        criado_em=datetime(2026, 9, 1),
        atualizado_em=datetime(2026, 9, 1),
    )
    cenario = Cenario(
        recorrencia(id="r", ultimo_mes_gerado="2026-08"),
        hoje=datetime(2026, 9, 2),
        lancamentos=[setembro],
    )

    resultado = cenario.servico.sincronizar()

    assert (resultado.lancamentos_gerados, resultado.detalhes) == (0, [])
    assert cenario.lancamentos.insercoes == 0
    assert cenario.marca() == "2026-09"


def test_recorrencia_apagada_durante_sincronizacao() -> None:
    """F-13 §3.2.6: os lançamentos gravados ficam e as demais recorrências seguem."""

    class SomeNaAtualizacao(RecorrenciasContadas):
        def atualizar(self, item: Recorrencia) -> None:
            if item.id == "some":
                raise NaoEncontrado("sumiu")
            super().atualizar(item)

    cenario = Cenario(hoje=datetime(2026, 9, 2))
    cenario.recorrencias = SomeNaAtualizacao(
        [recorrencia(id="some", mes_inicio="2026-09"), recorrencia(id="fica", mes_inicio="2026-09")]
    )
    cenario.servico = RecorrenciaService(
        cenario.categorias, cenario.recorrencias, cenario.lancamentos, relogio=lambda: cenario.hoje
    )

    resultado = cenario.servico.sincronizar()

    assert resultado.lancamentos_gerados == 2
    assert cenario.marca("fica") == "2026-09"
    assert len(cenario.gerados("some")) == 1


def test_trava_sincronizacoes_simultaneas__CA_F13_18() -> None:
    """Borda 19: duas sincronizações ao mesmo tempo (leitura lenta) geram uma vez só."""

    class LeituraLenta(LancamentoRepositoryMemoria):
        def listar(self) -> ListagemComAvisos[Lancamento]:
            leitura = super().listar()
            # Sem a trava, as duas leem os lançamentos antes de qualquer escrita, e
            # nem a defesa de F-13 §3.2.5 evita a duplicação.
            time.sleep(0.05)
            return leitura

    hoje = datetime(2026, 9, 2)
    recorrencias = RecorrenciaRepositoryMemoria([recorrencia(id="r", mes_inicio="2026-07")])
    lancamentos = LeituraLenta()
    categorias = CategoriaRepositoryMemoria([categoria("assinaturas", "Assinaturas", GASTO)])
    ids = count()
    resultados: list[Any] = []

    def sincronizar() -> None:
        servico = RecorrenciaService(  # um serviço por requisição, como na API
            categorias,
            recorrencias,
            lancamentos,
            relogio=lambda: hoje,
            novo_id=lambda: f"l{next(ids)}",
        )
        resultados.append(servico.sincronizar())

    tarefas = [threading.Thread(target=sincronizar) for _ in range(2)]
    for tarefa in tarefas:
        tarefa.start()
    for tarefa in tarefas:
        tarefa.join()

    assert len(lancamentos.listar().itens) == 3
    assert sorted(item.lancamentos_gerados for item in resultados) == [0, 3]


def test_edicao_espera_a_sincronizacao__CA_F13_18() -> None:
    """F-13 §3.2.1: a sincronização não grava por cima de uma edição feita no meio dela."""

    class LeituraLenta(LancamentoRepositoryMemoria):
        def listar(self) -> ListagemComAvisos[Lancamento]:
            leitura = super().listar()
            time.sleep(0.05)
            return leitura

    hoje = datetime(2026, 9, 2)
    recorrencias = RecorrenciaRepositoryMemoria([recorrencia(id="r", mes_inicio="2026-09")])
    categorias = CategoriaRepositoryMemoria([categoria("assinaturas", "Assinaturas", GASTO)])
    servico = RecorrenciaService(categorias, recorrencias, LeituraLenta(), relogio=lambda: hoje)

    sincronizacao = threading.Thread(target=servico.sincronizar)
    sincronizacao.start()
    time.sleep(0.01)  # a sincronização já leu a recorrência e está lendo os lançamentos
    servico.editar("r", **entrada(mes_inicio="2026-09", valor=Decimal("44.90")))
    sincronizacao.join()

    gravada = recorrencias.obter("r")
    assert (gravada.valor, gravada.ultimo_mes_gerado) == (Decimal("44.90"), "2026-09")
