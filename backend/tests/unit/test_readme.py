"""Guarda de documentação (CA-F02.13).

A parte automatizável do critério: toda falha de planilha que o backend sabe
reportar tem de estar documentada no README, com código e mensagem. Quando
alguém acrescentar um erro novo, este teste cobra a linha correspondente.
"""

from pathlib import Path

import pytest

from app.domain.erros import ErroPlanilha

README = Path(__file__).resolve().parents[3] / "README.md"

ERROS_DE_PLANILHA = sorted(ErroPlanilha.__subclasses__(), key=lambda erro: erro.codigo)


@pytest.fixture(scope="module")
def readme() -> str:
    assert README.is_file(), f"README não encontrado em {README}"
    return README.read_text(encoding="utf-8")


@pytest.mark.parametrize("erro", ERROS_DE_PLANILHA, ids=lambda erro: erro.codigo)
def test_readme_documenta_cada_erro_de_planilha__CA_F02_13(
    erro: type[ErroPlanilha], readme: str
) -> None:
    """Cada código e cada mensagem da tabela de `SPECS/02` §5.6 no README."""
    assert erro.codigo in readme, f"{erro.codigo} não está documentado"

    # A mensagem de permissão traz o e-mail da conta de serviço, que varia.
    trecho = erro.mensagem.split("<")[0].split(" com ")[0].strip()
    assert trecho in readme, f"a mensagem de {erro.codigo} não está no README"


def test_readme_cobre_a_preparacao_e_a_execucao__CA_F02_13(readme: str) -> None:
    """Os passos que o critério exige: credencial, compartilhar, ID, .env, rodar."""
    esperados = [
        "client_email",  # como descobrir o e-mail da conta de serviço
        "como Editor",  # compartilhar a planilha
        "SPREADSHEET_ID",  # o ID e onde colocá-lo
        ".env.example",  # de onde sai o .env
        "uvicorn app.main:app",  # subir o backend
        "npm start",  # subir o frontend
        "pytest",  # rodar os testes
    ]
    faltando = [trecho for trecho in esperados if trecho not in readme]

    assert not faltando, f"README não cobre: {faltando}"
