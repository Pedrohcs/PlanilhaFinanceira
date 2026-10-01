"""Recorrências: cadastro, edição, status e sincronização (REQ-09, REQ-10, RN-04..06, RN-09..11).

F-13 §3.1 (cadastro e status) e §3.2 (sincronização). Os formatos de campo
(valor com 2 casas, dia de 1 a 31, `YYYY-MM`…) são garantidos na entrada da
API e no modelo de domínio; aqui ficam as regras que dependem de outros dados
— a categoria (RN-04), o mês de fim e as transições de status. Depende só de
`domain`, `repositories.base` e das regras compartilhadas de lançamentos e
categorias.
"""

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.datas import (
    agora,
    ajustar_dia,
    ano_e_mes,
    mes_anterior,
    mes_de,
    meses_entre,
    proximo_mes,
)
from app.domain.enums import FormaPagamento, StatusRecorrencia, TipoLancamento
from app.domain.erros import ErroValidacao, NaoEncontrado
from app.domain.modelos import Lancamento, Recorrencia
from app.repositories.base import (
    CategoriaRepository,
    LancamentoRepository,
    RecorrenciaRepository,
)
from app.services.categoria_service import chave_do_nome
from app.services.lancamento_service import gerar_id, validar_categoria_e_forma

ATIVA = StatusRecorrencia.ATIVA
PAUSADA = StatusRecorrencia.PAUSADA
ENCERRADA = StatusRecorrencia.ENCERRADA

MENSAGEM_RECORRENCIA_INEXISTENTE = "Recorrência não encontrada."
MENSAGEM_MES_FIM_ANTES_DO_INICIO = "O mês de fim deve ser igual ou posterior ao mês de início."
MENSAGEM_ENCERRADA_NAO_EDITA = "Recorrência encerrada não pode ser editada."

# Encerrar é definitivo: nenhuma transição sai de ENCERRADA (F-13 Q3).
_TRANSICOES = {(ATIVA, PAUSADA), (PAUSADA, ATIVA), (ATIVA, ENCERRADA), (PAUSADA, ENCERRADA)}
_ORDEM_DO_STATUS = {ATIVA: 0, PAUSADA: 1, ENCERRADA: 2}

# Uma sincronização por vez no processo; editar e mudar status esperam por ela
# (F-13 §3.2.1). Sem isso, duas abas abrindo juntas gerariam em dobro, e uma
# edição feita no meio seria sobrescrita pela cópia antiga com a marca d'água nova.
_TRAVA = threading.Lock()

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MesesGerados:
    recorrencia_id: str
    meses: list[str]


@dataclass(frozen=True)
class Sincronizacao:
    """Resultado de `POST /api/recorrencias/sincronizar` (`03` §6.1)."""

    lancamentos_gerados: int
    detalhes: list[MesesGerados]  # só as recorrências que geraram algo


@dataclass(frozen=True)
class RecorrenciaComProximo:
    """Recorrência com o próximo mês a gerar, calculado (CA-09.1; nunca gravado)."""

    recorrencia: Recorrencia
    proximo_mes: str | None


def proximo_mes_a_gerar(recorrencia: Recorrencia) -> str | None:
    """Próximo mês que a sincronização gera (F-13 §3.1.7); `None` se não há.

    Pode ser um mês futuro: é quando ele vai ser gerado. Pausada e encerrada
    não geram; ativa com a vigência toda gerada também não.
    """
    if recorrencia.status is not ATIVA:
        return None
    proximo = recorrencia.mes_inicio
    if recorrencia.ultimo_mes_gerado is not None:
        proximo = max(proximo, proximo_mes(recorrencia.ultimo_mes_gerado))
    if recorrencia.mes_fim is not None and proximo > recorrencia.mes_fim:
        return None
    return proximo


class RecorrenciaService:
    def __init__(
        self,
        categorias: CategoriaRepository,
        recorrencias: RecorrenciaRepository,
        lancamentos: LancamentoRepository,
        *,
        relogio: Callable[[], datetime] = agora,
        novo_id: Callable[[], str] = gerar_id,
    ) -> None:
        self._categorias = categorias
        self._recorrencias = recorrencias
        self._lancamentos = lancamentos
        self._relogio = relogio
        self._novo_id = novo_id

    def listar(self) -> list[RecorrenciaComProximo]:
        """Ativas, pausadas, encerradas; dentro de cada, pela descrição (F-13 §3.1.6)."""
        itens = sorted(
            self._recorrencias.listar().itens,
            key=lambda item: (
                _ORDEM_DO_STATUS[item.status],
                chave_do_nome(item.descricao),
                item.criado_em,
            ),
        )
        return [_com_proximo(item) for item in itens]

    def criar(
        self,
        *,
        tipo: TipoLancamento,
        descricao: str,
        valor: Decimal,
        categoria_id: str,
        forma_pagamento: FormaPagamento | None,
        dia_do_mes: int,
        mes_inicio: str,
        mes_fim: str | None,
    ) -> RecorrenciaComProximo:
        """Nasce ativa e nunca gerada; `mes_inicio` no passado é aceito (F-13 Q6)."""
        _validar_vigencia(mes_inicio, mes_fim)
        categoria = validar_categoria_e_forma(self._categorias, categoria_id, tipo, forma_pagamento)
        instante = self._relogio()
        recorrencia = Recorrencia(
            id=self._novo_id(),
            tipo=tipo,
            descricao=descricao,
            valor=valor,
            categoria_id=categoria.id,
            forma_pagamento=forma_pagamento,
            dia_do_mes=dia_do_mes,
            mes_inicio=mes_inicio,
            mes_fim=mes_fim,
            status=ATIVA,
            ultimo_mes_gerado=None,
            criado_em=instante,
            atualizado_em=instante,
        )
        self._recorrencias.inserir([recorrencia])
        return _com_proximo(recorrencia)

    def editar(
        self,
        id: str,
        *,
        tipo: TipoLancamento,
        descricao: str,
        valor: Decimal,
        categoria_id: str,
        forma_pagamento: FormaPagamento | None,
        dia_do_mes: int,
        mes_inicio: str,
        mes_fim: str | None,
    ) -> RecorrenciaComProximo:
        """Qualquer campo, inclusive o tipo; vale só para o que for gerado depois (CA-09.2).

        Status, marca d'água e `criado_em` são preservados; nenhum lançamento
        já gerado é tocado.
        """
        with _TRAVA:
            return self._editar(
                id,
                tipo=tipo,
                descricao=descricao,
                valor=valor,
                categoria_id=categoria_id,
                forma_pagamento=forma_pagamento,
                dia_do_mes=dia_do_mes,
                mes_inicio=mes_inicio,
                mes_fim=mes_fim,
            )

    def _editar(
        self,
        id: str,
        *,
        tipo: TipoLancamento,
        descricao: str,
        valor: Decimal,
        categoria_id: str,
        forma_pagamento: FormaPagamento | None,
        dia_do_mes: int,
        mes_inicio: str,
        mes_fim: str | None,
    ) -> RecorrenciaComProximo:
        atual = self._obter(id)  # 404 antes de qualquer regra
        if atual.status is ENCERRADA:
            raise ErroValidacao.no_campo("status", MENSAGEM_ENCERRADA_NAO_EDITA)
        _validar_vigencia(mes_inicio, mes_fim)
        categoria = validar_categoria_e_forma(
            self._categorias,
            categoria_id,
            tipo,
            forma_pagamento,
            categoria_atual=atual.categoria_id,  # a atual pode estar inativa (F-08 Q1)
        )
        editada = Recorrencia.model_validate(
            {
                **atual.model_dump(),
                "tipo": tipo,
                "descricao": descricao,
                "valor": valor,
                "categoria_id": categoria.id,
                "forma_pagamento": forma_pagamento,
                "dia_do_mes": dia_do_mes,
                "mes_inicio": mes_inicio,
                "mes_fim": mes_fim,
                "atualizado_em": self._relogio(),
            }
        )
        self._gravar(editada)
        return _com_proximo(editada)

    def mudar_status(self, id: str, status: StatusRecorrencia) -> RecorrenciaComProximo:
        """Pausar, reativar (sem retroativos — RN-11) ou encerrar (definitivo — F-13 Q3)."""
        with _TRAVA:
            return self._mudar_status(id, status)

    def _mudar_status(self, id: str, status: StatusRecorrencia) -> RecorrenciaComProximo:
        atual = self._obter(id)
        if (atual.status, status) not in _TRANSICOES:
            raise ErroValidacao.no_campo(
                "status",
                f"Não é possível mudar de {atual.status.rotulo} para {status.rotulo}.",
            )
        instante = self._relogio()
        ultimo_mes_gerado = atual.ultimo_mes_gerado
        if status is ATIVA:
            # Reativar: os meses do período pausado não são gerados (RN-11, `03` §4.4).
            limite = mes_anterior(mes_de(instante.date()))
            ultimo_mes_gerado = max(ultimo_mes_gerado or limite, limite)
        alterada = Recorrencia.model_validate(
            {
                **atual.model_dump(),
                "status": status,
                "ultimo_mes_gerado": ultimo_mes_gerado,
                "atualizado_em": instante,
            }
        )
        self._gravar(alterada)
        return _com_proximo(alterada)

    def sincronizar(self) -> Sincronizacao:
        """Gera os lançamentos devidos das recorrências ativas (REQ-10; `03` §4.4, F-13 §3.2).

        Do mês seguinte à marca d'água até o corrente — nunca um mês futuro
        (CA-10.4). Idempotente: sem nada a gerar, nada é escrito (CA-10.2); um
        lançamento excluído não volta, porque está num mês ≤ marca d'água (RN-10).
        """
        with _TRAVA:
            return self._sincronizar()

    def _sincronizar(self) -> Sincronizacao:
        instante = self._relogio()
        corrente = mes_de(instante.date())
        recorrencias = self._recorrencias.listar().itens
        # Meses que já têm lançamento da recorrência: pulados, se uma sincronização
        # anterior gravou os lançamentos e falhou antes da marca d'água (F-13 §3.2.5).
        ja_gerados = {
            (item.recorrencia_id, mes_de(item.data))
            for item in self._lancamentos.listar().itens
            if item.recorrencia_id is not None
        }
        novos: list[Lancamento] = []
        avancadas: list[Recorrencia] = []
        detalhes: list[MesesGerados] = []
        for recorrencia in recorrencias:
            primeiro = proximo_mes_a_gerar(recorrencia)  # None se não ativa ou vigência gerada
            if primeiro is None:
                continue
            ultimo = min(corrente, recorrencia.mes_fim or corrente)
            meses = meses_entre(primeiro, ultimo)  # vazio se o início é futuro
            if not meses:
                continue
            gerar = [mes for mes in meses if (recorrencia.id, mes) not in ja_gerados]
            novos.extend(self._lancamento(recorrencia, mes, instante) for mes in gerar)
            if gerar:
                detalhes.append(MesesGerados(recorrencia.id, gerar))
            avancadas.append(
                Recorrencia.model_validate(
                    {
                        **recorrencia.model_dump(),
                        "ultimo_mes_gerado": ultimo,
                        "atualizado_em": instante,
                    }
                )
            )
        # Lançamentos numa única chamada; depois, as marcas d'água (`03` §4.4).
        # Nada a gerar → nenhuma escrita (CA-10.2; `02` §5.5).
        if novos:
            self._lancamentos.inserir(novos)
        for recorrencia in avancadas:
            try:
                self._recorrencias.atualizar(recorrencia)
            except NaoEncontrado:
                # Apagada à mão no meio da sincronização: o resto segue (F-13 §3.2.6).
                logger.warning(
                    "Recorrência %s sumiu da planilha durante a sincronização.", recorrencia.id
                )
        return Sincronizacao(len(novos), detalhes)

    def _lancamento(self, recorrencia: Recorrencia, mes: str, instante: datetime) -> Lancamento:
        """Os dados atuais da recorrência valem para o que é gerado agora (CA-09.2).

        A categoria não é validada: inativa ou apagada, gera mesmo assim (F-13 Q1).
        """
        ano, numero = ano_e_mes(mes)
        return Lancamento(
            id=self._novo_id(),
            data=ajustar_dia(ano, numero, recorrencia.dia_do_mes),  # dia 31 → último dia (RN-09)
            tipo=recorrencia.tipo,
            descricao=recorrencia.descricao,
            valor=recorrencia.valor,
            categoria_id=recorrencia.categoria_id,
            forma_pagamento=recorrencia.forma_pagamento,
            observacao=None,
            recorrencia_id=recorrencia.id,
            criado_em=instante,
            atualizado_em=instante,
        )

    def _obter(self, id: str) -> Recorrencia:
        try:
            return self._recorrencias.obter(id)
        except NaoEncontrado as erro:
            # A mensagem do repositório cita o `id`, que nada diz ao usuário.
            raise NaoEncontrado(MENSAGEM_RECORRENCIA_INEXISTENTE) from erro

    def _gravar(self, recorrencia: Recorrencia) -> None:
        try:
            self._recorrencias.atualizar(recorrencia)
        except NaoEncontrado as erro:  # sumiu da planilha entre a leitura e a escrita
            raise NaoEncontrado(MENSAGEM_RECORRENCIA_INEXISTENTE) from erro


def _validar_vigencia(mes_inicio: str, mes_fim: str | None) -> None:
    if mes_fim is not None and mes_fim < mes_inicio:
        raise ErroValidacao.no_campo("mes_fim", MENSAGEM_MES_FIM_ANTES_DO_INICIO)


def _com_proximo(recorrencia: Recorrencia) -> RecorrenciaComProximo:
    return RecorrenciaComProximo(recorrencia, proximo_mes_a_gerar(recorrencia))
