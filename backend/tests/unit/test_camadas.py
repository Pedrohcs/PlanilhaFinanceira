"""Regras de dependência entre camadas (`SPECS/03` §4.2, CA-F02.12)."""

import ast
import sys
from pathlib import Path

RAIZ_APP = Path(__file__).resolve().parents[2] / "app"


def imports_de(caminho: Path) -> set[str]:
    """Módulos importados por um arquivo, pelo texto do próprio arquivo."""
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    modulos: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            modulos.update(alias.name for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module:
            modulos.add(no.module)
    return modulos


def test_router_nao_importa_infra__CA_F02_12() -> None:
    """Routers recebem a conexão injetada; só `deps.py`/`main.py` veem `infra`."""
    routers = sorted((RAIZ_APP / "api" / "routers").glob("*.py"))
    assert routers, "nenhum router encontrado"

    for router in routers:
        modulos = imports_de(router)
        proibidos = {
            modulo
            for modulo in modulos
            if modulo == "gspread" or modulo.startswith(("gspread.", "app.infra", "google."))
        }
        assert not proibidos, f"{router.name} importa {proibidos}"


def test_domain_importa_apenas_biblioteca_padrao__CA_F02_12() -> None:
    """`domain` só usa biblioteca padrão, pydantic e o próprio `domain` (`SPECS/03` §4.2)."""
    for arquivo in sorted((RAIZ_APP / "domain").glob("*.py")):
        proibidos = {
            mod
            for mod in imports_de(arquivo)
            if not mod.startswith("app.domain")
            and mod.split(".")[0] not in sys.stdlib_module_names | {"pydantic"}
        }
        assert not proibidos, f"{arquivo.name} importa {proibidos}"


def test_infra_nao_importa_api_nem_services__CA_F02_12() -> None:
    for arquivo in sorted((RAIZ_APP / "infra").glob("*.py")):
        proibidos = {
            mod
            for mod in imports_de(arquivo)
            if mod.startswith(("app.api", "app.services", "app.repositories", "app.config"))
        }
        assert not proibidos, f"{arquivo.name} importa {proibidos}"
