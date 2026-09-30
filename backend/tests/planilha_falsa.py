"""Planilha falsa que imita a parte do gspread 6.2 usada pelo app.

Nenhuma chamada de rede. As assinaturas exigem **argumentos nomeados** e as
opções de `SPECS/02` §5.4 (`RAW` na escrita, `UNFORMATTED_VALUE` na leitura):
um código que esqueça qualquer uma delas falha no teste, não em produção.
Cada escrita fica registrada em `escritas`, para provar "nada foi alterado".
"""

from typing import Any

from gspread.utils import a1_to_rowcol

ESCRITA_RAW = "RAW"
LEITURA_CRUA = "UNFORMATTED_VALUE"


class ErroGradeFalsa(Exception):
    """Escrita fora dos limites da grade — a API real também recusa."""


class AbaFalsa:
    def __init__(
        self,
        planilha: "PlanilhaFalsa",
        title: str,
        *,
        linhas: list[list[Any]] | None = None,
        rows: int = 1000,
        cols: int = 26,
    ) -> None:
        self._planilha = planilha
        self.title = title
        self.row_count = rows
        self.col_count = cols
        self.valores: list[list[Any]] = [list(linha) for linha in linhas or []]

    # Leitura -----------------------------------------------------------------

    def row_values(self, row: int, *, value_render_option: str) -> list[Any]:
        _exigir(value_render_option, LEITURA_CRUA)
        if row > len(self.valores):
            return []
        linha = list(self.valores[row - 1])
        while linha and linha[-1] == "":
            linha.pop()  # a API omite células vazias no fim da linha
        return linha

    def get_all_values(self, *, value_render_option: str) -> list[list[Any]]:
        _exigir(value_render_option, LEITURA_CRUA)
        linhas = [list(linha) for linha in self.valores]
        while linhas and all(celula == "" for celula in linhas[-1]):
            linhas.pop()
        largura = max((len(linha) for linha in linhas), default=0)
        return [linha + [""] * (largura - len(linha)) for linha in linhas]

    # Escrita -----------------------------------------------------------------

    def update(self, *, values: list[list[Any]], range_name: str, value_input_option: str) -> None:
        _exigir(value_input_option, ESCRITA_RAW)
        linha_inicial, coluna_inicial = a1_to_rowcol(range_name)
        for deslocamento, linha in enumerate(values):
            indice = linha_inicial - 1 + deslocamento
            ultima_coluna = coluna_inicial - 1 + len(linha)
            if ultima_coluna > self.col_count:
                raise ErroGradeFalsa(f"{self.title}: coluna {ultima_coluna} > {self.col_count}")
            while len(self.valores) <= indice:
                self.valores.append([])
            atual = self.valores[indice]
            atual.extend([""] * (ultima_coluna - len(atual)))
            atual[coluna_inicial - 1 : ultima_coluna] = list(linha)
        self._planilha.registrar("update", self.title, range_name, values)

    def append_rows(self, *, values: list[list[Any]], value_input_option: str) -> None:
        _exigir(value_input_option, ESCRITA_RAW)
        while self.valores and all(celula == "" for celula in self.valores[-1]):
            self.valores.pop()
        self.valores.extend(list(linha) for linha in values)
        self._planilha.registrar("append_rows", self.title, values)

    def add_cols(self, cols: int) -> None:
        self.col_count += cols
        self._planilha.registrar("add_cols", self.title, cols)


class PlanilhaFalsa:
    """Documento com abas em memória: `{nome: [linhas]}`."""

    def __init__(self, abas: dict[str, list[list[Any]]] | None = None) -> None:
        self.escritas: list[tuple[Any, ...]] = []
        self._abas: dict[str, AbaFalsa] = {}
        for nome, linhas in (abas or {}).items():
            self._abas[nome] = AbaFalsa(self, nome, linhas=linhas)

    def registrar(self, *escrita: Any) -> None:
        self.escritas.append(escrita)

    def worksheets(self) -> list[AbaFalsa]:
        return list(self._abas.values())

    def worksheet(self, title: str) -> AbaFalsa:
        return self._abas[title]

    def add_worksheet(self, *, title: str, rows: int, cols: int) -> AbaFalsa:
        if title in self._abas:
            raise ValueError(f"aba {title} já existe")
        aba = AbaFalsa(self, title, rows=rows, cols=cols)
        self._abas[title] = aba
        self.registrar("add_worksheet", title, rows, cols)
        return aba

    # Atalhos para as asserções dos testes ------------------------------------

    def nomes_das_abas(self) -> list[str]:
        return list(self._abas)

    def linhas(self, title: str) -> list[list[Any]]:
        """Linhas não vazias da aba, sem as células vazias do fim."""
        return [
            linha
            for linha in (
                self._abas[title].row_values(numero, value_render_option=LEITURA_CRUA)
                for numero in range(1, len(self._abas[title].valores) + 1)
            )
            if linha
        ]


def _exigir(recebido: str, esperado: str) -> None:
    if recebido != esperado:
        raise AssertionError(f"opção {recebido!r} usada; `SPECS/02` §5.4 exige {esperado!r}")
