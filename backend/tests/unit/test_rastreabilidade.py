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


MARCA_PLANEJADA = "(planejada"
"""RN marcada *(planejada — F-xx)* em `01` §4 ainda não tem implementação e fica de fora (F-16)."""


def regras_na_secao(secao: str) -> list[str]:
    """Números das RN da tabela, sem as marcadas como planejadas."""
    regras = []
    for linha in secao.splitlines():
        achado = re.match(r"^\|\s*\*\*RN-(\d{2})\*\*", linha)
        if achado and MARCA_PLANEJADA not in linha:
            regras.append(achado.group(1))
    return regras


def regras_de_negocio() -> list[str]:
    texto = REQUISITOS.read_text(encoding="utf-8")
    secao = texto[
        texto.index("## 4. Regras de negócio") : texto.index("## 5. Requisitos não funcionais")
    ]
    return regras_na_secao(secao)


def test_rn_planejada_fica_de_fora__RNF_08() -> None:
    # Números fora de uso de propósito: o texto deste teste também é lido pelo guarda.
    secao = (
        "| **RN-97** | Regra pronta. |\n"
        "| **RN-98** | Regra futura. *(planejada — F-99)* |\n"
        "| **RN-99** | Outra pronta. |\n"
    )
    assert regras_na_secao(secao) == ["97", "99"]


def test_toda_rn_tem_teste__RNF_08() -> None:
    regras = regras_de_negocio()
    corpus = "\n".join(caminho.read_text(encoding="utf-8") for caminho in TESTES)

    sem_teste = [f"RN-{numero}" for numero in regras if not re.search(rf"RN[_-]{numero}\b", corpus)]

    assert len(regras) >= 16, "a tabela de RN de 01 §4 não foi encontrada"
    assert not sem_teste, f"RN sem nenhum teste que a cite: {sem_teste}"
