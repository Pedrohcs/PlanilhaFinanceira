"""Ambiente da suíte de integração, sem rede (F-15 §3.2.2–4; CA-F15.7 a CA-F15.9).

O que decide se a integração roda, contra qual planilha, e o que ela apaga no
fim — testado com arquivos `.env` temporários e a planilha falsa.
"""

from pathlib import Path

from app.infra.schema_planilha import ABA_CATEGORIAS, ABA_LANCAMENTOS
from tests.integracao.ambiente import (
    apagar_linhas_marcadas,
    ler_planilha_teste,
    mesma_planilha_do_app,
    nova_marca,
    planilhas_do_app,
)
from tests.planilha_falsa import PlanilhaFalsa


def arquivo_env(pasta: Path, conteudo: str) -> Path:
    caminho = pasta / ".env"
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho


def test_le_planilha_teste_do_env__CA_F15_7(tmp_path: Path) -> None:
    """Q5: o `.env` vale sozinho; o terminal tem precedência; vazio = pula (borda 9)."""
    env = arquivo_env(tmp_path, "SPREADSHEET_ID=app\nSPREADSHEET_ID_TESTE=do-arquivo\n")
    (tmp_path / "vazio").mkdir()
    vazio = arquivo_env(tmp_path / "vazio", "SPREADSHEET_ID_TESTE=\n")

    assert ler_planilha_teste({}, env) == "do-arquivo"
    assert ler_planilha_teste({"SPREADSHEET_ID_TESTE": "do-terminal"}, env) == "do-terminal"
    assert ler_planilha_teste({"SPREADSHEET_ID_TESTE": "  "}, env) == "do-arquivo"
    assert ler_planilha_teste({}, vazio) is None
    assert ler_planilha_teste({}, tmp_path / "nao-existe.env") is None


def test_trava_mesma_planilha__CA_F15_8(tmp_path: Path) -> None:
    """§3.2.3: a planilha de teste não pode ser a do app, venha ela do `.env` ou do terminal."""
    env = arquivo_env(
        tmp_path, "SPREADSHEET_ID=planilha-real\nSPREADSHEET_ID_TESTE=planilha-real\n"
    )

    assert planilhas_do_app(None, env) == {"planilha-real"}
    assert planilhas_do_app("outra-do-terminal", env) == {"planilha-real", "outra-do-terminal"}
    assert mesma_planilha_do_app("planilha-real", planilhas_do_app(None, env))
    assert mesma_planilha_do_app(" outra-do-terminal ", planilhas_do_app("outra-do-terminal", env))
    assert not mesma_planilha_do_app("planilha-de-teste", planilhas_do_app(None, env))


def test_apaga_so_linhas_marcadas__CA_F15_9() -> None:
    """Borda 10: marca em `id`, `descricao` ou `nome`, blocos separados, numa única escrita."""
    marca = nova_marca()
    cabecalho = list(ABA_LANCAMENTOS.colunas)
    coluna = {nome: i for i, nome in enumerate(cabecalho)}

    def lancamento(id_: str, descricao: str) -> list[str]:
        linha = [""] * len(cabecalho)
        linha[coluna["id"]], linha[coluna["descricao"]] = id_, descricao
        return linha

    documento = PlanilhaFalsa(
        {
            ABA_LANCAMENTOS.nome: [
                cabecalho,
                lancamento("real-1", "Mercado"),
                lancamento("a1", f"{marca} gasto"),  # marca na descrição
                lancamento(f"{marca}-id", "=SOMA(A1:A2)"),  # marca no id
                lancamento("real-2", "Aluguel"),
                lancamento("d1", "teste-desempenho-abc 7"),  # outra marca de teste
                lancamento("real-3", "texto com teste-integracao- no meio"),
            ],
            ABA_CATEGORIAS.nome: [
                list(ABA_CATEGORIAS.colunas),
                ["alimentacao", "Alimentação", "GASTO", "#E57373", True, ""],
                ["c1", f"{marca}-novo", "GASTO", "#5C6BC0", False, ""],
            ],
        }
    )  # sem a aba `Recorrencias`: é ignorada

    assert apagar_linhas_marcadas(documento) == 4

    restantes = [linha[coluna["id"]] for linha in documento.linhas(ABA_LANCAMENTOS.nome)[1:]]
    assert restantes == ["real-1", "real-2", "real-3"]
    assert [linha[0] for linha in documento.linhas(ABA_CATEGORIAS.nome)] == ["id", "alimentacao"]
    assert [escrita[0] for escrita in documento.escritas] == ["batch_update"]
    assert apagar_linhas_marcadas(documento) == 0
    assert len(documento.escritas) == 1  # nada a apagar, nenhuma escrita
