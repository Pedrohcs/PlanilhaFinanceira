"""Modelos de domínio (`SPECS/03` §5).

Cada modelo aceita só uma **linha válida** da planilha: tipos, enums, limites
de RN-01/RN-06 e as regras entre campos de `03` §5 (forma de pagamento
obrigatória em gasto, dados de parcela completos). Regras que dependem de
outros registros — categoria ativa e do mesmo tipo (RN-04) — ficam nos
serviços.
"""

import re
from datetime import date, datetime
from typing import Annotated, Any, Self

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from app.domain.datas import MES_PADRAO
from app.domain.dinheiro import PARCELAS_MAX, PARCELAS_MIN, Dinheiro
from app.domain.enums import FormaPagamento, StatusRecorrencia, TipoLancamento

_DATA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _data_iso(valor: Any) -> Any:
    """Aceita `date` ou texto `YYYY-MM-DD` — nunca número serial nem timestamp."""
    if isinstance(valor, datetime) or not isinstance(valor, date | str):
        raise ValueError("data deve estar no formato AAAA-MM-DD")
    if isinstance(valor, str) and not _DATA_ISO.fullmatch(valor):
        raise ValueError("data deve estar no formato AAAA-MM-DD")
    return valor


def _data_hora_iso(valor: Any) -> Any:
    """Aceita `datetime` ou texto ISO — nunca número (timestamp)."""
    if not isinstance(valor, datetime | str):
        raise ValueError("data e hora devem estar no formato ISO 8601")
    return valor


def _local_em_segundos(valor: datetime) -> datetime:
    """Hora local sem fuso, sem microssegundos (F-03 §3.2.6)."""
    if valor.tzinfo is not None:
        raise ValueError("data e hora devem ser locais, sem fuso")
    return valor.replace(microsecond=0)


Data = Annotated[date, BeforeValidator(_data_iso)]
DataHora = Annotated[datetime, BeforeValidator(_data_hora_iso), AfterValidator(_local_em_segundos)]
Mes = Annotated[str, Field(pattern=MES_PADRAO)]
Id = Annotated[str, Field(min_length=1)]
Slug = Annotated[str, Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]
Cor = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]
Descricao = Annotated[str, Field(min_length=1, max_length=100)]
Observacao = Annotated[str, Field(max_length=500)]


def _exigir_forma_se_gasto(tipo: TipoLancamento, forma: FormaPagamento | None) -> None:
    """RN-05: forma de pagamento é obrigatória para gasto e opcional para receita."""
    if tipo is TipoLancamento.GASTO and forma is None:
        raise ValueError("forma_pagamento é obrigatória para gasto")


class _ModeloDominio(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Lancamento(_ModeloDominio):
    """Linha da aba `Lancamentos` (`03` §5.1)."""

    id: Id
    data: Data
    tipo: TipoLancamento
    descricao: Descricao
    valor: Dinheiro
    categoria_id: Slug
    forma_pagamento: FormaPagamento | None = None
    observacao: Observacao | None = None
    parcelamento_id: Id | None = None
    parcela_numero: int | None = None
    parcela_total: int | None = None
    recorrencia_id: Id | None = None
    criado_em: DataHora
    atualizado_em: DataHora

    @model_validator(mode="after")
    def _validar_campos_relacionados(self) -> Self:
        _exigir_forma_se_gasto(self.tipo, self.forma_pagamento)
        parcela = (self.parcelamento_id, self.parcela_numero, self.parcela_total)
        preenchidos = sum(campo is not None for campo in parcela)
        if preenchidos not in (0, len(parcela)):
            raise ValueError(
                "parcelamento_id, parcela_numero e parcela_total vão juntos: "
                "todos preenchidos ou todos vazios"
            )
        if self.parcela_numero is not None and self.parcela_total is not None:
            if not PARCELAS_MIN <= self.parcela_total <= PARCELAS_MAX:
                raise ValueError(f"parcela_total deve estar entre {PARCELAS_MIN} e {PARCELAS_MAX}")
            if not 1 <= self.parcela_numero <= self.parcela_total:
                raise ValueError("parcela_numero deve estar entre 1 e parcela_total")
        return self


class Categoria(_ModeloDominio):
    """Linha da aba `Categorias` (`03` §5.2)."""

    id: Slug
    nome: Annotated[str, Field(min_length=1)]
    tipo: TipoLancamento
    cor: Cor
    ativa: bool
    criado_em: DataHora


class Recorrencia(_ModeloDominio):
    """Linha da aba `Recorrencias` (`03` §5.3)."""

    id: Id
    tipo: TipoLancamento
    descricao: Descricao
    valor: Dinheiro
    categoria_id: Slug
    forma_pagamento: FormaPagamento | None = None
    dia_do_mes: Annotated[int, Field(ge=1, le=31)]
    mes_inicio: Mes
    mes_fim: Mes | None = None
    status: StatusRecorrencia
    ultimo_mes_gerado: Mes | None = None
    criado_em: DataHora
    atualizado_em: DataHora

    @model_validator(mode="after")
    def _validar_campos_relacionados(self) -> Self:
        _exigir_forma_se_gasto(self.tipo, self.forma_pagamento)
        return self


class ListagemComAvisos[T](BaseModel):
    """Resultado de `listar()`: linhas válidas + quantas foram ignoradas (CA-16.3)."""

    itens: list[T]
    linhas_ignoradas: int = Field(default=0, ge=0)
