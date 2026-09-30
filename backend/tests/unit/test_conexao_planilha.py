"""`ConexaoPlanilha` com o passo de preparação (bootstrap) — `SPECS/03` §4.5, T-008.

A abertura real é trocada por uma que devolve `PlanilhaFalsa`: nenhuma rede.
"""

from collections.abc import Callable
from pathlib import Path

import gspread
import pytest
from requests.exceptions import ConnectionError as ErroDeConexao

from app.domain.erros import PlanilhaIndisponivel, SchemaPlanilhaInvalido
from app.infra import sheets_client
from app.infra.bootstrap import preparar_planilha
from app.infra.schema_planilha import ABA_CATEGORIAS, ABAS
from app.infra.sheets_client import ConexaoPlanilha, PlanilhaAberta
from tests.planilha_falsa import PlanilhaFalsa

TITULO = "Planilha Financeira"
CREDENCIAL_INEXISTENTE = Path("credencial-inexistente-de-teste.json")


class AberturaFalsa:
    """Substitui `abrir_planilha`, sempre devolvendo o mesmo documento falso."""

    def __init__(self, documento: PlanilhaFalsa) -> None:
        self.documento = documento
        self.chamadas = 0

    def __call__(self, *_args: object, **_kwargs: object) -> PlanilhaAberta:
        self.chamadas += 1
        return PlanilhaAberta(titulo=TITULO, documento=self.documento)  # type: ignore[arg-type]


@pytest.fixture
def abrir_falso(monkeypatch: pytest.MonkeyPatch) -> Callable[[PlanilhaFalsa], AberturaFalsa]:
    def instalar(documento: PlanilhaFalsa) -> AberturaFalsa:
        abertura = AberturaFalsa(documento)
        monkeypatch.setattr(sheets_client, "abrir_planilha", abertura)
        return abertura

    return instalar


def nova_conexao(
    preparar: Callable[[gspread.Spreadsheet], None] | None = preparar_planilha,
) -> ConexaoPlanilha:
    return ConexaoPlanilha(CREDENCIAL_INEXISTENTE, "id-de-teste", preparar=preparar)


def test_conectar_prepara_a_planilha__CA_15_1(
    abrir_falso: Callable[[PlanilhaFalsa], AberturaFalsa],
) -> None:
    documento = PlanilhaFalsa()
    abrir_falso(documento)
    conexao = nova_conexao()

    planilha = conexao.conectar()

    assert planilha is not None
    assert conexao.erro is None
    assert documento.nomes_das_abas() == [aba.nome for aba in ABAS]


def test_conexao_estabelecida_nao_prepara_de_novo(
    abrir_falso: Callable[[PlanilhaFalsa], AberturaFalsa],
) -> None:
    abertura = abrir_falso(PlanilhaFalsa())
    chamadas: list[object] = []
    conexao = nova_conexao(preparar=chamadas.append)

    conexao.conectar()
    conexao.conectar()

    assert abertura.chamadas == 1
    assert len(chamadas) == 1


def test_schema_invalido_fica_guardado_e_nova_tentativa_prepara_de_novo(
    abrir_falso: Callable[[PlanilhaFalsa], AberturaFalsa],
) -> None:
    """Falha de estrutura não conecta; corrigida à mão, a nova tentativa passa (`03` §4.5)."""
    documento = PlanilhaFalsa({"Categorias": [["id", "tipo", "nome"]]})
    abertura = abrir_falso(documento)
    conexao = nova_conexao()

    assert conexao.conectar() is None
    assert isinstance(conexao.erro, SchemaPlanilhaInvalido)
    assert "Categorias, coluna B" in conexao.erro.mensagem
    with pytest.raises(SchemaPlanilhaInvalido):
        conexao.exigir_planilha()
    assert documento.escritas == []

    documento.worksheet("Categorias").valores[0] = list(ABA_CATEGORIAS.colunas)
    planilha = conexao.conectar()

    assert planilha is not None
    assert conexao.erro is None
    assert abertura.chamadas == 2
    assert len(documento.linhas("Categorias")) == 1 + 15


def test_falha_de_rede_no_preparo_nao_conecta(
    abrir_falso: Callable[[PlanilhaFalsa], AberturaFalsa],
) -> None:
    abrir_falso(PlanilhaFalsa())

    def preparar_sem_rede(_documento: gspread.Spreadsheet) -> None:
        raise ErroDeConexao("sem internet")

    conexao = nova_conexao(preparar=preparar_sem_rede)

    assert conexao.conectar() is None
    assert isinstance(conexao.erro, PlanilhaIndisponivel)
    assert conexao.planilha is None


def test_sem_preparar_so_abre(abrir_falso: Callable[[PlanilhaFalsa], AberturaFalsa]) -> None:
    """Compatível com T-005: sem `preparar`, a conexão só abre a planilha."""
    documento = PlanilhaFalsa()
    abrir_falso(documento)

    assert nova_conexao(preparar=None).conectar() is not None
    assert documento.escritas == []
