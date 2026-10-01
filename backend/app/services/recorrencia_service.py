"""Recorrências: cadastro, edição e status (REQ-09, RN-04..06, RN-09, RN-11; F-13 §3.1).

A sincronização (REQ-10, RN-10) chega em T-029. Os formatos de campo
(valor com 2 casas, dia de 1 a 31, `YYYY-MM`…) são garantidos na entrada da
API e no modelo de domínio; aqui ficam as regras que dependem de outros dados
— a categoria (RN-04), o mês de fim e as transições de status. Depende só de
`domain`, `repositories.base` e das regras compartilhadas de lançamentos e
categorias.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.datas import agora, mes_anterior, mes_de, proximo_mes
from app.domain.enums import FormaPagamento, StatusRecorrencia, TipoLancamento
from app.domain.erros import ErroValidacao, NaoEncontrado
from app.domain.modelos import Recorrencia
from app.repositories.base import CategoriaRepository, RecorrenciaRepository
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
        *,
        relogio: Callable[[], datetime] = agora,
        novo_id: Callable[[], str] = gerar_id,
    ) -> None:
        self._categorias = categorias
        self._recorrencias = recorrencias
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
