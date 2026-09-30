"""`/api/categorias` — gestão de categorias (REQ-11; `SPECS/03` §6.1, F-05)."""

from fastapi import APIRouter, Response, status

from app.api.deps import CategoriaServiceDep
from app.api.schemas import CategoriaAtualizacao, CategoriaEntrada, CategoriaSaida
from app.domain.enums import TipoLancamento

router = APIRouter(prefix="/categorias", tags=["categorias"])


@router.get("", response_model=list[CategoriaSaida])
def listar(
    servico: CategoriaServiceDep,
    tipo: TipoLancamento | None = None,
    incluir_inativas: bool = False,
) -> list[CategoriaSaida]:
    """Ativas por padrão (é o que os formulários usam — CA-11.4); a página pede todas."""
    return [
        CategoriaSaida.de(item) for item in servico.listar(tipo, incluir_inativas=incluir_inativas)
    ]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CategoriaSaida)
def criar(entrada: CategoriaEntrada, servico: CategoriaServiceDep) -> CategoriaSaida:
    return CategoriaSaida.de(servico.criar(entrada.nome, entrada.tipo, entrada.cor))


@router.put("/{id}", response_model=CategoriaSaida)
def atualizar(
    id: str, entrada: CategoriaAtualizacao, servico: CategoriaServiceDep
) -> CategoriaSaida:
    return CategoriaSaida.de(servico.atualizar(id, entrada.nome, entrada.cor, entrada.ativa))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(id: str, servico: CategoriaServiceDep) -> Response:
    servico.excluir(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
