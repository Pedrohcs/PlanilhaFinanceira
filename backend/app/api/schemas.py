"""DTOs de entrada e saída da API (`SPECS/03` §6.3)."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field

from app.domain.enums import TipoLancamento
from app.services.categoria_service import CategoriaComUso, normalizar_nome

STATUS_OK = "ok"
STATUS_DEGRADADO = "degradado"


class ErroSaida(BaseModel):
    """Erro resumido, no mesmo vocabulário de códigos de `SPECS/03` §6.2."""

    codigo: str
    mensagem: str


class PlanilhaSaida(BaseModel):
    ok: bool
    titulo: str | None = None
    erro: ErroSaida | None = None


class SaudeSaida(BaseModel):
    """Resposta de `GET /api/health` — sempre HTTP 200 (`SPECS/03` §6.3)."""

    status: Literal["ok", "degradado"]
    planilha: PlanilhaSaida


# Categorias (F-05) ------------------------------------------------------------

NOME_CATEGORIA_MAXIMO = 40


def _normalizar_nome(valor: object) -> object:
    """Normaliza antes do limite de tamanho: `"  Pet   Shop "` conta como `"Pet Shop"`."""
    return normalizar_nome(valor) if isinstance(valor, str) else valor


def _cor_maiuscula(valor: object) -> object:
    return valor.strip().upper() if isinstance(valor, str) else valor


# O limite de 40 fica **só na entrada**: um nome maior digitado à mão na
# planilha continua válido na leitura (F-05 Q1; nota de T-013).
NomeCategoria = Annotated[
    str,
    BeforeValidator(_normalizar_nome),
    Field(min_length=1, max_length=NOME_CATEGORIA_MAXIMO),
]
CorCategoria = Annotated[str, BeforeValidator(_cor_maiuscula), Field(pattern=r"^#[0-9A-F]{6}$")]


class CategoriaEntrada(BaseModel):
    """`POST /api/categorias` (`SPECS/03` §6.1)."""

    nome: NomeCategoria
    tipo: TipoLancamento
    cor: CorCategoria


class CategoriaAtualizacao(BaseModel):
    """`PUT /api/categorias/{id}` — sem `tipo`: ele não muda (F-05 §3.3)."""

    nome: NomeCategoria
    cor: CorCategoria
    ativa: bool


class CategoriaSaida(BaseModel):
    """Categoria na resposta (`SPECS/03` §6.3), com `em_uso` calculado."""

    id: str
    nome: str
    tipo: TipoLancamento
    cor: str
    ativa: bool
    criado_em: datetime
    em_uso: bool

    @classmethod
    def de(cls, item: CategoriaComUso) -> "CategoriaSaida":
        return cls(**item.categoria.model_dump(), em_uso=item.em_uso)
