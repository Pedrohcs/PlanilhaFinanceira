"""Regras de categorias (REQ-11, RN-12; F-05 §3).

As funções puras cuidam do nome, da unicidade, do slug e da ordem; o
`CategoriaService` junta essas regras aos repositórios. Depende só de
`domain` e `repositories.base` (`SPECS/03` §4.2).
"""

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime

from app.domain.datas import agora
from app.domain.enums import TipoLancamento
from app.domain.erros import CategoriaDuplicada, CategoriaEmUso, CategoriaReservada, NaoEncontrado
from app.domain.modelos import TIPO_DA_CATEGORIA_RESERVADA, Categoria
from app.domain.textos import chave_sem_acento_e_caixa, colapsar_espacos, sem_acento
from app.repositories.base import (
    CategoriaRepository,
    LancamentoRepository,
    RecorrenciaRepository,
)

BASE_SLUG_PADRAO = "categoria"
_FORA_DO_SLUG = re.compile(r"[^a-z0-9]+")
_ORDEM_DO_TIPO = {TipoLancamento.GASTO: 0, TipoLancamento.RECEITA: 1}


@dataclass(frozen=True)
class CategoriaComUso:
    """Categoria com o `em_uso` calculado (F-05 §3.6.4, Q4)."""

    categoria: Categoria
    em_uso: bool

    @property
    def reservada(self) -> bool:
        """É uma das "A classificar", usadas pela importação dos cartões (RN-24)."""
        return e_reservada(self.categoria.id)


# Regras puras -------------------------------------------------------------------


def normalizar_nome(nome: str) -> str:
    """Pontas aparadas e espaços repetidos reduzidos a um (F-05 Q1)."""
    return colapsar_espacos(nome)


def e_reservada(id: str) -> bool:
    """Reservada é pelo **id**: renomeada, continua reservada (RN-24)."""
    return id in TIPO_DA_CATEGORIA_RESERVADA


def chave_do_nome(nome: str) -> str:
    """Chave de unicidade: sem acento e sem diferenciar maiúsculas (RN-12)."""
    return chave_sem_acento_e_caixa(nome)


def gerar_slug(nome: str) -> str:
    """`Contas da Casa (fixas)` → `contas-da-casa-fixas`; nada aproveitável → `categoria`."""
    slug = _FORA_DO_SLUG.sub("-", sem_acento(nome).lower()).strip("-")
    return slug or BASE_SLUG_PADRAO


def slug_livre(base: str, ocupados: set[str]) -> str:
    """`base`, ou `base-2`, `base-3`… o primeiro que não estiver em uso (`03` §5.2)."""
    if base not in ocupados:
        return base
    numero = 2
    while f"{base}-{numero}" in ocupados:
        numero += 1
    return f"{base}-{numero}"


def ordenar(categorias: Iterable[CategoriaComUso]) -> list[CategoriaComUso]:
    """GASTO antes de RECEITA; ativas antes; alfabética sem acento/caixa (F-05 Q3)."""
    return sorted(
        categorias,
        key=lambda item: (
            _ORDEM_DO_TIPO[item.categoria.tipo],
            not item.categoria.ativa,
            chave_do_nome(item.categoria.nome),
        ),
    )


# Serviço ----------------------------------------------------------------------


class CategoriaService:
    def __init__(
        self,
        categorias: CategoriaRepository,
        lancamentos: LancamentoRepository,
        recorrencias: RecorrenciaRepository,
        *,
        relogio: Callable[[], datetime] = agora,
    ) -> None:
        self._categorias = categorias
        self._lancamentos = lancamentos
        self._recorrencias = recorrencias
        self._relogio = relogio

    def listar(
        self, tipo: TipoLancamento | None = None, *, incluir_inativas: bool = False
    ) -> list[CategoriaComUso]:
        usadas = self._ids_em_uso()
        return ordenar(
            CategoriaComUso(categoria, categoria.id in usadas)
            for categoria in self._categorias.listar().itens
            if (tipo is None or categoria.tipo == tipo) and (incluir_inativas or categoria.ativa)
        )

    def criar(self, nome: str, tipo: TipoLancamento, cor: str) -> CategoriaComUso:
        nome = normalizar_nome(nome)
        existentes = self._categorias.listar().itens
        self._exigir_nome_livre(nome, tipo, existentes)
        categoria = Categoria(
            id=slug_livre(gerar_slug(nome), {c.id for c in existentes}),
            nome=nome,
            tipo=tipo,
            cor=cor.upper(),
            ativa=True,
            criado_em=self._relogio(),
        )
        self._categorias.inserir([categoria])
        return CategoriaComUso(categoria, em_uso=False)

    def atualizar(self, id: str, nome: str, cor: str, ativa: bool) -> CategoriaComUso:
        nome = normalizar_nome(nome)
        existentes = self._categorias.listar().itens
        atual = _encontrar(id, existentes)
        if e_reservada(id) and not ativa:
            raise CategoriaReservada.ao_desativar(atual.nome)
        self._exigir_nome_livre(nome, atual.tipo, existentes, ignorar_id=id)
        # `model_validate`, não `model_copy`: a cópia do Pydantic não valida (nota de T-007).
        atualizada = Categoria.model_validate(
            {**atual.model_dump(), "nome": nome, "cor": cor.upper(), "ativa": ativa}
        )
        self._categorias.atualizar(atualizada)
        return CategoriaComUso(atualizada, em_uso=id in self._ids_em_uso())

    def excluir(self, id: str) -> None:
        categoria = _encontrar(id, self._categorias.listar().itens)
        if e_reservada(id):
            raise CategoriaReservada.ao_excluir(categoria.nome)
        if id in self._ids_em_uso():
            raise CategoriaEmUso.para(categoria.nome)
        self._categorias.remover([id])

    def _ids_em_uso(self) -> set[str]:
        """Categorias referenciadas por lançamento ou recorrência, em qualquer status (RN-12)."""
        return {item.categoria_id for item in self._lancamentos.listar().itens} | {
            item.categoria_id for item in self._recorrencias.listar().itens
        }

    @staticmethod
    def _exigir_nome_livre(
        nome: str,
        tipo: TipoLancamento,
        existentes: Iterable[Categoria],
        *,
        ignorar_id: str | None = None,
    ) -> None:
        """Único por tipo, contra ativas **e** inativas (F-05 §3.1)."""
        chave = chave_do_nome(nome)
        for outra in existentes:
            if outra.id != ignorar_id and outra.tipo == tipo and chave_do_nome(outra.nome) == chave:
                raise CategoriaDuplicada.para(nome, tipo)


def _encontrar(id: str, categorias: Iterable[Categoria]) -> Categoria:
    for categoria in categorias:
        if categoria.id == id:
            return categoria
    raise NaoEncontrado("Categoria não encontrada.")
