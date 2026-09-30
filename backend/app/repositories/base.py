"""Contratos dos repositórios (`SPECS/03` §4.3).

Os serviços dependem só destes Protocols; as implementações de planilha e de
memória são intercambiáveis e observacionalmente equivalentes (CA-F03.23).
Filtros por mês, tipo etc. são feitos no serviço sobre `listar()`.
"""

from typing import Protocol

from app.domain.modelos import Categoria, Lancamento, ListagemComAvisos, Recorrencia


class Repositorio[T](Protocol):
    def listar(self) -> ListagemComAvisos[T]:
        """Todos os itens válidos, na ordem da aba, e quantas linhas foram ignoradas."""
        ...

    def obter(self, id: str) -> T:
        """Item do `id`; levanta `NaoEncontrado` se não existir."""
        ...

    def inserir(self, itens: list[T]) -> None:
        """Acrescenta os itens numa única escrita (sempre em lote)."""
        ...

    def atualizar(self, item: T) -> None:
        """Substitui o item de mesmo `id`; levanta `NaoEncontrado` se não existir."""
        ...

    def remover(self, ids: list[str]) -> None:
        """Remove todos os `ids` ou nenhum: levanta `NaoEncontrado` se faltar algum."""
        ...


class LancamentoRepository(Repositorio[Lancamento], Protocol): ...


class CategoriaRepository(Repositorio[Categoria], Protocol): ...


class RecorrenciaRepository(Repositorio[Recorrencia], Protocol): ...
