"""`ConexaoPlanilha` com o passo de preparação (bootstrap) — `SPECS/03` §4.5, T-008.

A abertura real é trocada por uma que devolve `PlanilhaFalsa`: nenhuma rede.
"""

from collections.abc import Callable
from pathlib import Path

import gspread
import pytest
from requests.exceptions import ConnectionError as ErroDeConexao

from app.domain.erros import (
    CredenciaisInvalidas,
    NaoEncontrado,
    PlanilhaIndisponivel,
    SchemaPlanilhaInvalido,
)
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
    assert len(documento.linhas("Categorias")) == 1 + 17


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


def test_executar_sem_conexao_levanta_o_erro_guardado__CA_16_1() -> None:
    """Endpoints de negócio respondem 503 com a causa real (`03` §4.5)."""
    conexao = nova_conexao()
    conexao.conectar()  # credencial inexistente: a conexão falha e guarda o erro

    with pytest.raises(CredenciaisInvalidas):
        conexao.executar(lambda documento: documento)


def test_executar_retenta_falha_transitoria__F02_3_2(
    abrir_falso: Callable[[PlanilhaFalsa], AberturaFalsa],
) -> None:
    """Operação de repositório usa a política de `02` §5.5: até 4 tentativas."""
    documento = PlanilhaFalsa()
    abrir_falso(documento)
    esperas: list[float] = []
    conexao = ConexaoPlanilha(
        CREDENCIAL_INEXISTENTE, "id-de-teste", preparar=None, dormir=esperas.append
    )
    conexao.conectar()
    tentativas: list[int] = []

    def operacao(recebido: gspread.Spreadsheet) -> str:
        tentativas.append(1)
        if len(tentativas) < 3:
            raise ErroDeConexao("instável")
        assert recebido is documento
        return "ok"

    assert conexao.executar(operacao) == "ok"
    assert len(tentativas) == 3
    assert len(esperas) == 2


def test_executar_nao_mascara_erro_de_dominio(
    abrir_falso: Callable[[PlanilhaFalsa], AberturaFalsa],
) -> None:
    """`NaoEncontrado` levantado dentro da operação sobe intacto, sem retry."""
    abrir_falso(PlanilhaFalsa())
    conexao = nova_conexao(preparar=None)
    conexao.conectar()
    chamadas: list[int] = []

    def operacao(_documento: gspread.Spreadsheet) -> None:
        chamadas.append(1)
        raise NaoEncontrado()

    with pytest.raises(NaoEncontrado):
        conexao.executar(operacao)
    assert len(chamadas) == 1
