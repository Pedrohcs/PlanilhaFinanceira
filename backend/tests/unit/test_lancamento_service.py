"""Registro de lançamentos (REQ-01, REQ-02, RN-04, RN-05; F-06 §3.5), em memória."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.domain.enums import FormaPagamento, TipoLancamento
from app.domain.erros import CategoriaInativa, CategoriaTipoIncompativel, ErroValidacao
from app.domain.modelos import Categoria
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
    assert criado.categoria.nome == "Mercado"
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
