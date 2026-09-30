"""Planilha falsa que imita a parte do gspread 6.2 usada pelo app.

Nenhuma chamada de rede. As assinaturas exigem **argumentos nomeados** e as
opções de `SPECS/02` §5.4 (`RAW` na escrita, `INSERT_ROWS` na inserção,
`UNFORMATTED_VALUE` na leitura): um código que esqueça qualquer uma delas
falha no teste, não em produção. Cada escrita fica registrada em `escritas`,
para provar "nada foi alterado", e cada leitura de aba conta em `leituras`,
para provar o uso do cache.
"""

from collections import Counter
from collections.abc import Callable
from typing import Any

from gspread.utils import a1_to_rowcol

ESCRITA_RAW = "RAW"
INSERCAO_DE_LINHAS = "INSERT_ROWS"
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
        self.id = planilha.proximo_id()
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
        self._planilha.leituras[self.title] += 1
        linhas = [list(linha) for linha in self.valores]
        while linhas and all(celula == "" for celula in linhas[-1]):
            linhas.pop()
        largura = max((len(linha) for linha in linhas), default=0)
        return [linha + [""] * (largura - len(linha)) for linha in linhas]

    # Escrita -----------------------------------------------------------------

    def update(self, *, values: list[list[Any]], range_name: str, value_input_option: str) -> None:
        _exigir(value_input_option, ESCRITA_RAW)
        linha_inicial, coluna_inicial = a1_to_rowcol(range_name.split(":")[0])
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

    def append_rows(
        self, *, values: list[list[Any]], value_input_option: str, insert_data_option: str
    ) -> None:
        _exigir(value_input_option, ESCRITA_RAW)
        _exigir(insert_data_option, INSERCAO_DE_LINHAS)
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
        self.leituras: Counter[str] = Counter()
        self.falhar_em: str | None = None  # nome de uma escrita que deve falhar
        self._ultimo_id = 0
        self._abas: dict[str, AbaFalsa] = {}
        for nome, linhas in (abas or {}).items():
            self._abas[nome] = AbaFalsa(self, nome, linhas=linhas)

    def registrar(self, *escrita: Any) -> None:
        """Registra a escrita; `falhar_em` simula resposta perdida depois de aplicar."""
        self.escritas.append(escrita)
        if escrita[0] == self.falhar_em:
            raise RuntimeError(f"falha simulada em {escrita[0]}")

    def proximo_id(self) -> int:
        self._ultimo_id += 1
        return self._ultimo_id

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

    def batch_update(self, body: dict[str, Any]) -> None:
        """Só `deleteDimension` de linhas, aplicado na ordem recebida — como a API."""
        for pedido in body["requests"]:
            intervalo = pedido["deleteDimension"]["range"]
            assert intervalo["dimension"] == "ROWS"
            aba = next(aba for aba in self._abas.values() if aba.id == intervalo["sheetId"])
            del aba.valores[intervalo["startIndex"] : intervalo["endIndex"]]
        self.registrar("batch_update", body)

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


class FonteFalsa:
    """Faz o papel de `ConexaoPlanilha.executar` sobre uma `PlanilhaFalsa`."""

    def __init__(self, planilha: PlanilhaFalsa) -> None:
        self.planilha = planilha
        self.execucoes = 0

    def executar[R](self, operacao: Callable[[Any], R]) -> R:
        self.execucoes += 1
        return operacao(self.planilha)
