"""Resumo do mês (REQ-12, RN-03, RN-13, RN-16; F-09 §3.1), em memória."""

from datetime import date, datetime
from decimal import Decimal
from itertools import count

import pytest

from app.domain.enums import FormaPagamento, TipoLancamento
from app.domain.modelos import Categoria, Lancamento
from app.repositories.memoria import CategoriaRepositoryMemoria, LancamentoRepositoryMemoria
from app.services.lancamento_service import LancamentoService
from app.services.resumo_service import ResumoService

AGORA = datetime(2026, 9, 30, 12, 0)
GASTO = TipoLancamento.GASTO
RECEITA = TipoLancamento.RECEITA
PIX = FormaPagamento.PIX
CREDITO = FormaPagamento.CREDITO
_ids = count()


def categoria(
    id_: str, nome: str, tipo: TipoLancamento = GASTO, *, ativa: bool = True, cor: str = "#E57373"
) -> Categoria:
    return Categoria(id=id_, nome=nome, tipo=tipo, cor=cor, ativa=ativa, criado_em=AGORA)


def lancamento(
    dia: date,
    valor: str,
    categoria_id: str = "mercado",
    *,
    tipo: TipoLancamento = GASTO,
    forma: FormaPagamento | None = PIX,
    **extras: object,
) -> Lancamento:
    return Lancamento(
        id=f"l{next(_ids)}",
        data=dia,
        tipo=tipo,
        descricao="Compra",
        valor=Decimal(valor),
        categoria_id=categoria_id,
        forma_pagamento=forma if tipo is GASTO else None,
        criado_em=AGORA,
        atualizado_em=AGORA,
        **extras,  # type: ignore[arg-type]
    )


def receita(dia: date, valor: str) -> Lancamento:
    return lancamento(dia, valor, "salario", tipo=RECEITA)


CATEGORIAS = [
    categoria("mercado", "Mercado"),
    categoria("lazer", "Lazer", cor="#FFB74D"),
    categoria("agua", "Água", cor="#4FC3F7"),
    categoria("velha", "Velha", ativa=False),
    categoria("salario", "Salário", RECEITA),
]


def servico(*itens: Lancamento, categorias: list[Categoria] = CATEGORIAS) -> ResumoService:
    return ResumoService(
        CategoriaRepositoryMemoria(categorias), LancamentoRepositoryMemoria(list(itens))
    )


def test_totais_iguais_aos_da_listagem__CA_12_1() -> None:
    """CA-F09.1, borda 1: só setembro conta, com parcela e recorrente; = listagem sem filtro."""
    itens = [
        lancamento(date(2026, 9, 1), "100.00"),
        lancamento(
            date(2026, 9, 30),
            "333.34",
            parcelamento_id="par",
            parcela_numero=1,
            parcela_total=3,
        ),
        lancamento(
            date(2026, 10, 1), "333.33", parcelamento_id="par", parcela_numero=2, parcela_total=3
        ),
        receita(date(2026, 9, 5), "5000.00"),
        lancamento(date(2026, 9, 10), "39.90", recorrencia_id="rec"),
        lancamento(date(2026, 8, 31), "999.99"),
    ]
    categorias = CategoriaRepositoryMemoria(CATEGORIAS)
    lancamentos = LancamentoRepositoryMemoria(itens)

    resumo = ResumoService(categorias, lancamentos).mensal("2026-09")
    lista = LancamentoService(categorias, lancamentos).listar("2026-09")

    assert resumo.totais == lista.totais
    assert resumo.totais.gastos == Decimal("473.24")
    assert resumo.totais.receitas == Decimal("5000.00")
    assert resumo.totais.saldo == Decimal("4526.76")


def test_somas_exatas_em_centavos__RN_16() -> None:
    """CA-F09.2: 0,10 + 0,20 três vezes = 0,90 exato (em float daria 0,9000000000000001)."""
    itens = [lancamento(date(2026, 9, 1), valor) for valor in ["0.10", "0.20"] * 3]

    resumo = servico(*itens).mensal("2026-09")

    assert resumo.totais.gastos == Decimal("0.90")
    assert resumo.gasto_acumulado_diario[-1] == Decimal("0.90")
    assert resumo.por_categoria[0].total == Decimal("0.90")


def test_por_categoria_e_forma_ordenados__CA_F09_3() -> None:
    """Só gastos; maior primeiro; empates: nome sem acento/caixa, forma na ordem de RN-05."""
    resumo = servico(
        lancamento(date(2026, 9, 1), "50.00", "lazer", forma=CREDITO),
        lancamento(date(2026, 9, 2), "30.00", "mercado", forma=PIX),
        lancamento(date(2026, 9, 3), "20.00", "mercado", forma=PIX),
        lancamento(date(2026, 9, 4), "25.00", "agua", forma=CREDITO),
        lancamento(date(2026, 9, 5), "25.00", "agua", forma=FormaPagamento.BOLETO),
        receita(date(2026, 9, 5), "5000.00"),  # não entra nas listas
    ).mensal("2026-09")

    # Água, Lazer e Mercado empatam em 50: "Água" vem antes de "Lazer" ignorando o acento.
    assert [(c.nome, c.total, c.percentual) for c in resumo.por_categoria] == [
        ("Água", Decimal("50.00"), Decimal("33.3")),
        ("Lazer", Decimal("50.00"), Decimal("33.3")),
        ("Mercado", Decimal("50.00"), Decimal("33.3")),
    ]
    assert [
        (f.forma_pagamento, f.nome, f.total, f.percentual) for f in resumo.por_forma_pagamento
    ] == [
        (CREDITO, "Cartão de crédito", Decimal("75.00"), Decimal("50.0")),
        (PIX, "Pix", Decimal("50.00"), Decimal("33.3")),
        (FormaPagamento.BOLETO, "Boleto", Decimal("25.00"), Decimal("16.7")),
    ]
    assert resumo.por_categoria[0].cor == "#4FC3F7"


def test_empate_de_forma_segue_rn_05() -> None:
    resumo = servico(
        lancamento(date(2026, 9, 1), "10.00", forma=FormaPagamento.TRANSFERENCIA),
        lancamento(date(2026, 9, 1), "10.00", forma=FormaPagamento.DEBITO),
        lancamento(date(2026, 9, 1), "10.00", forma=PIX),
    ).mensal("2026-09")

    assert [f.forma_pagamento for f in resumo.por_forma_pagamento] == [
        PIX,
        FormaPagamento.DEBITO,
        FormaPagamento.TRANSFERENCIA,
    ]


@pytest.mark.parametrize(
    ("valores", "percentuais"),
    [
        (["10.00", "10.00", "10.00"], ["33.3", "33.3", "33.3"]),  # soma 99,9 (Q1)
        (["200.00", "100.00"], ["66.7", "33.3"]),  # soma 100,0
        (["100.00"], ["100.0"]),  # borda 5
        (["0.05", "0.01"], ["83.3", "16.7"]),  # 83,33… e 16,66… → meio para cima
    ],
)
def test_percentuais_arredondados__Q1(valores: list[str], percentuais: list[str]) -> None:
    ids = ["mercado", "lazer", "agua"]
    resumo = servico(
        *[lancamento(date(2026, 9, 1), valor, ids[i]) for i, valor in enumerate(valores)]
    ).mensal("2026-09")

    assert [c.percentual for c in resumo.por_categoria] == [Decimal(p) for p in percentuais]


def test_categoria_inativa_renomeada_e_apagada__CA_F09_4() -> None:
    """Bordas 8–10: nome e cor atuais; apagada à mão vira "Categoria não encontrada"."""
    categorias = [
        categoria("mercado", "Supermercado", cor="#123456"),  # renomeada depois
        categoria("velha", "Velha", ativa=False),
    ]
    resumo = servico(
        lancamento(date(2026, 9, 1), "30.00", "mercado"),
        lancamento(date(2026, 9, 1), "20.00", "velha"),
        lancamento(date(2026, 9, 1), "10.00", "sumiu"),
        categorias=categorias,
    ).mensal("2026-09")

    assert [(c.categoria_id, c.nome, c.cor) for c in resumo.por_categoria] == [
        ("mercado", "Supermercado", "#123456"),
        ("velha", "Velha", "#E57373"),
        ("sumiu", "Categoria não encontrada", "#9E9E9E"),
    ]


@pytest.mark.parametrize(
    ("mes", "gastos", "esperado"),
    [
        (
            "2026-09",
            [(1, "10.00"), (15, "5.50"), (30, "4.50")],
            {1: "10.00", 14: "10.00", 15: "15.50", 29: "15.50", 30: "20.00"},
        ),
        ("2028-02", [(29, "1.00")], {28: "0.00", 29: "1.00"}),
    ],
)
def test_acumulado_diario__CA_F09_5(
    mes: str, gastos: list[tuple[int, str]], esperado: dict[int, str]
) -> None:
    """Todos os dias do mês (Q2), cresce nos dias de gasto e fica constante entre eles."""
    ano, numero = (int(parte) for parte in mes.split("-"))
    resumo = servico(
        *[lancamento(date(ano, numero, dia), valor) for dia, valor in gastos],
        receita(date(ano, numero, 2), "1000.00"),  # receita não entra
    ).mensal(mes)

    acumulado = resumo.gasto_acumulado_diario
    assert len(acumulado) == {"2026-09": 30, "2028-02": 29}[mes]
    for dia, total in esperado.items():
        assert acumulado[dia - 1] == Decimal(total)


def test_mes_vazio_e_so_receitas__CA_F09_6() -> None:
    """Borda 3 e mês sem nada: 200 com zeros, listas vazias e acumulado zerado."""
    vazio = servico().mensal("2026-04")
    so_receitas = servico(receita(date(2026, 9, 5), "5000.00")).mensal("2026-09")

    assert vazio.totais.gastos == vazio.totais.receitas == vazio.totais.saldo == Decimal("0.00")
    assert vazio.por_categoria == vazio.por_forma_pagamento == []
    assert vazio.gasto_acumulado_diario == [Decimal("0.00")] * 30
    assert so_receitas.totais.saldo == Decimal("5000.00")
    assert so_receitas.por_categoria == so_receitas.por_forma_pagamento == []
    assert set(so_receitas.gasto_acumulado_diario) == {Decimal("0.00")}
