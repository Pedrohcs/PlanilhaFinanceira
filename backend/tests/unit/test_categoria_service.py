"""Regras de categorias (REQ-11, RN-12; F-05 §3), com repositórios em memória."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.domain.enums import FormaPagamento, StatusRecorrencia, TipoLancamento
from app.domain.erros import CategoriaDuplicada, CategoriaEmUso, NaoEncontrado
from app.domain.modelos import Categoria, Lancamento, Recorrencia
from app.repositories.memoria import (
    CategoriaRepositoryMemoria,
    LancamentoRepositoryMemoria,
    RecorrenciaRepositoryMemoria,
)
from app.services.categoria_service import (
    CategoriaService,
    chave_do_nome,
    gerar_slug,
    normalizar_nome,
    slug_livre,
)

GASTO = TipoLancamento.GASTO
RECEITA = TipoLancamento.RECEITA
AGORA = datetime(2026, 9, 30, 12, 0)


def categoria(
    id_: str, nome: str, tipo: TipoLancamento = GASTO, *, ativa: bool = True
) -> Categoria:
    return Categoria(id=id_, nome=nome, tipo=tipo, cor="#E57373", ativa=ativa, criado_em=AGORA)


def lancamento(categoria_id: str) -> Lancamento:
    return Lancamento(
        id=f"l-{categoria_id}",
        data=date(2019, 1, 10),
        tipo=GASTO,
        descricao="Compra antiga",
        valor=Decimal("10.00"),
        categoria_id=categoria_id,
        forma_pagamento=FormaPagamento.PIX,
        criado_em=AGORA,
        atualizado_em=AGORA,
    )


def recorrencia(categoria_id: str, status: StatusRecorrencia) -> Recorrencia:
    return Recorrencia(
        id=f"r-{categoria_id}",
        tipo=GASTO,
        descricao="Assinatura",
        valor=Decimal("39.90"),
        categoria_id=categoria_id,
        forma_pagamento=FormaPagamento.CREDITO,
        dia_do_mes=10,
        mes_inicio="2026-01",
        status=status,
        criado_em=AGORA,
        atualizado_em=AGORA,
    )


class Cenario:
    def __init__(
        self,
        categorias: list[Categoria] | None = None,
        lancamentos: list[Lancamento] | None = None,
        recorrencias: list[Recorrencia] | None = None,
    ) -> None:
        self.categorias = CategoriaRepositoryMemoria(categorias)
        self.lancamentos = LancamentoRepositoryMemoria(lancamentos)
        self.recorrencias = RecorrenciaRepositoryMemoria(recorrencias)
        self.servico = CategoriaService(
            self.categorias, self.lancamentos, self.recorrencias, relogio=lambda: AGORA
        )

    def nomes(self) -> list[str]:
        return [c.nome for c in self.categorias.listar().itens]


# Nome e unicidade ----------------------------------------------------------------


@pytest.mark.parametrize("repetido", ["mercado", "MERCADO", "Mércado", "  Mercado  ", "MeRcAdO"])
def test_nome_duplicado_ignora_caixa_e_acento__RN_12(repetido: str) -> None:
    """CA-11.1, CA-F05.1, borda 1."""
    cenario = Cenario([categoria("mercado", "Mercado")])

    with pytest.raises(CategoriaDuplicada) as erro:
        cenario.servico.criar(repetido, GASTO, "#FF8A65")

    assert erro.value.codigo == "CATEGORIA_DUPLICADA"
    assert erro.value.mensagem == f'Já existe uma categoria de gasto chamada "{repetido.strip()}".'
    assert cenario.nomes() == ["Mercado"]


def test_acento_nao_conta__RN_12() -> None:
    """Borda 2: "Saude" com "Saúde" existente."""
    cenario = Cenario([categoria("saude", "Saúde")])

    with pytest.raises(CategoriaDuplicada):
        cenario.servico.criar("Saude", GASTO, "#F06292")


def test_mesmo_nome_em_outro_tipo_e_permitido__RN_12() -> None:
    """CA-F05.2, borda 3: `id` com sufixo porque o slug é global."""
    cenario = Cenario([categoria("outros", "Outros", GASTO)])

    criada = cenario.servico.criar("Outros", RECEITA, "#66BB6A")

    assert criada.categoria.id == "outros-2"
    assert criada.categoria.tipo is RECEITA


def test_inativa_ocupa_o_nome__RN_12() -> None:
    """Borda 4."""
    cenario = Cenario([categoria("pet", "Pet", ativa=False)])

    with pytest.raises(CategoriaDuplicada):
        cenario.servico.criar("pet", GASTO, "#A1887F")


def test_renomear_para_outra_grafia_do_proprio_nome__RN_12() -> None:
    """CA-F05.3, borda 5."""
    cenario = Cenario([categoria("mercado", "mercado")])

    atualizada = cenario.servico.atualizar("mercado", "Mercado", "#FF8A65", True)

    assert atualizada.categoria.nome == "Mercado"


def test_renomear_para_nome_existente__RN_12() -> None:
    """Borda 6: nada muda."""
    cenario = Cenario([categoria("mercado", "Mercado"), categoria("lazer", "Lazer")])

    with pytest.raises(CategoriaDuplicada):
        cenario.servico.atualizar("mercado", "LAZER", "#FF8A65", True)

    assert cenario.nomes() == ["Mercado", "Lazer"]


def test_renomear_para_nome_de_outro_tipo_e_permitido__RN_12() -> None:
    cenario = Cenario([categoria("extra", "Extra", GASTO), categoria("bonus", "Bônus", RECEITA)])

    cenario.servico.atualizar("extra", "Bônus", "#FF8A65", True)

    assert cenario.nomes() == ["Bônus", "Bônus"]


def test_nome_normalizado_e_limite__CA_F05_23() -> None:
    """Bordas 7 e 7a: normalização no serviço; o limite de 40 é da entrada da API."""
    cenario = Cenario()

    criada = cenario.servico.criar("  Pet   Shop  ", GASTO, "#e57373")

    assert criada.categoria.nome == "Pet Shop"
    assert criada.categoria.cor == "#E57373"  # borda 14
    assert normalizar_nome("a\t\tb\nc") == "a b c"


# Slug ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("nome", "slug"),
    [
        ("Contas da Casa (fixas)", "contas-da-casa-fixas"),
        ("Saúde", "saude"),
        ("  Pet  Shop!! ", "pet-shop"),
        ("Educação & Cursos", "educacao-cursos"),
        ("!!!", "categoria"),
        ("   ", "categoria"),
        ("2º semestre", "2o-semestre"),
    ],
)
def test_gerar_slug__F05_3_2(nome: str, slug: str) -> None:
    """CA-F05.4, borda 8."""
    assert gerar_slug(nome) == slug


def test_slug_na_criacao_e_colisao__F05_3_2() -> None:
    """CA-F05.4, bordas 8 e 9."""
    assert slug_livre("pet", set()) == "pet"
    assert slug_livre("pet", {"pet", "pet-2"}) == "pet-3"

    cenario = Cenario([categoria("categoria", "Diversos")])
    criada = cenario.servico.criar("!!!", GASTO, "#90A4AE")
    assert criada.categoria.id == "categoria-2"


def test_id_de_categoria_excluida_pode_voltar__F05_3_2() -> None:
    """Borda 9."""
    cenario = Cenario([categoria("pet", "Pet")])
    cenario.servico.excluir("pet")

    assert cenario.servico.criar("Pet", GASTO, "#A1887F").categoria.id == "pet"


def test_renomear_nao_muda_id_nem_lancamentos__CA_11_2() -> None:
    """CA-11.2, CA-F05.5: o lançamento guarda só o `categoria_id`."""
    cenario = Cenario([categoria("mercado", "Mercado")], lancamentos=[lancamento("mercado")])

    atualizada = cenario.servico.atualizar("mercado", "Supermercado", "#FF8A65", True)

    assert atualizada.categoria.id == "mercado"
    assert cenario.lancamentos.listar().itens == [lancamento("mercado")]


def test_chave_do_nome() -> None:
    assert chave_do_nome("  SAÚDE ") == chave_do_nome("saude") == "saude"


# Excluir e em uso ----------------------------------------------------------------


def test_excluir_em_uso_por_lancamento__RN_12() -> None:
    """CA-11.3, CA-F05.6, borda 11: lançamento de anos atrás."""
    cenario = Cenario([categoria("mercado", "Mercado")], lancamentos=[lancamento("mercado")])

    with pytest.raises(CategoriaEmUso) as erro:
        cenario.servico.excluir("mercado")

    assert erro.value.codigo == "CATEGORIA_EM_USO"
    assert erro.value.mensagem == (
        'A categoria "Mercado" está em uso em lançamentos ou recorrências e não pode ser '
        "excluída. Desative-a para que não apareça mais em novos lançamentos."
    )
    assert cenario.nomes() == ["Mercado"]


@pytest.mark.parametrize("status", list(StatusRecorrencia))
def test_excluir_em_uso_por_recorrencia_em_qualquer_status__RN_12(
    status: StatusRecorrencia,
) -> None:
    """CA-F05.6, borda 10."""
    cenario = Cenario(
        [categoria("assinaturas", "Assinaturas")],
        recorrencias=[recorrencia("assinaturas", status)],
    )

    with pytest.raises(CategoriaEmUso):
        cenario.servico.excluir("assinaturas")


def test_excluir_sem_uso__RN_12() -> None:
    """CA-F05.7."""
    cenario = Cenario([categoria("pet", "Pet"), categoria("lazer", "Lazer")])

    cenario.servico.excluir("pet")

    assert cenario.nomes() == ["Lazer"]


def test_id_inexistente__CA_F05_10() -> None:
    cenario = Cenario([categoria("pet", "Pet")])

    with pytest.raises(NaoEncontrado, match="Categoria não encontrada."):
        cenario.servico.atualizar("nao-existe", "X", "#E57373", True)
    with pytest.raises(NaoEncontrado):
        cenario.servico.excluir("nao-existe")


def test_em_uso__CA_F05_21() -> None:
    """Borda 22: excluído o último lançamento, `em_uso` volta a `false`."""
    cenario = Cenario(
        [categoria("a", "A"), categoria("b", "B"), categoria("c", "C")],
        lancamentos=[lancamento("a")],
        recorrencias=[recorrencia("b", StatusRecorrencia.ENCERRADA)],
    )

    uso = {item.categoria.id: item.em_uso for item in cenario.servico.listar()}
    assert uso == {"a": True, "b": True, "c": False}

    cenario.lancamentos.remover(["l-a"])
    uso = {item.categoria.id: item.em_uso for item in cenario.servico.listar()}
    assert uso["a"] is False


# Ativar/desativar, listagem e ordem ----------------------------------------------


def test_ativar_desativar_preserva_o_resto__CA_11_4() -> None:
    """CA-F05.9."""
    cenario = Cenario([categoria("pet", "Pet")])

    desativada = cenario.servico.atualizar("pet", "Pet", "#E57373", False)
    assert desativada.categoria.ativa is False
    assert [c.categoria.id for c in cenario.servico.listar()] == []

    reativada = cenario.servico.atualizar("pet", "Pet", "#E57373", True)
    assert reativada.categoria == categoria("pet", "Pet")


def test_listar_filtra_tipo_e_inativas__CA_11_4() -> None:
    """CA-F05.8."""
    cenario = Cenario(
        [
            categoria("mercado", "Mercado"),
            categoria("velha", "Velha", ativa=False),
            categoria("salario", "Salário", RECEITA),
        ]
    )

    def ids(**filtro: object) -> list[str]:
        return [item.categoria.id for item in cenario.servico.listar(**filtro)]  # type: ignore[arg-type]

    assert ids() == ["mercado", "salario"]
    assert ids(incluir_inativas=True) == ["mercado", "velha", "salario"]
    assert ids(tipo=GASTO) == ["mercado"]
    assert ids(tipo=RECEITA, incluir_inativas=True) == ["salario"]


def test_ordem__CA_F05_22() -> None:
    """Ativas antes, alfabética sem acento/caixa, inativas no fim; GASTO antes de RECEITA."""
    cenario = Cenario(
        [
            categoria("salario", "Salário", RECEITA),
            categoria("saude", "saúde"),
            categoria("assinaturas", "Assinaturas", ativa=False),
            categoria("mercado", "Mercado"),
            categoria("alimentacao", "Alimentação"),
            categoria("bonus", "bônus", RECEITA),
        ]
    )

    nomes = [item.categoria.nome for item in cenario.servico.listar(incluir_inativas=True)]

    assert nomes == ["Alimentação", "Mercado", "saúde", "Assinaturas", "bônus", "Salário"]


def test_ultima_ativa_pode_ser_desativada_e_excluida__Q5() -> None:
    """Borda 18 (F-05 Q5)."""
    cenario = Cenario([categoria("salario", "Salário", RECEITA)])

    cenario.servico.atualizar("salario", "Salário", "#66BB6A", False)
    cenario.servico.excluir("salario")

    assert cenario.nomes() == []
