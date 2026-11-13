"""Comparação de textos sem acento e sem caixa (RN-12, RN-19).

A mesma chave serve à unicidade do nome das categorias (RN-12) e ao
aprendizado da categoria pela descrição na importação dos cartões (RN-19).
"""

import re
import unicodedata

_ESPACOS = re.compile(r"\s+")
# "LOJA X PARC 03/10", "Ifood *Restaurante 1/2": o banco escreve a parcela no fim.
_SUFIXO_DE_PARCELA = re.compile(r"\s*(parc(ela)?\.?\s*)?\d{1,2}\s*/\s*\d{1,2}$")


def colapsar_espacos(texto: str) -> str:
    """Pontas aparadas e espaços repetidos reduzidos a um."""
    return _ESPACOS.sub(" ", texto).strip()


def sem_acento(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(caractere for caractere in decomposto if not unicodedata.combining(caractere))


def chave_sem_acento_e_caixa(texto: str) -> str:
    """`"  Saúde   e Bem-estar "` → `"saude e bem-estar"`."""
    return sem_acento(colapsar_espacos(texto)).casefold()


def normalizar_descricao(descricao: str) -> str:
    """Descrição comparável entre lançamentos (RN-19; F-16 §3.4.1).

    Sem acentos, minúsculas, espaços colapsados e sem o sufixo de parcela
    (retirado uma vez): `"LOJA X PARC 03/10"` → `"loja x"`.
    """
    chave = sem_acento(colapsar_espacos(descricao)).lower()
    return _SUFIXO_DE_PARCELA.sub("", chave, count=1).strip()
