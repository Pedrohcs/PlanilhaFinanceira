"""DTOs de entrada e saída da API (`SPECS/03` §6.3)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field, PlainSerializer

from app.domain.dinheiro import PARCELAS_MAX, PARCELAS_MIN, Dinheiro, Montante
from app.domain.enums import FormaPagamento, StatusRecorrencia, TipoLancamento
from app.domain.modelos import Data, Mes
from app.services.categoria_service import CategoriaComUso, normalizar_nome
from app.services.lancamento_service import LancamentoComCategoria, ListaDoMes
from app.services.parcelamento_service import ParcelamentoCriado
from app.services.recorrencia_service import RecorrenciaComProximo, Sincronizacao
from app.services.resumo_service import HistoricoDoPeriodo, ResumoDoMes

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
    """Categoria na resposta (`SPECS/03` §6.3), com `em_uso` e `reservada` calculados."""

    id: str
    nome: str
    tipo: TipoLancamento
    cor: str
    ativa: bool
    criado_em: datetime
    em_uso: bool
    reservada: bool

    @classmethod
    def de(cls, item: CategoriaComUso) -> "CategoriaSaida":
        return cls(**item.categoria.model_dump(), em_uso=item.em_uso, reservada=item.reservada)


# Lançamentos e formas de pagamento (F-06) --------------------------------------

DESCRICAO_MAXIMO = 100
OBSERVACAO_MAXIMO = 500


def _aparar(valor: object) -> object:
    return valor.strip() if isinstance(valor, str) else valor


def _aparar_ou_nulo(valor: object) -> object:
    """Observação vazia (ou só espaços) é gravada vazia e devolvida `null` (RN-06)."""
    if isinstance(valor, str):
        return valor.strip() or None
    return valor


DescricaoEntrada = Annotated[
    str, BeforeValidator(_aparar), Field(min_length=1, max_length=DESCRICAO_MAXIMO)
]
# O limite vale só para o texto: `None` (observação vazia) não tem tamanho.
ObservacaoEntrada = Annotated[
    Annotated[str, Field(max_length=OBSERVACAO_MAXIMO)] | None,
    BeforeValidator(_aparar_ou_nulo),
]


class LancamentoEntrada(BaseModel):
    """`POST /api/lancamentos` (`SPECS/03` §6.3). `data` não aceita número (serial/timestamp)."""

    data: Data
    tipo: TipoLancamento
    descricao: DescricaoEntrada
    valor: Dinheiro
    categoria_id: Annotated[str, Field(min_length=1)]
    forma_pagamento: FormaPagamento | None = None
    observacao: ObservacaoEntrada = None


class LancamentoSaida(BaseModel):
    """Lançamento na resposta (`SPECS/03` §6.3), com nome e cor da categoria."""

    id: str
    data: date
    tipo: TipoLancamento
    descricao: str
    valor: Dinheiro
    categoria_id: str
    categoria_nome: str
    categoria_cor: str
    forma_pagamento: FormaPagamento | None
    observacao: str | None
    parcelamento_id: str | None
    parcela_numero: int | None
    parcela_total: int | None
    recorrencia_id: str | None
    criado_em: datetime
    atualizado_em: datetime

    @classmethod
    def de(cls, item: LancamentoComCategoria) -> "LancamentoSaida":
        return cls(
            **item.lancamento.model_dump(),
            categoria_nome=item.categoria_nome,
            categoria_cor=item.categoria_cor,
        )


class FormaPagamentoSaida(BaseModel):
    """`GET /api/formas-pagamento`: código do enum e rótulo (RN-05)."""

    codigo: FormaPagamento
    nome: str


class TotaisSaida(BaseModel):
    """Totais do que foi listado (`03` §6.3); `saldo` pode ser negativo (RN-13)."""

    gastos: Montante
    receitas: Montante
    saldo: Montante


class ListaLancamentosSaida(BaseModel):
    """`GET /api/lancamentos` (`SPECS/03` §6.3)."""

    mes: str
    itens: list[LancamentoSaida]
    totais: TotaisSaida
    linhas_ignoradas: int

    @classmethod
    def de(cls, lista: ListaDoMes) -> "ListaLancamentosSaida":
        return cls(
            mes=lista.mes,
            itens=[LancamentoSaida.de(item) for item in lista.itens],
            totais=TotaisSaida(
                gastos=lista.totais.gastos,
                receitas=lista.totais.receitas,
                saldo=lista.totais.saldo,
            ),
            linhas_ignoradas=lista.linhas_ignoradas,
        )


# Parcelamentos (F-12) ------------------------------------------------------------


class ParcelamentoEntrada(BaseModel):
    """`POST /api/parcelamentos` (`SPECS/03` §6.3). Sem `tipo`: é sempre gasto (REQ-07)."""

    data: Data
    descricao: DescricaoEntrada
    valor_total: Dinheiro
    parcelas: Annotated[int, Field(ge=PARCELAS_MIN, le=PARCELAS_MAX)]
    categoria_id: Annotated[str, Field(min_length=1)]
    forma_pagamento: FormaPagamento | None = None
    observacao: ObservacaoEntrada = None


class ParcelamentoSaida(BaseModel):
    """`201` de `POST /api/parcelamentos`: parcelas em ordem de `parcela_numero`."""

    parcelamento_id: str
    lancamentos: list[LancamentoSaida]

    @classmethod
    def de(cls, criado: ParcelamentoCriado) -> "ParcelamentoSaida":
        return cls(
            parcelamento_id=criado.parcelamento_id,
            lancamentos=[LancamentoSaida.de(item) for item in criado.lancamentos],
        )


# Recorrências (F-13) -------------------------------------------------------------


class RecorrenciaEntrada(BaseModel):
    """`POST`/`PUT /api/recorrencias` (`SPECS/03` §6.3). Sem observação: a aba não tem a coluna."""

    tipo: TipoLancamento
    descricao: DescricaoEntrada
    valor: Dinheiro
    categoria_id: Annotated[str, Field(min_length=1)]
    forma_pagamento: FormaPagamento | None = None
    dia_do_mes: Annotated[int, Field(ge=1, le=31)]
    mes_inicio: Mes
    mes_fim: Mes | None = None


class StatusEntrada(BaseModel):
    """`PATCH /api/recorrencias/{id}/status` — pausar, reativar ou encerrar (F-13 §3.1.5)."""

    status: StatusRecorrencia


class RecorrenciaSaida(BaseModel):
    """Recorrência na resposta (`SPECS/03` §6.3), com `proximo_mes` calculado."""

    id: str
    tipo: TipoLancamento
    descricao: str
    valor: Dinheiro
    categoria_id: str
    forma_pagamento: FormaPagamento | None
    dia_do_mes: int
    mes_inicio: str
    mes_fim: str | None
    status: StatusRecorrencia
    ultimo_mes_gerado: str | None
    proximo_mes: str | None
    criado_em: datetime
    atualizado_em: datetime

    @classmethod
    def de(cls, item: RecorrenciaComProximo) -> "RecorrenciaSaida":
        return cls(**item.recorrencia.model_dump(), proximo_mes=item.proximo_mes)


class MesesGeradosSaida(BaseModel):
    recorrencia_id: str
    meses: list[str]


class SincronizacaoSaida(BaseModel):
    """`POST /api/recorrencias/sincronizar` (`SPECS/03` §6.1): só quem gerou algo em `detalhes`."""

    lancamentos_gerados: int
    detalhes: list[MesesGeradosSaida]

    @classmethod
    def de(cls, sincronizacao: Sincronizacao) -> "SincronizacaoSaida":
        return cls(
            lancamentos_gerados=sincronizacao.lancamentos_gerados,
            detalhes=[MesesGeradosSaida(**vars(item)) for item in sincronizacao.detalhes],
        )


# Resumo (F-09) -----------------------------------------------------------------------

Percentual = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]
"""0 a 100 com 1 casa (`SPECS/03` §6.3); sai no JSON como número."""


class GastoPorCategoriaSaida(BaseModel):
    categoria_id: str
    nome: str
    cor: str
    total: Montante
    percentual: Percentual


class GastoPorFormaSaida(BaseModel):
    forma_pagamento: FormaPagamento
    nome: str
    total: Montante
    percentual: Percentual


class GastoAcumuladoSaida(BaseModel):
    dia: int
    total: Montante


class ResumoMensalSaida(BaseModel):
    """`GET /api/resumo/mensal` (`SPECS/03` §6.3). Listas só de gastos, maior primeiro."""

    mes: str
    total_gastos: Montante
    total_receitas: Montante
    saldo: Montante
    por_categoria: list[GastoPorCategoriaSaida]
    por_forma_pagamento: list[GastoPorFormaSaida]
    gasto_acumulado_diario: list[GastoAcumuladoSaida]
    linhas_ignoradas: int

    @classmethod
    def de(cls, resumo: ResumoDoMes) -> "ResumoMensalSaida":
        return cls(
            mes=resumo.mes,
            total_gastos=resumo.totais.gastos,
            total_receitas=resumo.totais.receitas,
            saldo=resumo.totais.saldo,
            por_categoria=[GastoPorCategoriaSaida(**vars(item)) for item in resumo.por_categoria],
            por_forma_pagamento=[
                GastoPorFormaSaida(**vars(item)) for item in resumo.por_forma_pagamento
            ],
            gasto_acumulado_diario=[
                GastoAcumuladoSaida(dia=dia, total=total)
                for dia, total in enumerate(resumo.gasto_acumulado_diario, start=1)
            ],
            linhas_ignoradas=resumo.linhas_ignoradas,
        )


# Histórico (F-11) --------------------------------------------------------------------


class MesDoHistoricoSaida(BaseModel):
    mes: str
    total_gastos: Montante
    total_receitas: Montante
    saldo: Montante


class CategoriaNoHistoricoSaida(BaseModel):
    categoria_id: str
    nome: str
    cor: str
    valores: list[Montante]


class ResumoHistoricoSaida(BaseModel):
    """`GET /api/resumo/historico` (`SPECS/03` §6.3). `valores` alinhados a `meses`."""

    inicio: str
    fim: str
    meses: list[MesDoHistoricoSaida]
    por_categoria: list[CategoriaNoHistoricoSaida]
    total_gastos_periodo: Montante
    media_mensal_gastos: Montante
    linhas_ignoradas: int

    @classmethod
    def de(cls, historico: HistoricoDoPeriodo) -> "ResumoHistoricoSaida":
        return cls(
            inicio=historico.inicio,
            fim=historico.fim,
            meses=[
                MesDoHistoricoSaida(
                    mes=item.mes,
                    total_gastos=item.totais.gastos,
                    total_receitas=item.totais.receitas,
                    saldo=item.totais.saldo,
                )
                for item in historico.meses
            ],
            por_categoria=[
                CategoriaNoHistoricoSaida(**vars(item)) for item in historico.por_categoria
            ],
            total_gastos_periodo=historico.total_gastos_periodo,
            media_mensal_gastos=historico.media_mensal_gastos,
            linhas_ignoradas=historico.linhas_ignoradas,
        )
