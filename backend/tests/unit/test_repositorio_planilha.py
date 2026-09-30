"""Repositórios sobre a planilha (F-03 §3.6; CA-16.3, CA-F03.16, .19–.22).

Tudo contra `PlanilhaFalsa`, que exige RAW, INSERT_ROWS e UNFORMATTED_VALUE.
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.domain.enums import FormaPagamento, StatusRecorrencia, TipoLancamento
from app.domain.erros import NaoEncontrado
from app.domain.modelos import Categoria, Lancamento, Recorrencia
from app.infra.cache import CacheAbas
from app.infra.schema_planilha import ABA_CATEGORIAS, ABA_LANCAMENTOS, ABA_RECORRENCIAS
from app.repositories.planilha import (
    CategoriaRepositoryPlanilha,
    LancamentoRepositoryPlanilha,
    RecorrenciaRepositoryPlanilha,
)
from tests.planilha_falsa import FonteFalsa, PlanilhaFalsa

CABECALHO = list(ABA_LANCAMENTOS.colunas)
CRIADO = "2026-09-29T10:15:00"


def linha(id_: str, **campos: Any) -> list[Any]:
    """Linha crua da aba `Lancamentos`, como o Sheets devolve (UNFORMATTED)."""
    dados: dict[str, Any] = {
        "id": id_, "data": "2026-09-29", "tipo": "GASTO", "descricao": f"Compra {id_}",
        "valor": 42.5, "categoria_id": "alimentacao", "forma_pagamento": "PIX",
        "observacao": "", "parcelamento_id": "", "parcela_numero": "", "parcela_total": "",
        "recorrencia_id": "", "criado_em": CRIADO, "atualizado_em": CRIADO,
    }  # fmt: skip
    dados.update(campos)
    return [dados[coluna] for coluna in CABECALHO]


def lancamento(id_: str, **campos: Any) -> Lancamento:
    dados: dict[str, Any] = {
        "id": id_,
        "data": date(2026, 9, 29),
        "tipo": TipoLancamento.GASTO,
        "descricao": f"Compra {id_}",
        "valor": Decimal("42.50"),
        "categoria_id": "alimentacao",
        "forma_pagamento": FormaPagamento.PIX,
        "criado_em": datetime(2026, 9, 29, 10, 15),
        "atualizado_em": datetime(2026, 9, 29, 10, 15),
    }
    dados.update(campos)
    return Lancamento(**dados)


def repositorio_com(*linhas: list[Any]) -> tuple[LancamentoRepositoryPlanilha, PlanilhaFalsa]:
    planilha = PlanilhaFalsa({"Lancamentos": [CABECALHO, *linhas]})
    return LancamentoRepositoryPlanilha(FonteFalsa(planilha), CacheAbas(30)), planilha


# Leitura e validação -----------------------------------------------------------


@pytest.mark.parametrize(
    ("motivo", "invalida"),
    [
        ("id vazio", linha("")),
        ("id só com espaços", linha("   ")),
        ("data como número serial", linha("x", data=46294)),
        ("data em formato brasileiro", linha("x", data="29/09/2026")),
        ("data inexistente", linha("x", data="2026-02-30")),
        ("valor zero", linha("x", valor=0)),
        ("valor negativo", linha("x", valor=-5)),
        ("valor não numérico", linha("x", valor="abc")),
        ("valor com vírgula", linha("x", valor="42,50")),
        ("tipo fora do enum", linha("x", tipo="DESPESA")),
        ("forma fora do enum", linha("x", forma_pagamento="CHEQUE")),
        ("descrição vazia", linha("x", descricao="")),
        ("categoria vazia", linha("x", categoria_id="")),
        ("gasto sem forma de pagamento", linha("x", forma_pagamento="")),
        ("parcela incompleta", linha("x", parcelamento_id="p1", parcela_numero=1)),
        ("criado_em como número", linha("x", criado_em=46294.5)),
    ],
)
def test_ignora_linhas_invalidas_e_conta__CA_16_3(
    motivo: str, invalida: list[Any], caplog: pytest.LogCaptureFixture
) -> None:
    """Borda 13 e `03` §5.6: a linha some da listagem, conta e gera WARNING."""
    repositorio, _ = repositorio_com(linha("boa-1"), invalida, linha("boa-2"))

    with caplog.at_level(logging.WARNING):
        listagem = repositorio.listar()

    assert [item.id for item in listagem.itens] == ["boa-1", "boa-2"], motivo
    assert listagem.linhas_ignoradas == 1
    assert "Aba Lancamentos, linha 3 ignorada" in caplog.text


def test_tres_validas_duas_invalidas__CA_F03_16(caplog: pytest.LogCaptureFixture) -> None:
    repositorio, _ = repositorio_com(
        linha("a"), linha("b", valor=0), linha("c"), linha("d", tipo="?"), linha("e")
    )

    with caplog.at_level(logging.WARNING):
        listagem = repositorio.listar()

    assert [item.id for item in listagem.itens] == ["a", "c", "e"]
    assert listagem.linhas_ignoradas == 2
    avisos = [registro for registro in caplog.records if registro.levelno == logging.WARNING]
    assert [registro.getMessage().split(":")[0] for registro in avisos] == [
        "Aba Lancamentos, linha 3 ignorada",
        "Aba Lancamentos, linha 5 ignorada",
    ]


def test_id_repetido_vale_o_primeiro__CA_16_3() -> None:
    """Borda 18, aplicada a todas as abas (T-009)."""
    repositorio, _ = repositorio_com(linha("a", descricao="primeira"), linha("a", descricao="2ª"))

    listagem = repositorio.listar()

    assert [item.descricao for item in listagem.itens] == ["primeira"]
    assert listagem.linhas_ignoradas == 1


def test_normaliza_espacos__RN_14() -> None:
    """Borda 14: `PIX ` com espaço no fim é aceito."""
    repositorio, _ = repositorio_com(
        linha(" a ", forma_pagamento="PIX ", tipo=" GASTO", categoria_id=" alimentacao ")
    )

    item = repositorio.obter("a")

    assert item.forma_pagamento is FormaPagamento.PIX
    assert item.categoria_id == "alimentacao"


def test_valor_com_erro_binario__RN_16() -> None:
    """Borda 17: `42.500000000000004` vira `Decimal("42.50")`."""
    repositorio, _ = repositorio_com(linha("a", valor=42.500000000000004), linha("b", valor=10))

    valores = [item.valor for item in repositorio.listar().itens]

    assert valores == [Decimal("42.50"), Decimal("10.00")]
    assert all(isinstance(valor, Decimal) for valor in valores)


def test_descricao_numerica_vira_texto() -> None:
    """Descrição "2024" digitada à mão volta do Sheets como número."""
    repositorio, _ = repositorio_com(linha("a", descricao=2024))

    assert repositorio.obter("a").descricao == "2024"


def test_linha_vazia_nao_conta() -> None:
    """Linha em branco no meio da aba é espaço, não dado inválido (T-009)."""
    repositorio, _ = repositorio_com(linha("a"), [""] * 14, [], linha("b"))

    listagem = repositorio.listar()

    assert [item.id for item in listagem.itens] == ["a", "b"]
    assert listagem.linhas_ignoradas == 0


def test_colunas_extras_ignoradas() -> None:
    planilha = PlanilhaFalsa({"Lancamentos": [[*CABECALHO, "notas"], [*linha("a"), "lembrar"]]})
    repositorio = LancamentoRepositoryPlanilha(FonteFalsa(planilha), CacheAbas(30))

    assert [item.id for item in repositorio.listar().itens] == ["a"]


def test_receita_sem_forma_de_pagamento_e_valida__RN_05() -> None:
    """Bordas 15 e 16: gasto sem forma é ignorado; receita sem forma é válida."""
    repositorio, _ = repositorio_com(
        linha("gasto", forma_pagamento=""),
        linha("receita", tipo="RECEITA", categoria_id="salario", forma_pagamento=""),
    )

    listagem = repositorio.listar()

    assert [item.id for item in listagem.itens] == ["receita"]
    assert listagem.itens[0].forma_pagamento is None
    assert listagem.linhas_ignoradas == 1


def test_leitura_unica_por_aba__RNF_04() -> None:
    """Borda 20: 5.000 lançamentos, uma chamada; o resto é memória."""
    repositorio, planilha = repositorio_com(*(linha(f"id-{n}") for n in range(5000)))

    assert len(repositorio.listar().itens) == 5000
    repositorio.obter("id-4999")
    assert planilha.leituras["Lancamentos"] == 1


def test_obter_inexistente_levanta_nao_encontrado__CA_F03_21() -> None:
    repositorio, _ = repositorio_com(linha("a"))

    with pytest.raises(NaoEncontrado) as erro:
        repositorio.obter("nao-existe")

    assert erro.value.codigo == "NAO_ENCONTRADO"


def test_listar_devolve_copia_da_lista() -> None:
    repositorio, _ = repositorio_com(linha("a"))

    repositorio.listar().itens.clear()

    assert len(repositorio.listar().itens) == 1


# Escrita -----------------------------------------------------------------------


def test_inserir_sempre_em_lote__F03_3_6_4() -> None:
    repositorio, planilha = repositorio_com()

    repositorio.inserir([lancamento("a"), lancamento("b"), lancamento("c")])
    repositorio.inserir([])

    assert [escrita[0] for escrita in planilha.escritas] == ["append_rows"]
    assert [item.id for item in repositorio.listar().itens] == ["a", "b", "c"]


def test_escreve_datas_e_enums_como_texto_e_valor_como_numero__F03_3_6_8() -> None:
    repositorio, planilha = repositorio_com()

    repositorio.inserir([lancamento("a", observacao=None)])

    assert planilha.worksheet("Lancamentos").valores[1] == [
        "a", "2026-09-29", "GASTO", "Compra a", 42.5, "alimentacao", "PIX",
        "", "", "", "", "", CRIADO, CRIADO,
    ]  # fmt: skip


def test_descricao_com_igual_nao_vira_formula__CA_F03_22() -> None:
    """Borda 19: gravada com RAW (exigido pela planilha falsa) e lida como texto."""
    repositorio, planilha = repositorio_com()

    repositorio.inserir([lancamento("a", descricao="=SOMA(A1:A9)")])

    assert planilha.worksheet("Lancamentos").valores[1][3] == "=SOMA(A1:A9)"
    assert repositorio.obter("a").descricao == "=SOMA(A1:A9)"


def test_atualiza_so_a_linha_do_id_apos_reordenacao__CA_F03_19() -> None:
    """O usuário reordenou as linhas depois da última leitura: vale o `id`, não a posição."""
    repositorio, planilha = repositorio_com(linha("a"), linha("b"), linha("c"))
    repositorio.listar()  # cache com a ordem antiga
    aba = planilha.worksheet("Lancamentos")
    aba.valores[1], aba.valores[3] = aba.valores[3], aba.valores[1]  # c, b, a
    antes = [list(valores) for valores in aba.valores]

    repositorio.atualizar(lancamento("a", descricao="Alterado", valor=Decimal("99.90")))

    depois = aba.valores
    assert depois[3][:5] == ["a", "2026-09-29", "GASTO", "Alterado", 99.9]
    assert [depois[i] for i in (0, 1, 2)] == [antes[i] for i in (0, 1, 2)]
    assert repositorio.obter("a").descricao == "Alterado"


def test_atualizar_preserva_colunas_extras_do_usuario() -> None:
    planilha = PlanilhaFalsa({"Lancamentos": [[*CABECALHO, "notas"], [*linha("a"), "lembrar"]]})
    repositorio = LancamentoRepositoryPlanilha(FonteFalsa(planilha), CacheAbas(30))

    repositorio.atualizar(lancamento("a", descricao="Alterado"))

    assert planilha.worksheet("Lancamentos").valores[1][-1] == "lembrar"
    assert planilha.escritas[0][2] == "A2:N2"


def test_atualizar_inexistente_levanta_nao_encontrado__CA_F03_21() -> None:
    repositorio, planilha = repositorio_com(linha("a"))

    with pytest.raises(NaoEncontrado):
        repositorio.atualizar(lancamento("nao-existe"))

    assert planilha.escritas == []


def test_remove_varios_ids_sem_deslizar_indices__CA_F03_20() -> None:
    """Uma única chamada, de baixo para cima: somem exatamente os pedidos."""
    repositorio, planilha = repositorio_com(*(linha(letra) for letra in "abcdef"))

    repositorio.remover(["b", "e", "c"])

    assert [item.id for item in repositorio.listar().itens] == ["a", "d", "f"]
    assert len(planilha.escritas) == 1
    pedidos = planilha.escritas[0][1]["requests"]
    inicios = [pedido["deleteDimension"]["range"]["startIndex"] for pedido in pedidos]
    assert inicios == sorted(inicios, reverse=True)


def test_remover_com_id_inexistente_nao_apaga_nada__CA_F03_20() -> None:
    """Tudo ou nada (T-009)."""
    repositorio, planilha = repositorio_com(linha("a"), linha("b"))

    with pytest.raises(NaoEncontrado, match="nao-existe"):
        repositorio.remover(["a", "nao-existe"])

    assert planilha.escritas == []
    assert [item.id for item in repositorio.listar().itens] == ["a", "b"]


def test_remover_apaga_tambem_linhas_repetidas_do_id() -> None:
    repositorio, _ = repositorio_com(linha("a"), linha("b"), linha("a", descricao="cópia"))

    repositorio.remover(["a"])

    listagem = repositorio.listar()
    assert [item.id for item in listagem.itens] == ["b"]
    assert listagem.linhas_ignoradas == 0


def test_referencia_da_aba_e_reaproveitada() -> None:
    """Sem chamada de metadados a cada operação (leitura continua sendo uma por aba)."""
    repositorio, planilha = repositorio_com(linha("a"))
    buscas: list[str] = []
    original = planilha.worksheet

    def worksheet_contado(title: str) -> Any:
        buscas.append(title)
        return original(title)

    planilha.worksheet = worksheet_contado  # type: ignore[method-assign]

    repositorio.listar()
    repositorio.inserir([lancamento("b")])
    repositorio.atualizar(lancamento("b", descricao="x"))

    assert buscas == ["Lancamentos"]


# Outras entidades --------------------------------------------------------------


def test_ida_e_volta_de_categoria_e_recorrencia__F03_3_6_8() -> None:
    planilha = PlanilhaFalsa(
        {
            "Categorias": [list(ABA_CATEGORIAS.colunas)],
            "Recorrencias": [list(ABA_RECORRENCIAS.colunas)],
        }
    )
    fonte = FonteFalsa(planilha)
    cache = CacheAbas(30)
    categorias = CategoriaRepositoryPlanilha(fonte, cache)
    recorrencias = RecorrenciaRepositoryPlanilha(fonte, cache)
    categoria = Categoria(
        id="pet", nome="Pet", tipo=TipoLancamento.GASTO, cor="#123456", ativa=False,
        criado_em=datetime(2026, 9, 29, 10, 15),
    )  # fmt: skip
    recorrencia = Recorrencia(
        id="r1", tipo=TipoLancamento.RECEITA, descricao="Salário", valor=Decimal("5000.00"),
        categoria_id="salario", dia_do_mes=5, mes_inicio="2026-01", mes_fim=None,
        status=StatusRecorrencia.ATIVA, ultimo_mes_gerado="2026-09",
        criado_em=datetime(2026, 1, 1, 8, 0), atualizado_em=datetime(2026, 9, 5, 8, 0),
    )  # fmt: skip

    categorias.inserir([categoria])
    recorrencias.inserir([recorrencia])

    assert planilha.worksheet("Categorias").valores[1][4] is False  # booleano, não texto
    assert categorias.obter("pet") == categoria
    assert recorrencias.obter("r1") == recorrencia
    assert planilha.worksheet("Recorrencias").valores[1][8] == ""  # mes_fim vazio


def test_categoria_ativa_como_texto_e_status_invalido() -> None:
    """Edição manual: `TRUE` digitado como texto é aceito; status fora do enum, não."""
    categoria = ["pet", "Pet", "GASTO", "#123456", "TRUE", CRIADO]
    recorrencia = [
        "r1", "GASTO", "Aluguel", 1500, "moradia", "BOLETO", 10, "2026-01", "", "SUSPENSA", "",
        CRIADO, CRIADO,
    ]  # fmt: skip
    planilha = PlanilhaFalsa(
        {
            "Categorias": [list(ABA_CATEGORIAS.colunas), categoria],
            "Recorrencias": [list(ABA_RECORRENCIAS.colunas), recorrencia],
        }
    )
    fonte = FonteFalsa(planilha)

    assert CategoriaRepositoryPlanilha(fonte, CacheAbas(30)).obter("pet").ativa is True
    listagem = RecorrenciaRepositoryPlanilha(fonte, CacheAbas(30)).listar()
    assert listagem.itens == []
    assert listagem.linhas_ignoradas == 1
