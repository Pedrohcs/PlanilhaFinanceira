"""Resumo do mês e histórico (REQ-12, REQ-14, RN-03, RN-13, RN-16; F-09, F-11), em memória."""

from datetime import date, datetime
from decimal import Decimal
from itertools import count

import pytest

from app.domain.enums import FormaPagamento, TipoLancamento
from app.domain.erros import ErroValidacao
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


# Histórico (F-11 §3.1) ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("hoje", "inicio", "fim"),
    [(date(2026, 10, 1), "2025-11", "2026-10"), (date(2027, 1, 15), "2026-02", "2027-01")],
)
def test_historico_padrao_ultimos_12__CA_14_1(hoje: date, inicio: str, fim: str) -> None:
    """CA-F11.1, borda 1: 12 meses até o corrente, em ordem, os vazios com zero."""
    historico = servico(lancamento(hoje, "10.00")).historico(hoje=hoje)

    assert (historico.inicio, historico.fim) == (inicio, fim)
    assert len(historico.meses) == 12
    assert [m.mes for m in historico.meses] == sorted(m.mes for m in historico.meses)
    assert historico.meses[0].mes == inicio
    assert historico.meses[0].totais.gastos == Decimal("0.00")
    assert historico.meses[-1].totais.gastos == Decimal("10.00")


def test_historico_meses_iguais_ao_mensal__CA_F11_2() -> None:
    """Cada mês com os totais do resumo mensal; nada de fora do período (RN-03, RN-13)."""
    itens = [
        lancamento(date(2026, 7, 31), "40.00"),
        lancamento(
            date(2026, 8, 1), "25.00", parcelamento_id="p", parcela_numero=1, parcela_total=2
        ),
        lancamento(
            date(2026, 9, 1), "25.00", parcelamento_id="p", parcela_numero=2, parcela_total=2
        ),
        lancamento(date(2026, 9, 10), "39.90", "lazer", recorrencia_id="r"),
        receita(date(2026, 9, 5), "100.00"),
        lancamento(date(2026, 10, 1), "999.00"),  # fora do período
    ]
    resumos = servico(*itens)
    historico = resumos.historico("2026-07", "2026-09")

    assert [m.mes for m in historico.meses] == ["2026-07", "2026-08", "2026-09"]
    for item in historico.meses:
        assert item.totais == resumos.mensal(item.mes).totais
    assert historico.meses[2].totais.saldo == Decimal("35.10")
    assert historico.total_gastos_periodo == Decimal("129.90")


def test_historico_somas_exatas__RN_16() -> None:
    """CA-F11.3, borda 3: 0,10 + 0,20 (×3) = 0,90 exato no mês e no período."""
    valores = ["0.10", "0.20"] * 3
    historico = servico(*[lancamento(date(2026, 9, 1), v) for v in valores]).historico(
        "2026-09", "2026-09"
    )

    assert historico.meses[0].totais.gastos == Decimal("0.90")
    assert historico.total_gastos_periodo == Decimal("0.90")
    assert historico.por_categoria[0].valores == [Decimal("0.90")]


def test_historico_por_categoria_alinhado__CA_F11_4() -> None:
    """Só gastos; `valores` alinhados aos meses; ordem por total no período, empate pelo nome."""
    categorias = [
        categoria("mercado", "Supermercado", cor="#123456"),  # renomeada: nome atual (borda 12)
        categoria("lazer", "Lazer", cor="#FFB74D"),
        categoria("agua", "Água", cor="#4FC3F7"),
        categoria("salario", "Salário", RECEITA),
    ]
    historico = servico(
        lancamento(date(2026, 7, 3), "10.00", "mercado"),
        lancamento(date(2026, 9, 3), "40.00", "mercado"),
        lancamento(date(2026, 8, 3), "30.00", "lazer"),
        lancamento(date(2026, 9, 4), "30.00", "agua"),
        receita(date(2026, 8, 5), "5000.00"),
        lancamento(date(2026, 6, 30), "500.00", "lazer"),  # fora do período
        categorias=categorias,
    ).historico("2026-07", "2026-09")

    assert [(c.categoria_id, c.nome, c.cor) for c in historico.por_categoria] == [
        ("mercado", "Supermercado", "#123456"),
        ("agua", "Água", "#4FC3F7"),  # empate com Lazer: "agua" < "lazer"
        ("lazer", "Lazer", "#FFB74D"),
    ]
    assert [c.valores for c in historico.por_categoria] == [
        [Decimal("10.00"), Decimal("0.00"), Decimal("40.00")],
        [Decimal("0.00"), Decimal("0.00"), Decimal("30.00")],
        [Decimal("0.00"), Decimal("30.00"), Decimal("0.00")],
    ]


def test_historico_categoria_inativa_e_apagada__CA_F11_5() -> None:
    """Bordas 13–14: inativa aparece; cada categoria apagada à mão vira um item cinza."""
    historico = servico(
        lancamento(date(2026, 9, 1), "30.00", "velha"),
        lancamento(date(2026, 9, 1), "20.00", "sumiu"),
        lancamento(date(2026, 9, 1), "10.00", "sumiu-2"),
    ).historico("2026-09", "2026-09")

    assert [(c.categoria_id, c.nome, c.cor) for c in historico.por_categoria] == [
        ("velha", "Velha", "#E57373"),
        ("sumiu", "Categoria não encontrada", "#9E9E9E"),
        ("sumiu-2", "Categoria não encontrada", "#9E9E9E"),
    ]


@pytest.mark.parametrize(
    ("inicio", "fim", "itens", "total", "media"),
    [
        # CA-F11.6, borda 9: dois meses sem lançamento entram no divisor (Q3).
        ("2026-07", "2026-09", [(date(2026, 8, 10), "100.00")], "100.00", "33.33"),
        # Borda 4: um mês só, média = total.
        ("2026-09", "2026-09", [(date(2026, 9, 10), "12.34")], "12.34", "12.34"),
        # Borda 8: parcelas em meses futuros contam no total e na média.
        ("2026-10", "2027-01", [(date(2026, 11, 15), "50.00"), (date(2027, 1, 15), "50.01")],
         "100.01", "25.00"),
        # ROUND_HALF_UP: 0,05 ÷ 2 = 0,025 → 0,03.
        ("2026-08", "2026-09", [(date(2026, 9, 1), "0.05")], "0.05", "0.03"),
    ],
)  # fmt: skip
def test_historico_total_e_media__CA_14_3(
    inicio: str, fim: str, itens: list[tuple[date, str]], total: str, media: str
) -> None:
    historico = servico(
        *[lancamento(dia, valor) for dia, valor in itens], receita(date(2026, 9, 1), "999.00")
    ).historico(inicio, fim)

    assert historico.total_gastos_periodo == Decimal(total)
    assert historico.media_mensal_gastos == Decimal(media)


def test_historico_periodo_vazio_e_so_receitas__CA_F11_7() -> None:
    """Borda 10 e período sem nada: zeros, sem categorias, total e média 0."""
    vazio = servico().historico("2026-01", "2026-03")
    so_receitas = servico(receita(date(2026, 2, 5), "5000.00")).historico("2026-01", "2026-03")

    assert [m.totais.gastos for m in vazio.meses] == [Decimal("0.00")] * 3
    assert [m.totais.saldo for m in vazio.meses] == [Decimal("0.00")] * 3
    assert vazio.por_categoria == []
    assert vazio.total_gastos_periodo == vazio.media_mensal_gastos == Decimal("0.00")
    assert so_receitas.por_categoria == []
    assert so_receitas.meses[1].totais.saldo == Decimal("5000.00")
    assert so_receitas.total_gastos_periodo == so_receitas.media_mensal_gastos == Decimal("0.00")


@pytest.mark.parametrize(
    ("inicio", "fim", "campo", "mensagem"),
    [
        ("2026-01", None, "fim", "Informe o início e o fim do período."),
        (None, "2026-01", "inicio", "Informe o início e o fim do período."),
        ("2026-09", "2026-01", "fim", "O fim do período deve ser igual ou posterior ao início."),
        ("2024-01", "2027-01", "fim", "O período pode ter no máximo 36 meses."),  # 37 meses
    ],
)
def test_historico_intervalo_invalido__CA_F11_8(
    inicio: str | None, fim: str | None, campo: str, mensagem: str
) -> None:
    """Bordas 5–7 (Q2): as duas pontas ou nenhuma, início ≤ fim, até 36 meses."""
    with pytest.raises(ErroValidacao) as erro:
        servico().historico(inicio, fim)

    assert erro.value.mensagem == mensagem
    assert erro.value.detalhes == [{"campo": campo, "mensagem": mensagem}]


def test_historico_36_meses_aceito__CA_F11_8() -> None:
    """Borda 5: exatamente 36 meses é o limite aceito."""
    historico = servico().historico("2024-01", "2026-12")

    assert len(historico.meses) == 36
