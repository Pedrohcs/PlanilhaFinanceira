"""Repositório genérico sobre uma aba da planilha (F-03 §3.5–§3.6).

- **Leitura:** uma chamada por aba (`UNFORMATTED_VALUE`), guardada no cache;
  linha inválida é ignorada, contada e registrada em `WARNING` (CA-16.3).
- **Escrita:** `RAW` + `INSERT_ROWS`, sempre em lote; invalida o cache da aba.
- **Atualizar/remover:** relê a aba na hora e localiza a linha pelo `id` —
  nunca guarda número de linha, porque o usuário reordena a planilha à mão.
  `atualizar_varios` grava todas as linhas numa única chamada (F-16).
"""

import logging
from collections.abc import Callable
from typing import Any, Protocol

import gspread
from gspread.utils import InsertDataOption, ValueInputOption, ValueRenderOption, rowcol_to_a1
from pydantic import BaseModel, ValidationError

from app.domain.dinheiro import valor_da_planilha
from app.domain.erros import NaoEncontrado
from app.domain.modelos import ListagemComAvisos
from app.infra.cache import CacheAbas
from app.infra.schema_planilha import Aba

# Número lido numa coluna monetária vem com erro binário do Sheets (RN-16).
COLUNAS_MONETARIAS = frozenset({"valor"})
# Texto digitado à mão que o Sheets guardou como número (ex.: descrição "2024").
# Vale também para o final do cartão ("1234") e o nome do banco (F-16).
COLUNAS_TEXTO_LIVRE = frozenset({"descricao", "observacao", "nome", "banco", "final"})

logger = logging.getLogger(__name__)


class FontePlanilha(Protocol):
    """Quem dá acesso à planilha aberta — `ConexaoPlanilha.executar` em produção."""

    def executar[R](self, operacao: Callable[[gspread.Spreadsheet], R]) -> R: ...


class RepositorioPlanilha[M: BaseModel]:
    """Base das implementações; cada subclasse define `aba` e `modelo`."""

    aba: Aba
    modelo: type[M]

    def __init__(self, fonte: FontePlanilha, cache: CacheAbas) -> None:
        self._fonte = fonte
        self._cache = cache
        self._referencia: tuple[gspread.Spreadsheet, gspread.Worksheet] | None = None

    # Leitura ---------------------------------------------------------------

    def listar(self) -> ListagemComAvisos[M]:
        listagem = self._cache.obter(self.aba.nome, self._ler)
        # Cópia da lista: quem chama pode mexer nela sem estragar o cache.
        return ListagemComAvisos[M](
            itens=list(listagem.itens), linhas_ignoradas=listagem.linhas_ignoradas
        )

    def obter(self, id: str) -> M:
        for item in self.listar().itens:
            if _id_de(item) == id:
                return item
        raise NaoEncontrado(f"Registro {id} não encontrado.")

    def _ler(self) -> ListagemComAvisos[M]:
        linhas = self._executar(
            lambda _documento, aba: aba.get_all_values(
                value_render_option=ValueRenderOption.unformatted
            )
        )
        return self._interpretar(linhas)

    def _interpretar(self, linhas: list[list[Any]]) -> ListagemComAvisos[M]:
        itens: list[M] = []
        ids_vistos: set[str] = set()
        ignoradas = 0
        for numero, linha in enumerate(linhas[1:], start=2):
            celulas = self._celulas(linha)
            if all(valor is None for valor in celulas.values()):
                continue  # linha em branco é espaço, não dado inválido
            try:
                item = self.modelo.model_validate(celulas)
            except ValidationError as erro:
                ignoradas += 1
                self._avisar(numero, _motivo(erro))
                continue
            if _id_de(item) in ids_vistos:
                ignoradas += 1
                self._avisar(numero, f"id {_id_de(item)} repetido")
                continue
            ids_vistos.add(_id_de(item))
            itens.append(item)
        return ListagemComAvisos[M](itens=itens, linhas_ignoradas=ignoradas)

    def _celulas(self, linha: list[Any]) -> dict[str, Any]:
        """Linha crua → campos do modelo: sem espaços, `""` vira `None`."""
        completa = list(linha) + [""] * (len(self.aba.colunas) - len(linha))
        celulas: dict[str, Any] = {}
        for coluna, valor in zip(self.aba.colunas, completa, strict=False):
            if isinstance(valor, str):
                valor = valor.strip() or None
            elif _e_numero(valor):
                if coluna in COLUNAS_MONETARIAS:
                    valor = valor_da_planilha(valor)
                elif coluna in COLUNAS_TEXTO_LIVRE:
                    valor = str(valor)
            celulas[coluna] = valor
        return celulas

    def _avisar(self, numero: int, motivo: str) -> None:
        logger.warning("Aba %s, linha %d ignorada: %s", self.aba.nome, numero, motivo)

    # Escrita ---------------------------------------------------------------

    def inserir(self, itens: list[M]) -> None:
        if not itens:
            return
        linhas = [self._para_linha(item) for item in itens]
        self._escrever(
            lambda _documento, aba: aba.append_rows(
                values=linhas,
                value_input_option=ValueInputOption.raw,
                insert_data_option=InsertDataOption.insert_rows,
            )
        )

    def atualizar(self, item: M) -> None:
        linha = self._para_linha(item)
        id_ = _id_de(item)

        def operacao(_documento: gspread.Spreadsheet, aba: gspread.Worksheet) -> None:
            numero = self._linhas_do_id(aba, [id_])[id_][0]
            aba.update(
                values=[linha],
                range_name=self._intervalo_da_linha(numero),
                value_input_option=ValueInputOption.raw,
            )

        self._escrever(operacao)

    def atualizar_varios(self, itens: list[M]) -> None:
        """Uma leitura para localizar os `id`s e **uma** escrita com todas as linhas."""
        if not itens:
            return
        linhas = {_id_de(item): self._para_linha(item) for item in itens}

        def operacao(_documento: gspread.Spreadsheet, aba: gspread.Worksheet) -> None:
            numeros = self._linhas_do_id(aba, list(linhas))
            aba.batch_update(
                data=[
                    {
                        "range": self._intervalo_da_linha(numeros[id_][0]),
                        "values": [linha],
                    }
                    for id_, linha in linhas.items()
                ],
                value_input_option=ValueInputOption.raw,
            )

        self._escrever(operacao)

    def remover(self, ids: list[str]) -> None:
        if not ids:
            return

        def operacao(documento: gspread.Spreadsheet, aba: gspread.Worksheet) -> None:
            numeros = sorted(
                (numero for lista in self._linhas_do_id(aba, ids).values() for numero in lista),
                reverse=True,  # de baixo para cima: os índices não deslizam
            )
            documento.batch_update(
                body={
                    "requests": [
                        {
                            "deleteDimension": {
                                "range": {
                                    "sheetId": aba.id,
                                    "dimension": "ROWS",
                                    "startIndex": numero - 1,
                                    "endIndex": numero,
                                }
                            }
                        }
                        for numero in numeros
                    ]
                }
            )

        self._escrever(operacao)

    def _linhas_do_id(self, aba: gspread.Worksheet, ids: list[str]) -> dict[str, list[int]]:
        """Números de linha (1 = cabeçalho) de cada `id`, relendo a aba agora.

        Tudo ou nada: se faltar algum `id`, levanta `NaoEncontrado` antes de
        qualquer escrita.
        """
        valores = aba.get_all_values(value_render_option=ValueRenderOption.unformatted)
        encontrados: dict[str, list[int]] = {id_: [] for id_ in ids}
        for numero, linha in enumerate(valores[1:], start=2):
            id_ = str(linha[0]).strip() if linha else ""
            if id_ in encontrados:
                encontrados[id_].append(numero)
        faltando = [id_ for id_, numeros in encontrados.items() if not numeros]
        if faltando:
            raise NaoEncontrado(f"Registro {', '.join(faltando)} não encontrado.")
        return encontrados

    def _intervalo_da_linha(self, numero: int) -> str:
        """`A7:N7`: só as colunas do schema — as extras do usuário ficam como estão."""
        return f"A{numero}:{rowcol_to_a1(numero, len(self.aba.colunas))}"

    def _para_linha(self, item: M) -> list[Any]:
        """Modelo → células: datas e enums como texto, valor como número (`02` §5.4)."""
        dados = item.model_dump(mode="json")
        return ["" if dados[coluna] is None else dados[coluna] for coluna in self.aba.colunas]

    def _escrever(self, operacao: Callable[[gspread.Spreadsheet, gspread.Worksheet], None]) -> None:
        try:
            self._executar(operacao)
        finally:
            # Mesmo se a escrita falhar no meio, o cache não pode servir o antes.
            self._cache.invalidar(self.aba.nome)

    # Acesso à aba ----------------------------------------------------------

    def _executar[R](self, operacao: Callable[[gspread.Spreadsheet, gspread.Worksheet], R]) -> R:
        return self._fonte.executar(lambda documento: operacao(documento, self._aba(documento)))

    def _aba(self, documento: gspread.Spreadsheet) -> gspread.Worksheet:
        """Referência da aba guardada por documento: sem chamada extra a cada operação."""
        if self._referencia is None or self._referencia[0] is not documento:
            self._referencia = (documento, documento.worksheet(self.aba.nome))
        return self._referencia[1]


def _id_de(item: BaseModel) -> str:
    return str(item.id)  # type: ignore[attr-defined]


def _e_numero(valor: Any) -> bool:
    return isinstance(valor, int | float) and not isinstance(valor, bool)


def _motivo(erro: ValidationError) -> str:
    """Primeiro problema da linha, curto: `campo: mensagem`."""
    primeiro = erro.errors()[0]
    campo = ".".join(str(parte) for parte in primeiro["loc"]) or "linha"
    return f"{campo}: {primeiro['msg']}"
