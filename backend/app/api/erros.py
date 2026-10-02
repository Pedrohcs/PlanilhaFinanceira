"""Tradução de exceções para o corpo de erro de `SPECS/03` §6.2.

É aqui que mora o mapa `codigo` → status HTTP: o domínio não conhece HTTP.
"""

import logging
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.domain.erros import ErroDominio

logger = logging.getLogger(__name__)

CODIGO_VALIDACAO = "VALIDACAO"
CODIGO_NAO_ENCONTRADO = "NAO_ENCONTRADO"
CODIGO_ERRO_INTERNO = "ERRO_INTERNO"

MENSAGEM_ERRO_INTERNO = "Erro interno. Consulte o log do servidor."
MENSAGEM_NAO_ENCONTRADO = "Recurso não encontrado."

STATUS_POR_CODIGO = {
    CODIGO_VALIDACAO: status.HTTP_422_UNPROCESSABLE_CONTENT,
    CODIGO_NAO_ENCONTRADO: status.HTTP_404_NOT_FOUND,
    "CATEGORIA_DUPLICADA": status.HTTP_409_CONFLICT,
    "CATEGORIA_EM_USO": status.HTTP_409_CONFLICT,
    "CATEGORIA_INATIVA": status.HTTP_409_CONFLICT,
    "CATEGORIA_TIPO_INCOMPATIVEL": status.HTTP_409_CONFLICT,
    "PLANILHA_INDISPONIVEL": status.HTTP_503_SERVICE_UNAVAILABLE,
    "SEM_PERMISSAO_PLANILHA": status.HTTP_503_SERVICE_UNAVAILABLE,
    "PLANILHA_NAO_ENCONTRADA": status.HTTP_503_SERVICE_UNAVAILABLE,
    "CREDENCIAIS_INVALIDAS": status.HTTP_503_SERVICE_UNAVAILABLE,
    "API_SHEETS_DESABILITADA": status.HTTP_503_SERVICE_UNAVAILABLE,
    "SCHEMA_PLANILHA_INVALIDO": status.HTTP_503_SERVICE_UNAVAILABLE,
    CODIGO_ERRO_INTERNO: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def corpo_erro(
    codigo: str, mensagem: str, detalhes: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    """Monta o corpo único de erro da API (`SPECS/03` §6.2)."""
    return {"erro": {"codigo": codigo, "mensagem": mensagem, "detalhes": detalhes or []}}


def status_de(codigo: str) -> int:
    """Status HTTP do código; desconhecido é tratado como erro interno."""
    return STATUS_POR_CODIGO.get(codigo, status.HTTP_500_INTERNAL_SERVER_ERROR)


def _campo_de(localizacao: tuple[Any, ...]) -> str:
    """Caminho do campo inválido, sem o prefixo `body`/`query` do Pydantic."""
    partes = [str(parte) for parte in localizacao if parte not in ("body", "query")]
    return ".".join(partes) or "(corpo)"


MENSAGEM_VALOR_INVALIDO = "Valor inválido."

# Mensagens em pt-BR por tipo de erro do Pydantic (F-14 §3.5). `{...}` vem do
# `ctx` do erro. `too_short`/`too_long` são os nomes que o Pydantic usa em
# texto com `BeforeValidator` (ex.: `descricao`).
MENSAGENS_PYDANTIC = {
    "missing": "Campo obrigatório.",
    "greater_than": "Deve ser maior que {gt}.",
    "greater_than_equal": "Deve ser no mínimo {ge}.",
    "less_than_equal": "Deve ser no máximo {le}.",
    "string_too_short": "Texto obrigatório.",
    "too_short": "Texto obrigatório.",
    "string_too_long": "Use no máximo {max_length} caracteres.",
    "too_long": "Use no máximo {max_length} caracteres.",
    "string_pattern_mismatch": "Formato inválido.",
    "decimal_max_places": "Use no máximo 2 casas decimais.",
    "decimal_whole_digits": "Valor acima do máximo permitido.",
    "decimal_max_digits": "Valor acima do máximo permitido.",
    **dict.fromkeys(
        (
            "int_parsing",
            "int_from_float",
            "int_type",
            "decimal_parsing",
            "decimal_type",
            "float_parsing",
            "float_type",
        ),
        "Número inválido.",
    ),
    **dict.fromkeys(("date_parsing", "date_from_datetime_parsing", "date_type"), "Data inválida."),
    **dict.fromkeys(("enum", "literal_error"), "Valor não permitido."),
}


def mensagem_em_ptbr(item: Mapping[str, Any]) -> str:
    """Mensagem curta em pt-BR para um erro do Pydantic, pelo `type` (F-14 §3.5)."""
    tipo = item.get("type", "")
    contexto = item.get("ctx") or {}
    if tipo == "value_error":
        # Validadores do domínio já falam pt-BR (ex.: `Data`): usa o texto deles.
        texto = str(contexto.get("error", "")).strip().rstrip(".")
        return f"{texto[0].upper()}{texto[1:]}." if texto else MENSAGEM_VALOR_INVALIDO
    modelo = MENSAGENS_PYDANTIC.get(tipo)
    if modelo is None:
        return MENSAGEM_VALOR_INVALIDO
    try:
        return modelo.format(**contexto)
    except (KeyError, IndexError):
        return MENSAGEM_VALOR_INVALIDO


async def tratar_erro_dominio(_: Request, erro: Exception) -> JSONResponse:
    """`ErroDominio` → status do mapa, com a mensagem em pt-BR do domínio."""
    assert isinstance(erro, ErroDominio)
    return JSONResponse(
        status_code=status_de(erro.codigo),
        content=corpo_erro(erro.codigo, erro.mensagem, erro.detalhes),
    )


async def tratar_erro_validacao(_: Request, erro: Exception) -> JSONResponse:
    """Erro do Pydantic → 422 `VALIDACAO`, um item de `detalhes` por campo, em pt-BR."""
    assert isinstance(erro, RequestValidationError)
    detalhes = [
        {"campo": _campo_de(item.get("loc", ())), "mensagem": mensagem_em_ptbr(item)}
        for item in erro.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=corpo_erro(CODIGO_VALIDACAO, "Dados inválidos.", detalhes),
    )


async def tratar_http_exception(_: Request, erro: Exception) -> JSONResponse:
    """Erros do próprio framework (rota inexistente, método errado) no envelope.

    Usa a `HTTPException` do Starlette, não a do FastAPI: o 404 de rota
    inexistente vem do roteamento e levanta a classe-mãe.
    """
    assert isinstance(erro, HTTPException)
    if erro.status_code == status.HTTP_404_NOT_FOUND:
        codigo, mensagem = CODIGO_NAO_ENCONTRADO, MENSAGEM_NAO_ENCONTRADO
    else:
        codigo, mensagem = CODIGO_ERRO_INTERNO, str(erro.detail)
    return JSONResponse(status_code=erro.status_code, content=corpo_erro(codigo, mensagem))


async def tratar_erro_inesperado(_: Request, erro: Exception) -> JSONResponse:
    """Qualquer outra exceção → 500 genérico; o detalhe fica só no log."""
    logger.exception("Erro não previsto", exc_info=erro)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=corpo_erro(CODIGO_ERRO_INTERNO, MENSAGEM_ERRO_INTERNO),
    )


def registrar_handlers(app: FastAPI) -> None:
    """Liga todos os handlers de erro à aplicação."""
    app.add_exception_handler(ErroDominio, tratar_erro_dominio)
    app.add_exception_handler(RequestValidationError, tratar_erro_validacao)
    app.add_exception_handler(HTTPException, tratar_http_exception)
    app.add_exception_handler(Exception, tratar_erro_inesperado)
