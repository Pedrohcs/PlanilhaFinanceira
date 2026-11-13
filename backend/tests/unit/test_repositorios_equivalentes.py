"""Planilha e memória com o mesmo comportamento observável (CA-F03.23).

Os testes de serviço de M1 usam o repositório em memória (`SPECS/02` §8): se
os dois divergissem, a suíte ficaria verde e o app quebraria. O mesmo roteiro
roda nos dois, para as cinco entidades, e os resultados são comparados.
"""

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pytest
from pydantic import BaseModel

from app.domain.enums import (
    FormaPagamento,
    SituacaoImportacao,
    StatusRecorrencia,
    TipoLancamento,
)
from app.domain.erros import NaoEncontrado
from app.domain.modelos import Cartao, Categoria, Importacao, Lancamento, Recorrencia
from app.infra.bootstrap import preparar_planilha
from app.infra.cache import CacheAbas
from app.repositories.base import Repositorio
from app.repositories.memoria import (
    CartaoRepositoryMemoria,
    CategoriaRepositoryMemoria,
    ImportacaoRepositoryMemoria,
    LancamentoRepositoryMemoria,
    RecorrenciaRepositoryMemoria,
)
from app.repositories.planilha import (
    CartaoRepositoryPlanilha,
    CategoriaRepositoryPlanilha,
    ImportacaoRepositoryPlanilha,
    LancamentoRepositoryPlanilha,
    RecorrenciaRepositoryPlanilha,
)
from tests.planilha_falsa import FonteFalsa, PlanilhaFalsa

CRIADO = datetime(2026, 9, 29, 10, 15)


def fazer_lancamento(id_: str, descricao: str) -> Lancamento:
    return Lancamento(
        id=id_, data=date(2026, 1, 31), tipo=TipoLancamento.GASTO, descricao=descricao,
        valor=Decimal("33.34"), categoria_id="moradia", forma_pagamento=FormaPagamento.CREDITO,
        observacao="=SOMA(A1:A2)", parcelamento_id="p1", parcela_numero=1, parcela_total=3,
        criado_em=CRIADO, atualizado_em=CRIADO,
    )  # fmt: skip


def fazer_categoria(id_: str, descricao: str) -> Categoria:
    return Categoria(
        id=id_, nome=descricao, tipo=TipoLancamento.RECEITA, cor="#66BB6A", ativa=True,
        criado_em=CRIADO,
    )  # fmt: skip


def fazer_recorrencia(id_: str, descricao: str) -> Recorrencia:
    return Recorrencia(
        id=id_, tipo=TipoLancamento.GASTO, descricao=descricao, valor=Decimal("39.90"),
        categoria_id="assinaturas", forma_pagamento=FormaPagamento.CREDITO, dia_do_mes=31,
        mes_inicio="2026-07", status=StatusRecorrencia.ATIVA, criado_em=CRIADO,
        atualizado_em=CRIADO,
    )  # fmt: skip


def fazer_cartao(id_: str, descricao: str) -> Cartao:
    return Cartao(
        id=id_, item_id="itm-9", banco="Nubank", nome=descricao, final="0123",
        criado_em=CRIADO, atualizado_em=CRIADO,
    )  # fmt: skip


def fazer_importacao(id_: str, descricao: str) -> Importacao:
    return Importacao(
        id=id_, transacao_id=f"tx-{id_}", cartao_id="acc-123", lancamento_id=f"l-{id_}",
        situacao=SituacaoImportacao.CONCILIADA, data=date(2026, 11, 11),
        tipo=TipoLancamento.RECEITA, valor=Decimal("59.90"), descricao=descricao,
        status_pluggy="PENDING", criado_em=CRIADO, atualizado_em=CRIADO,
    )  # fmt: skip


Fabrica = Callable[[str, str], BaseModel]

ENTIDADES: list[tuple[str, Fabrica, type, type]] = [
    ("Lancamentos", fazer_lancamento, LancamentoRepositoryPlanilha, LancamentoRepositoryMemoria),
    ("Categorias", fazer_categoria, CategoriaRepositoryPlanilha, CategoriaRepositoryMemoria),
    (
        "Recorrencias",
        fazer_recorrencia,
        RecorrenciaRepositoryPlanilha,
        RecorrenciaRepositoryMemoria,
    ),
    ("Cartoes", fazer_cartao, CartaoRepositoryPlanilha, CartaoRepositoryMemoria),
    ("Importacoes", fazer_importacao, ImportacaoRepositoryPlanilha, ImportacaoRepositoryMemoria),
]


def roteiro(repositorio: Repositorio[Any], fazer: Fabrica) -> list[Any]:
    """Operações e erros em sequência; devolve tudo o que é observável."""
    observado: list[Any] = []

    def registrar(acao: Callable[[], Any]) -> None:
        try:
            resultado = acao()
        except NaoEncontrado as erro:
            observado.append(("NaoEncontrado", erro.codigo))
        else:
            observado.append(resultado)

    def estado() -> Any:
        listagem = repositorio.listar()
        return ([item.model_dump() for item in listagem.itens], listagem.linhas_ignoradas)

    registrar(estado)
    registrar(lambda: repositorio.inserir([fazer("a", "Primeiro"), fazer("b", "Segundo")]))
    registrar(lambda: repositorio.inserir([fazer("c", "Terceiro")]))
    registrar(lambda: repositorio.inserir([]))
    registrar(estado)
    registrar(lambda: repositorio.obter("b").model_dump())
    registrar(lambda: repositorio.obter("nao-existe"))
    registrar(lambda: repositorio.atualizar(fazer("b", "Segundo alterado")))
    registrar(lambda: repositorio.atualizar(fazer("nao-existe", "x")))
    registrar(estado)
    # `atualizar_varios` (F-16): tudo ou nada, e lista vazia não faz nada.
    registrar(lambda: repositorio.atualizar_varios([fazer("c", "C em lote"), fazer("a", "A")]))
    registrar(estado)
    registrar(lambda: repositorio.atualizar_varios([fazer("a", "x"), fazer("nao-existe", "y")]))
    registrar(lambda: repositorio.atualizar_varios([]))
    registrar(estado)
    registrar(lambda: repositorio.remover(["a", "nao-existe"]))
    registrar(estado)
    registrar(lambda: repositorio.remover(["c", "a"]))
    registrar(lambda: repositorio.remover([]))
    registrar(estado)
    return observado


@pytest.mark.parametrize(
    ("aba", "fazer", "classe_planilha", "classe_memoria"), ENTIDADES, ids=[e[0] for e in ENTIDADES]
)
def test_mesmo_comportamento_nos_dois_repositorios__CA_F03_23(
    aba: str, fazer: Fabrica, classe_planilha: type, classe_memoria: type
) -> None:
    planilha = PlanilhaFalsa()
    preparar_planilha(planilha)
    if aba == "Categorias":  # o seed de RN-15 não faz parte do roteiro
        planilha.worksheet("Categorias").valores[1:] = []

    na_planilha = roteiro(classe_planilha(FonteFalsa(planilha), CacheAbas(30)), fazer)
    na_memoria = roteiro(classe_memoria(), fazer)

    assert na_planilha == na_memoria
    assert na_planilha[-1] == ([fazer("b", "Segundo alterado").model_dump()], 0)
