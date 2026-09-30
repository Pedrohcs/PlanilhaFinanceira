"""Registro de lançamentos (REQ-01, REQ-02, RN-04, RN-05; F-06 §3.5), em memória."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.domain.enums import FormaPagamento, TipoLancamento
from app.domain.erros import (
    CategoriaInativa,
    CategoriaTipoIncompativel,
    ErroValidacao,
    NaoEncontrado,
)
from app.domain.modelos import Categoria, Lancamento
from app.repositories.memoria import CategoriaRepositoryMemoria, LancamentoRepositoryMemoria
from app.services.lancamento_service import LancamentoService

AGORA = datetime(2026, 9, 30, 12, 34, 56)
GASTO = TipoLancamento.GASTO
RECEITA = TipoLancamento.RECEITA


def categoria(id_: str, nome: str, tipo: TipoLancamento, *, ativa: bool = True) -> Categoria:
    return Categoria(id=id_, nome=nome, tipo=tipo, cor="#E57373", ativa=ativa, criado_em=AGORA)


class Cenario:
    def __init__(self) -> None:
        self.categorias = CategoriaRepositoryMemoria(
            [
                categoria("mercado", "Mercado", GASTO),
                categoria("velha", "Velha", GASTO, ativa=False),
                categoria("salario", "Salário", RECEITA),
            ]
        )
        self.lancamentos = LancamentoRepositoryMemoria()
        self.servico = LancamentoService(
            self.categorias, self.lancamentos, relogio=lambda: AGORA, novo_id=lambda: "abc123"
        )

    def criar(self, **alteracoes: Any) -> Any:
        dados: dict[str, Any] = {
            "data": date(2026, 9, 29),
            "tipo": GASTO,
            "descricao": "Almoço",
            "valor": Decimal("42.50"),
            "categoria_id": "mercado",
            "forma_pagamento": FormaPagamento.PIX,
            "observacao": None,
        }
        dados.update(alteracoes)
        return self.servico.criar(**dados)


def test_cria_gasto_valido__CA_01_2() -> None:
    """CA-F06.1: uma linha, id gerado, horários iguais, categoria junto para a resposta."""
    cenario = Cenario()

    criado = cenario.criar()

    assert criado.lancamento.id == "abc123"
    assert criado.lancamento.criado_em == criado.lancamento.atualizado_em == AGORA
    assert criado.lancamento.parcelamento_id is None
    assert criado.lancamento.recorrencia_id is None
    assert (criado.categoria_nome, criado.categoria_cor) == ("Mercado", "#E57373")
    assert cenario.lancamentos.listar().itens == [criado.lancamento]


def test_id_padrao_e_uuid_hex() -> None:
    cenario = Cenario()
    servico = LancamentoService(cenario.categorias, cenario.lancamentos)

    criado = servico.criar(
        data=date(2026, 9, 29),
        tipo=GASTO,
        descricao="Almoço",
        valor=Decimal("1.00"),
        categoria_id="mercado",
        forma_pagamento=FormaPagamento.PIX,
        observacao=None,
    )

    assert len(criado.lancamento.id) == 32
    int(criado.lancamento.id, 16)  # hexadecimal


@pytest.mark.parametrize(
    ("alteracoes", "erro", "mensagem"),
    [
        (
            {"categoria_id": "velha"},
            CategoriaInativa,
            'A categoria "Velha" está desativada. Escolha uma categoria ativa.',
        ),
        (
            {"categoria_id": "salario"},
            CategoriaTipoIncompativel,
            'A categoria "Salário" é de receita e não pode ser usada num gasto.',
        ),
        (
            {"tipo": RECEITA, "categoria_id": "mercado", "forma_pagamento": None},
            CategoriaTipoIncompativel,
            'A categoria "Mercado" é de gasto e não pode ser usada numa receita.',
        ),
    ],
)
def test_categoria_inativa_ou_de_outro_tipo__RN_04(
    alteracoes: dict[str, Any], erro: type[Exception], mensagem: str
) -> None:
    """CA-F06.4, borda 7: nada é gravado."""
    cenario = Cenario()

    with pytest.raises(erro) as capturado:
        cenario.criar(**alteracoes)

    assert capturado.value.mensagem == mensagem  # type: ignore[attr-defined]
    assert cenario.lancamentos.listar().itens == []


def test_categoria_inexistente_422__RN_04() -> None:
    cenario = Cenario()

    with pytest.raises(ErroValidacao) as capturado:
        cenario.criar(categoria_id="nao-existe")

    assert capturado.value.detalhes == [
        {"campo": "categoria_id", "mensagem": "Categoria não encontrada."}
    ]
    assert cenario.lancamentos.listar().itens == []


def test_gasto_exige_forma_receita_nao__RN_05() -> None:
    """CA-F06.5, CA-02.2, borda 8."""
    cenario = Cenario()

    with pytest.raises(ErroValidacao) as capturado:
        cenario.criar(forma_pagamento=None)
    assert capturado.value.detalhes == [
        {"campo": "forma_pagamento", "mensagem": "Informe a forma de pagamento."}
    ]

    sem_forma = cenario.criar(tipo=RECEITA, categoria_id="salario", forma_pagamento=None)
    com_forma = cenario.criar(
        tipo=RECEITA, categoria_id="salario", forma_pagamento=FormaPagamento.TRANSFERENCIA
    )

    assert sem_forma.lancamento.forma_pagamento is None
    assert com_forma.lancamento.forma_pagamento is FormaPagamento.TRANSFERENCIA
    assert len(cenario.lancamentos.listar().itens) == 2


def test_datas_passadas_e_futuras__RN_02() -> None:
    """Borda 4; e a data gravada é a escolhida, não a do relógio (borda 6, RN-03)."""
    cenario = Cenario()

    antigo = cenario.criar(data=date(1999, 1, 1))
    futuro = cenario.criar(data=date(2030, 12, 31))

    assert antigo.lancamento.data == date(1999, 1, 1)
    assert futuro.lancamento.data == date(2030, 12, 31)


# Listagem mensal (F-07 §3.1) -----------------------------------------------------


def lanc(
    id_: str,
    data: date,
    valor: str = "10.00",
    *,
    tipo: TipoLancamento = GASTO,
    categoria_id: str = "mercado",
    forma: FormaPagamento | None = FormaPagamento.PIX,
    criado_em: datetime = AGORA,
) -> Lancamento:
    return Lancamento(
        id=id_,
        data=data,
        tipo=tipo,
        descricao=f"Lançamento {id_}",
        valor=Decimal(valor),
        categoria_id=categoria_id,
        forma_pagamento=forma,
        criado_em=criado_em,
        atualizado_em=criado_em,
    )


def cenario_com(*lancamentos: Lancamento) -> Cenario:
    cenario = Cenario()
    cenario.lancamentos.inserir(list(lancamentos))
    return cenario


def ids(lista: Any) -> list[str]:
    return [item.lancamento.id for item in lista.itens]


def test_listar_filtra_pelo_mes__RN_03() -> None:
    """CA-F07.1, bordas 1–2: as pontas do mês entram; os vizinhos, não."""
    cenario = cenario_com(
        lanc("ago", date(2026, 8, 31)),
        lanc("set-1", date(2026, 9, 1)),
        lanc("set-30", date(2026, 9, 30), forma=FormaPagamento.CREDITO),
        lanc("out", date(2026, 10, 1)),
        lanc("dez", date(2026, 12, 31)),
        lanc("jan", date(2027, 1, 1)),
    )

    assert ids(cenario.servico.listar("2026-09")) == ["set-30", "set-1"]
    assert ids(cenario.servico.listar("2026-12")) == ["dez"]
    assert ids(cenario.servico.listar("2027-01")) == ["jan"]
    assert ids(cenario.servico.listar("2026-11")) == []


def test_ordem_data_e_criacao_decrescentes__REQ_03() -> None:
    """CA-F07.2, borda 3."""
    cenario = cenario_com(
        lanc("antigo", date(2026, 9, 5)),
        lanc("primeiro-do-dia", date(2026, 9, 20), criado_em=datetime(2026, 9, 20, 8, 0)),
        lanc("ultimo-do-dia", date(2026, 9, 20), criado_em=datetime(2026, 9, 20, 21, 0)),
        lanc("recente", date(2026, 9, 28)),
    )

    assert ids(cenario.servico.listar("2026-09")) == [
        "recente",
        "ultimo-do-dia",
        "primeiro-do-dia",
        "antigo",
    ]


@pytest.mark.parametrize(
    ("filtros", "esperados", "gastos", "receitas"),
    [
        ({}, ["g-pix", "g-credito", "g-lazer", "r-sem-forma", "r-pix"], "60.00", "1500.00"),
        ({"tipo": GASTO}, ["g-pix", "g-credito", "g-lazer"], "60.00", "0.00"),
        ({"tipo": RECEITA}, ["r-sem-forma", "r-pix"], "0.00", "1500.00"),
        ({"categoria_id": "lazer"}, ["g-lazer"], "30.00", "0.00"),
        # Borda 4: receita sem forma não aparece com o filtro de forma ativo.
        ({"forma_pagamento": FormaPagamento.PIX}, ["g-pix", "g-lazer", "r-pix"], "40.00", "500.00"),
        (
            {"tipo": GASTO, "forma_pagamento": FormaPagamento.PIX, "categoria_id": "mercado"},
            ["g-pix"],
            "10.00",
            "0.00",
        ),
        ({"categoria_id": "nao-existe"}, [], "0.00", "0.00"),  # borda 5
    ],
)
def test_filtros_combinados_e_totais__CA_03_2(
    filtros: dict[str, Any], esperados: list[str], gastos: str, receitas: str
) -> None:
    """CA-03.2, CA-F07.3: totais somam só o que foi filtrado."""
    cenario = cenario_com(
        lanc("g-pix", date(2026, 9, 25), "10.00"),
        lanc("g-credito", date(2026, 9, 24), "20.00", forma=FormaPagamento.CREDITO),
        lanc("g-lazer", date(2026, 9, 23), "30.00", categoria_id="lazer"),
        lanc("r-sem-forma", date(2026, 9, 22), "1000.00", tipo=RECEITA, categoria_id="salario",
             forma=None),
        lanc("r-pix", date(2026, 9, 21), "500.00", tipo=RECEITA, categoria_id="salario"),
        lanc("outro-mes", date(2026, 8, 25), "999.00"),
    )  # fmt: skip

    lista = cenario.servico.listar("2026-09", **filtros)

    assert ids(lista) == esperados
    assert lista.totais.gastos == Decimal(gastos)
    assert lista.totais.receitas == Decimal(receitas)
    assert lista.totais.saldo == Decimal(receitas) - Decimal(gastos)


def test_totais_exatos__RN_13_RN_16() -> None:
    """CA-F07.4, bordas 10–12."""
    pequenos = cenario_com(
        lanc("a", date(2026, 9, 1), "0.10"),
        lanc("b", date(2026, 9, 2), "0.20"),
        lanc("r", date(2026, 9, 3), "1000.00", tipo=RECEITA, categoria_id="salario"),
    )
    totais = pequenos.servico.listar("2026-09").totais
    assert (totais.gastos, totais.receitas, totais.saldo) == (
        Decimal("0.30"),
        Decimal("1000.00"),
        Decimal("999.70"),
    )

    mil_centavos = cenario_com(*(lanc(f"c{n}", date(2026, 9, 5), "0.01") for n in range(1000)))
    assert mil_centavos.servico.listar("2026-09").totais.gastos == Decimal("10.00")

    negativo = cenario_com(lanc("g", date(2026, 9, 1), "150.00"))
    assert negativo.servico.listar("2026-09").totais.saldo == Decimal("-150.00")

    vazio = Cenario().servico.listar("2026-09")
    assert (vazio.totais.gastos, vazio.totais.receitas, vazio.totais.saldo) == (
        Decimal("0.00"),
        Decimal("0.00"),
        Decimal("0.00"),
    )


def test_nome_atual_e_categoria_inexistente__CA_11_2() -> None:
    """CA-11.2, CA-F07.6, bordas 6–8: nome atual; inativa normal; apagada = placeholder."""
    cenario = cenario_com(
        lanc("renomeada", date(2019, 1, 10), categoria_id="mercado"),
        lanc("inativa", date(2019, 1, 11), categoria_id="velha"),
        lanc("apagada", date(2019, 1, 12), categoria_id="sumiu"),
    )
    cenario.categorias.atualizar(
        Categoria.model_validate(
            {**cenario.categorias.obter("mercado").model_dump(), "nome": "Supermercado"}
        )
    )

    itens = {item.lancamento.id: item for item in cenario.servico.listar("2019-01").itens}

    assert itens["renomeada"].categoria_nome == "Supermercado"
    assert itens["inativa"].categoria_nome == "Velha"
    assert (itens["apagada"].categoria_nome, itens["apagada"].categoria_cor) == (
        "Categoria não encontrada",
        "#9E9E9E",
    )


def test_listar_repassa_linhas_ignoradas__CA_16_3() -> None:
    cenario = Cenario()

    assert cenario.servico.listar("2026-09").linhas_ignoradas == 0


# Editar e excluir (F-08 §3.1–§3.2) -----------------------------------------------

DEPOIS = datetime(2026, 10, 1, 9, 0)


def editar(cenario: Cenario, id_: str, **alteracoes: Any) -> Any:
    dados: dict[str, Any] = {
        "data": date(2026, 9, 29),
        "tipo": GASTO,
        "descricao": "Almoço",
        "valor": Decimal("42.50"),
        "categoria_id": "mercado",
        "forma_pagamento": FormaPagamento.PIX,
        "observacao": None,
    }
    dados.update(alteracoes)
    return cenario.servico.editar(id_, **dados)


def cenario_de_edicao(*lancamentos: Lancamento) -> Cenario:
    cenario = cenario_com(*lancamentos)
    cenario.servico = LancamentoService(
        cenario.categorias, cenario.lancamentos, relogio=lambda: DEPOIS
    )
    return cenario


def test_editar_todos_os_campos_preserva_os_demais__CA_05_1() -> None:
    """CA-F08.1: tipo trocado inclusive; parcela, recorrência, id e criado_em preservados."""
    original = Lancamento.model_validate(
        {
            **lanc("p3", date(2026, 9, 15), "333.34").model_dump(),
            "parcelamento_id": "par",
            "parcela_numero": 3,
            "parcela_total": 10,
            "recorrencia_id": "rec",
        }
    )
    cenario = cenario_de_edicao(original)

    editado = editar(
        cenario,
        "p3",
        data=date(2026, 10, 2),
        tipo=RECEITA,
        descricao="Estorno",
        valor=Decimal("10.00"),
        categoria_id="salario",
        forma_pagamento=None,
        observacao="corrigido",
    ).lancamento

    assert (editado.data, editado.tipo, editado.descricao, editado.valor) == (
        date(2026, 10, 2),
        RECEITA,
        "Estorno",
        Decimal("10.00"),
    )
    assert (editado.categoria_id, editado.forma_pagamento, editado.observacao) == (
        "salario",
        None,
        "corrigido",
    )
    assert (editado.id, editado.parcelamento_id, editado.parcela_numero, editado.parcela_total) == (
        "p3",
        "par",
        3,
        10,
    )
    assert editado.recorrencia_id == "rec"
    assert editado.criado_em == original.criado_em
    assert editado.atualizado_em == DEPOIS
    assert cenario.lancamentos.obter("p3") == editado


def test_editar_sem_mudar_nada_so_atualiza_o_horario() -> None:
    """Borda 10."""
    original = lanc("a", date(2026, 9, 29), "42.50")
    cenario = cenario_de_edicao(original)

    editado = editar(cenario, "a", descricao=original.descricao).lancamento

    assert editado.model_dump(exclude={"atualizado_em"}) == original.model_dump(
        exclude={"atualizado_em"}
    )
    assert editado.atualizado_em == DEPOIS


@pytest.mark.parametrize(
    ("alteracoes", "erro"),
    [
        ({"categoria_id": "salario"}, CategoriaTipoIncompativel),  # gasto com categoria de receita
        ({"tipo": RECEITA, "forma_pagamento": None}, CategoriaTipoIncompativel),  # borda 4
        ({"categoria_id": "nao-existe"}, ErroValidacao),
        ({"forma_pagamento": None}, ErroValidacao),  # borda 5
    ],
)
def test_editar_regras_de_categoria_e_forma__RN_04_RN_05(
    alteracoes: dict[str, Any], erro: type[Exception]
) -> None:
    """CA-F08.4: a linha não muda."""
    original = lanc("a", date(2026, 9, 29))
    cenario = cenario_de_edicao(original)

    with pytest.raises(erro):
        editar(cenario, "a", **alteracoes)

    assert cenario.lancamentos.obter("a") == original


def test_editar_categoria_inativa__Q1() -> None:
    """CA-F08.5: manter a atual inativa passa; trocar para outra inativa, não."""
    cenario = cenario_de_edicao(
        lanc("na-velha", date(2026, 9, 29), categoria_id="velha"),
        lanc("no-mercado", date(2026, 9, 28), categoria_id="mercado"),
    )

    mantida = editar(cenario, "na-velha", categoria_id="velha", valor=Decimal("99.00"))
    assert mantida.lancamento.valor == Decimal("99.00")
    assert mantida.categoria_nome == "Velha"

    with pytest.raises(CategoriaInativa):
        editar(cenario, "no-mercado", categoria_id="velha")


def test_editar_e_excluir_inexistente_404__CA_F08_3() -> None:
    """404 vem antes das regras de categoria (uma categoria errada não mascara o 404)."""
    cenario = cenario_de_edicao(lanc("a", date(2026, 9, 29)))

    with pytest.raises(NaoEncontrado, match="^Lançamento não encontrado.$"):
        editar(cenario, "nao-existe", categoria_id="tambem-nao-existe")
    with pytest.raises(NaoEncontrado, match="^Lançamento não encontrado.$"):
        cenario.servico.excluir("nao-existe")
    assert ids(cenario.servico.listar("2026-09")) == ["a"]


def test_excluir_parcela_so_ela__RN_08() -> None:
    """CA-F08.8, borda 8: as outras parcelas continuam com "k/N"."""
    parcelas = [
        Lancamento.model_validate(
            {
                **lanc(f"p{k}", date(2026, 9, 15), "100.00").model_dump(),
                "parcelamento_id": "par",
                "parcela_numero": k,
                "parcela_total": 3,
            }
        )
        for k in (1, 2, 3)
    ]
    cenario = cenario_de_edicao(*parcelas)

    cenario.servico.excluir("p2")

    restantes = cenario.lancamentos.listar().itens
    assert [(p.id, p.parcela_numero, p.parcela_total) for p in restantes] == [
        ("p1", 1, 3),
        ("p3", 3, 3),
    ]


def test_excluir_recorrente_nao_toca_recorrencia__RN_10() -> None:
    """Borda 9: o serviço só remove o lançamento; a marca d'água da recorrência não muda."""
    recorrente = Lancamento.model_validate(
        {**lanc("r", date(2026, 9, 10)).model_dump(), "recorrencia_id": "rec"}
    )
    cenario = cenario_de_edicao(recorrente)

    cenario.servico.excluir("r")

    assert cenario.lancamentos.listar().itens == []
