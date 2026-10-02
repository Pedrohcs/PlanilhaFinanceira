"""Guarda dos scripts de execução (`scripts/*.ps1`; F-15 §3.1).

O comportamento (subir, esperar, abrir o navegador) é conferido executando os
scripts (roteiro de F-15). Aqui fica a parte automatizável: os três existem,
abrem no Windows PowerShell 5.1 sem erro de sintaxe e com os acentos certos, e
não leem segredos (RNF-05).
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

PASTA_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
NOMES = ["start-backend.ps1", "start-frontend.ps1", "start.ps1"]
BOM_UTF8 = b"\xef\xbb\xbf"

# Leitura de arquivo em PowerShell: nenhum script pode abrir o .env ou a credencial.
LEITURA = re.compile(r"Get-Content|ReadAll|StreamReader|Select-String|Import-Csv|\bgc\s|\bcat\s")


def texto(nome: str) -> str:
    return (PASTA_SCRIPTS / nome).read_text(encoding="utf-8-sig")


@pytest.mark.parametrize("nome", NOMES)
def test_scripts_em_utf8_com_bom__RNF_03(nome: str) -> None:
    """Sem BOM, o Windows PowerShell 5.1 lê o arquivo como ANSI e estraga os acentos."""
    assert (PASTA_SCRIPTS / nome).read_bytes().startswith(BOM_UTF8)


@pytest.mark.skipif(shutil.which("powershell") is None, reason="Windows PowerShell ausente")
@pytest.mark.parametrize("nome", NOMES)
def test_scripts_sem_erro_de_sintaxe__CA_F15_1(nome: str) -> None:
    """Analisa com o parser do próprio PowerShell (nada é executado)."""
    caminho = str(PASTA_SCRIPTS / nome).replace("'", "''")
    comando = (
        "$erros = $null; "
        f"[void][System.Management.Automation.Language.Parser]::ParseFile('{caminho}', "
        "[ref]$null, [ref]$erros); "
        "$erros | ForEach-Object { $_.Message }; exit $erros.Count"
    )
    resultado = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", comando],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr


@pytest.mark.parametrize("nome", NOMES)
def test_scripts_sem_ler_segredos__CA_F15_6(nome: str) -> None:
    """RNF-05: nenhuma leitura de arquivo e a credencial nem é citada; caminhos via script."""
    conteudo = texto(nome)

    assert not LEITURA.search(conteudo)
    assert "credentials" not in conteudo.lower()
    assert "$PSScriptRoot" in conteudo  # funciona a partir de qualquer pasta (borda 1)


def test_backend_so_em_localhost__CA_F15_6() -> None:
    """RNF-05: o uvicorn escuta só na própria máquina, sem `--reload` (Q1)."""
    conteudo = texto("start-backend.ps1")
    [comando] = [linha for linha in conteudo.splitlines() if "uvicorn app.main:app" in linha]

    assert "--host 127.0.0.1 --port 8000" in comando
    assert "--reload" not in comando
    assert "0.0.0.0" not in conteudo
