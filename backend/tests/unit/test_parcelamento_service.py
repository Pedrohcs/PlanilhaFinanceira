"""Compras parceladas (REQ-07, REQ-08, RN-07, RN-08; F-12 §3.1–3.2), em memória."""

from datetime import date, datetime
from decimal import Decimal
from itertools import count
from typing import Any

import pytest

from app.domain.enums import FormaPagamento, TipoLancamento
from app.domain.erros import (
    CategoriaInativa,
    CategoriaTipoIncompativel,
    ErroValidacao,
    NaoEncontrado,
)
from app.domain.modelos import Categoria, Lancamento, ListagemComAvisos
from app.repositories.memoria import CategoriaRepositoryMemoria, LancamentoRepositoryMemoria
from app.services.parcelamento_service import ParcelamentoService

AGORA = datetime(2026, 9, 30, 12, 34, 56)
GASTO = TipoLancamento.GASTO
RECEITA = TipoLancamento.RECEITA


def categoria(id_: str, nome: str, tipo: TipoLancamento, *, ativa: bool = True) -> Categoria:
    return Categoria(id=id_, nome=nome, tipo=tipo, cor="#E57373", ativa=ativa, criado_em=AGORA)


def avulso(id_: str) -> Lancamento:
    """Lançamento que não é parcela: nunca pode ser tocado pelo parcelamento."""
    return Lancamento(
        id=id_,
        data=date(2026, 1, 20),
        tipo=GASTO,
        descricao="Avulso",
        valor=Decimal("10.00"),
        categoria_id="mercado",
        forma_pagamento=FormaPagamento.PIX,
        criado_em=AGORA,
        atualizado_em=AGORA,
    )


class Cenario:
    def __init__(self, lancamentos: Any = None) -> None:
        self.categorias = CategoriaRepositoryMemoria(
            [
                categoria("mercado", "Mercado", GASTO),
                categoria("velha", "Velha", GASTO, ativa=False),
                categoria("salario", "Salário", RECEITA),
            ]
        )
        self.lancamentos = lancamentos or LancamentoRepositoryMemoria()
        ids = count()
        self.servico = ParcelamentoService(
            self.categorias,
            self.lancamentos,
            relogio=lambda: AGORA,
            novo_id=lambda: f"id{next(ids)}",
        )

    def criar(self, **alteracoes: Any) -> Any:
        dados: dict[str, Any] = {
            "data": date(2026, 1, 15),
            "descricao": "Geladeira",
            "valor_total": Decimal("1000.00"),
            "parcelas": 3,
            "categoria_id": "mercado",
            "forma_pagamento": FormaPagamento.CREDITO,
            "observacao": "loja do centro",
        }
        dados.update(alteracoes)
        return self.servico.criar(**dados)


def test_criar_mil_em_tres__CA_07_1() -> None:
    """CA-F12.1: N lançamentos comuns ligados pelo `parcelamento_id`, soma exata."""
    cenario = Cenario()

    criado = cenario.criar()

    parcelas = [item.lancamento for item in criado.lancamentos]
    assert criado.parcelamento_id == "id0"
    assert [p.valor for p in parcelas] == [Decimal("333.34"), Decimal("333.33"), Decimal("333.33")]
    assert [p.data for p in parcelas] == [date(2026, 1, 15), date(2026, 2, 15), date(2026, 3, 15)]
    assert sum(p.valor for p in parcelas) == Decimal("1000.00")
    assert [p.id for p in parcelas] == ["id1", "id2", "id3"]
    assert [(p.parcela_numero, p.parcela_total) for p in parcelas] == [(1, 3), (2, 3), (3, 3)]
    for parcela in parcelas:
        assert parcela.parcelamento_id == "id0"
        assert parcela.tipo is GASTO
        assert parcela.descricao == "Geladeira"  # a original, sem "(k/N)" (CA-07.3)
        assert parcela.categoria_id == "mercado"
        assert parcela.forma_pagamento is FormaPagamento.CREDITO
        assert parcela.observacao == "loja do centro"
        assert parcela.recorrencia_id is None
        assert parcela.criado_em == parcela.atualizado_em == AGORA
    assert {(i.categoria_nome, i.categoria_cor) for i in criado.lancamentos} == {
        ("Mercado", "#E57373")
    }
    assert cenario.lancamentos.listar().itens == parcelas


@pytest.mark.parametrize(
    ("compra", "parcelas", "datas"),
    [
        (date(2026, 1, 31), 2, [date(2026, 1, 31), date(2026, 2, 28)]),
        (date(2028, 1, 31), 2, [date(2028, 1, 31), date(2028, 2, 29)]),  # bissexto
        # Sempre a partir da compra: a 3ª volta ao dia 31 (borda 3).
        (date(2026, 1, 31), 3, [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)]),
        (date(2026, 12, 15), 3, [date(2026, 12, 15), date(2027, 1, 15), date(2027, 2, 15)]),
    ],
)
def test_datas_fim_de_mes_e_bissexto__CA_07_2(
    compra: date, parcelas: int, datas: list[date]
) -> None:
    criado = Cenario().criar(data=compra, parcelas=parcelas, valor_total=Decimal("100.00"))

    assert [item.lancamento.data for item in criado.lancamentos] == datas


@pytest.mark.parametrize(
    ("total", "parcelas", "primeira", "demais"),
    [
        ("0.10", 3, "0.04", "0.03"),
        ("100.00", 48, "2.24", "2.08"),  # 100,00 − 47 × 2,08
    ],
)
def test_centavos_na_primeira__RN_07(total: str, parcelas: int, primeira: str, demais: str) -> None:
    criado = Cenario().criar(valor_total=Decimal(total), parcelas=parcelas)

    valores = [item.lancamento.valor for item in criado.lancamentos]
    assert valores == [Decimal(primeira)] + [Decimal(demais)] * (parcelas - 1)
    assert sum(valores) == Decimal(total)


@pytest.mark.parametrize(
    ("parcelas", "total", "campo", "mensagem"),
    [
        (1, "100.00", "parcelas", "Informe de 2 a 48 parcelas."),
        (49, "100.00", "parcelas", "Informe de 2 a 48 parcelas."),
        (10, "0.05", "valor_total", "10 parcelas exigem um valor total de no mínimo R$ 0,10."),
    ],
)
def test_limites_de_parcelas_e_valor_minimo__RN_07(
    parcelas: int, total: str, campo: str, mensagem: str
) -> None:
    """CA-F12.3; checados antes da categoria (aqui, de receita): 422, não 409."""
    cenario = Cenario()

    with pytest.raises(ErroValidacao) as erro:
        cenario.criar(parcelas=parcelas, valor_total=Decimal(total), categoria_id="salario")

    assert erro.value.detalhes == [{"campo": campo, "mensagem": mensagem}]
    assert cenario.lancamentos.listar().itens == []


@pytest.mark.parametrize(
    ("alteracoes", "excecao", "campo"),
    [
        ({"categoria_id": "nao-existe"}, ErroValidacao, "categoria_id"),
        ({"categoria_id": "velha"}, CategoriaInativa, None),
        ({"categoria_id": "salario"}, CategoriaTipoIncompativel, None),
        ({"forma_pagamento": None}, ErroValidacao, "forma_pagamento"),
    ],
)
def test_regras_de_categoria_e_forma__RN_04_RN_05(
    alteracoes: dict[str, Any], excecao: type[Exception], campo: str | None
) -> None:
    """CA-F12.4: mesmas regras e códigos do registro; nada gravado."""
    cenario = Cenario()

    with pytest.raises(excecao) as erro:
        cenario.criar(**alteracoes)

    if campo:
        assert [d["campo"] for d in erro.value.detalhes] == [campo]  # type: ignore[attr-defined]
    assert cenario.lancamentos.listar().itens == []


def test_excluir_restantes_inclusive_editada__CA_08_2() -> None:
    """CA-F12.6, borda 12: uma já excluída, outra editada de mês; o resto intacto."""
    cenario = Cenario(LancamentoRepositoryMemoria([avulso("antes")]))
    alvo = cenario.criar(parcelas=4)
    outro = cenario.criar(descricao="Sofá")
    ids = [item.lancamento.id for item in alvo.lancamentos]
    cenario.lancamentos.remover([ids[1]])  # parcela 2/4 excluída sozinha (F-08)
    editada = cenario.lancamentos.obter(ids[2])
    cenario.lancamentos.atualizar(editada.model_copy(update={"data": date(2026, 9, 1)}))

    cenario.servico.excluir(alvo.parcelamento_id)

    restantes = [item.id for item in cenario.lancamentos.listar().itens]
    assert restantes == ["antes"] + [item.lancamento.id for item in outro.lancamentos]


def test_excluir_inexistente_404__CA_F12_7() -> None:
    """Borda 13: inexistente, ou com todas as parcelas já excluídas uma a uma."""
    cenario = Cenario(LancamentoRepositoryMemoria([avulso("antes")]))
    criado = cenario.criar(parcelas=2)
    cenario.lancamentos.remover([item.lancamento.id for item in criado.lancamentos])

    for parcelamento_id in ("nao-existe", criado.parcelamento_id):
        with pytest.raises(NaoEncontrado, match="^Parcelamento não encontrado.$"):
            cenario.servico.excluir(parcelamento_id)
    assert [item.id for item in cenario.lancamentos.listar().itens] == ["antes"]


class LeituraAntiga(LancamentoRepositoryMemoria):
    """Como o cache de planilha dentro do TTL: a 1ª leitura é a de antes da edição manual."""

    def __init__(self) -> None:
        super().__init__()
        self.antiga: ListagemComAvisos[Lancamento] | None = None
        self.remocoes = 0

    def listar(self) -> ListagemComAvisos[Lancamento]:
        if self.antiga is not None:
            antiga, self.antiga = self.antiga, None  # o `remover` que falha invalida o cache
            return antiga
        return super().listar()

    def remover(self, ids: list[str]) -> None:
        self.remocoes += 1
        super().remover(ids)


def test_excluir_tenta_de_novo_apos_mudanca_manual__CA_F12_8() -> None:
    """Borda 14: parcela apagada à mão depois da última leitura; as restantes somem."""
    repositorio = LeituraAntiga()
    cenario = Cenario(repositorio)
    criado = cenario.criar()
    repositorio.antiga = repositorio.listar()
    repositorio.remover([criado.lancamentos[0].lancamento.id])  # "à mão"
    repositorio.remocoes = 0

    cenario.servico.excluir(criado.parcelamento_id)

    assert repositorio.listar().itens == []
    assert repositorio.remocoes == 2  # a 1ª falhou (tudo ou nada), a 2ª com a aba relida
