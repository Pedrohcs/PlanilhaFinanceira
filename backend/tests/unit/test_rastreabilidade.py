"""Guarda do RNF-08: toda regra de negócio tem teste automatizado (F-15 §3.5, Q10).

Lê as RN da tabela de `SPECS/01-requisitos.md` §4 — uma RN nova entra aqui sem
mexer no teste — e procura cada uma, como `RN_xx` ou `RN-xx`, no nome ou na
docstring de algum teste do backend ou do frontend (`02` §7, rastreio em testes).
"""

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
REQUISITOS = RAIZ / "SPECS" / "01-requisitos.md"
TESTES = [
    *(RAIZ / "backend" / "tests").rglob("test_*.py"),
    *(RAIZ / "frontend" / "src").rglob("*.spec.ts"),
]


def regras_de_negocio() -> list[str]:
    texto = REQUISITOS.read_text(encoding="utf-8")
    secao = texto[
        texto.index("## 4. Regras de negócio") : texto.index("## 5. Requisitos não funcionais")
    ]
    return re.findall(r"^\|\s*\*\*RN-(\d{2})\*\*", secao, flags=re.MULTILINE)


def test_toda_rn_tem_teste__RNF_08() -> None:
    regras = regras_de_negocio()
    corpus = "\n".join(caminho.read_text(encoding="utf-8") for caminho in TESTES)

    sem_teste = [f"RN-{numero}" for numero in regras if not re.search(rf"RN[_-]{numero}\b", corpus)]

    assert len(regras) >= 16, "a tabela de RN de 01 §4 não foi encontrada"
    assert not sem_teste, f"RN sem nenhum teste que a cite: {sem_teste}"
