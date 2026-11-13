"""Repositórios em memória, para os testes de serviço e de API (`SPECS/02` §8).

Mesmo comportamento observável dos de planilha (CA-F03.23): mesma ordem, mesma
exceção, remoção tudo-ou-nada, e `linhas_ignoradas` sempre 0 — aqui não há
edição manual.
"""

from pydantic import BaseModel

from app.domain.erros import NaoEncontrado
from app.domain.modelos import (
    Cartao,
    Categoria,
    Importacao,
    Lancamento,
    ListagemComAvisos,
    Recorrencia,
)


class RepositorioMemoria[T: BaseModel]:
    def __init__(self, itens: list[T] | None = None) -> None:
        self._itens: list[T] = list(itens or [])

    def listar(self) -> ListagemComAvisos[T]:
        return ListagemComAvisos[T](itens=list(self._itens))

    def obter(self, id: str) -> T:
        return self._itens[self._posicao(id)]

    def inserir(self, itens: list[T]) -> None:
        self._itens.extend(itens)

    def atualizar(self, item: T) -> None:
        self._itens[self._posicao(_id_de(item))] = item

    def atualizar_varios(self, itens: list[T]) -> None:
        posicoes = [self._posicao(_id_de(item)) for item in itens]  # tudo ou nada
        for posicao, item in zip(posicoes, itens, strict=True):
            self._itens[posicao] = item

    def remover(self, ids: list[str]) -> None:
        posicoes = {self._posicao(id) for id in ids}  # tudo ou nada
        self._itens = [item for posicao, item in enumerate(self._itens) if posicao not in posicoes]

    def _posicao(self, id: str) -> int:
        for posicao, item in enumerate(self._itens):
            if _id_de(item) == id:
                return posicao
        raise NaoEncontrado(f"Registro {id} não encontrado.")


class LancamentoRepositoryMemoria(RepositorioMemoria[Lancamento]): ...


class CategoriaRepositoryMemoria(RepositorioMemoria[Categoria]): ...


class RecorrenciaRepositoryMemoria(RepositorioMemoria[Recorrencia]): ...


class CartaoRepositoryMemoria(RepositorioMemoria[Cartao]): ...


class ImportacaoRepositoryMemoria(RepositorioMemoria[Importacao]): ...


def _id_de(item: BaseModel) -> str:
    return str(item.id)  # type: ignore[attr-defined]
