"""Ambiente da suíte de integração (`SPECS/features/F-15` §3.2).

Fica fora do `conftest` para os testes unitários poderem importá-lo sem tocar
na rede: de onde vem a planilha de teste (Q5), a trava contra a planilha do app
e a limpeza das linhas que os testes criam.
"""

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from gspread.utils import ValueRenderOption
from pydantic import SecretStr
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from app.infra.schema_planilha import ABA_CATEGORIAS, ABA_LANCAMENTOS, ABA_RECORRENCIAS

VARIAVEL_PLANILHA_TESTE = "SPREADSHEET_ID_TESTE"
PASTA_BACKEND = Path(__file__).resolve().parents[2]
ARQUIVO_ENV = PASTA_BACKEND / ".env"

# Valores do terminal **antes** de o `conftest` raiz trocá-los por falsos. Este
# módulo é importado por ele antes da troca, e uma vez só (o `conftest` pode ser
# carregado de novo com outro nome e já veria os falsos).
SPREADSHEET_ID_DO_AMBIENTE = os.environ.get("SPREADSHEET_ID")
CREDENCIAL_DO_AMBIENTE = os.environ.get("GOOGLE_CREDENTIALS_PATH")

# O `conftest` raiz zera estas variáveis para a suíte padrão nunca ligar a
# integração com a Pluggy; o que havia no terminal fica aqui, só para o teste de
# contrato (`pytest -m pluggy`). O segredo nunca é impresso nem comparado em teste.
VARIAVEIS_PLUGGY = (
    "PLUGGY_CLIENT_ID",
    "PLUGGY_CLIENT_SECRET",
    "PLUGGY_ITEM_IDS",
    "PLUGGY_DATA_INICIAL",
    "PLUGGY_ITEM_ID_TESTE",
)
PLUGGY_DO_AMBIENTE = {variavel: os.environ.get(variavel) for variavel in VARIAVEIS_PLUGGY}

# Tudo o que um teste de integração grava começa com uma destas marcas.
MARCA = "teste-integracao-"
MARCAS = (MARCA, "teste-desempenho-")
# Abas onde os testes gravam e as colunas onde a marca pode estar.
ABAS_MARCADAS = (ABA_LANCAMENTOS, ABA_CATEGORIAS, ABA_RECORRENCIAS)
COLUNAS_MARCADAS = ("id", "descricao", "nome")


def nova_marca() -> str:
    """Prefixo único de um teste: `teste-integracao-<12 hex>` (29 caracteres, cabe num nome)."""
    return f"{MARCA}{uuid4().hex[:12]}"


# Intervalo entre testes: a janela de cota de leituras do Google é de 1 minuto (F-15 §3.2.7).
INTERVALO_DE_COTA_S = 61.0


def segundos_de_espera(fim_do_anterior: float | None, agora: float) -> float:
    """Quanto esperar antes do próximo teste para a janela de cota estar zerada."""
    if fim_do_anterior is None:
        return 0.0
    return max(0.0, INTERVALO_DE_COTA_S - (agora - fim_do_anterior))


MENSAGEM_MESMA_PLANILHA = (
    "SPREADSHEET_ID_TESTE aponta para a mesma planilha do app. Use uma planilha separada."
)


class ArquivoEnv(BaseSettings):
    """Só o `backend/.env`, sem o ambiente: o `conftest` raiz põe um `SPREADSHEET_ID` falso nele."""

    model_config = SettingsConfigDict(
        env_file=ARQUIVO_ENV, env_file_encoding="utf-8", extra="ignore"
    )

    spreadsheet_id: str | None = None
    spreadsheet_id_teste: str | None = None
    pluggy_client_id: str | None = None
    pluggy_client_secret: SecretStr | None = None
    pluggy_item_id_teste: str | None = None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings, dotenv_settings)


def _limpo(valor: str | None) -> str | None:
    return (valor or "").strip() or None


def ler_planilha_teste(ambiente: Mapping[str, str], arquivo_env: Path = ARQUIVO_ENV) -> str | None:
    """ID da planilha de teste: o do terminal tem precedência sobre o do `.env` (Q5)."""
    return _limpo(ambiente.get(VARIAVEL_PLANILHA_TESTE)) or _limpo(
        ArquivoEnv(_env_file=arquivo_env).spreadsheet_id_teste  # type: ignore[call-arg]
    )


@dataclass(frozen=True)
class PluggyDeContrato:
    """O que o teste de contrato precisa: credenciais da aplicação e o item Sandbox."""

    client_id: str
    client_secret: SecretStr
    item_id: str


def ler_pluggy_de_contrato(
    do_terminal: Mapping[str, str | None] = PLUGGY_DO_AMBIENTE, arquivo_env: Path = ARQUIVO_ENV
) -> PluggyDeContrato | None:
    """Credenciais e item Sandbox do terminal ou, sem ele, do `.env`; `None` se faltar algo."""
    arquivo = ArquivoEnv(_env_file=arquivo_env)  # type: ignore[call-arg]
    segredo_do_arquivo = (
        arquivo.pluggy_client_secret.get_secret_value() if arquivo.pluggy_client_secret else None
    )
    client_id = _limpo(do_terminal.get("PLUGGY_CLIENT_ID")) or _limpo(arquivo.pluggy_client_id)
    segredo = _limpo(do_terminal.get("PLUGGY_CLIENT_SECRET")) or _limpo(segredo_do_arquivo)
    item_id = _limpo(do_terminal.get("PLUGGY_ITEM_ID_TESTE")) or _limpo(
        arquivo.pluggy_item_id_teste
    )
    if not (client_id and segredo and item_id):
        return None
    return PluggyDeContrato(client_id, SecretStr(segredo), item_id)


def caminho_da_credencial() -> Path:
    """Caminho da credencial dos testes `integracao` (padrão do `.env.example`).

    Relativo à pasta `backend/`, como no app (`SPECS/02` §6). Só o caminho: quem
    abre o arquivo é o `google-auth`.
    """
    caminho = Path(CREDENCIAL_DO_AMBIENTE or "../credentials.json")
    return caminho if caminho.is_absolute() else PASTA_BACKEND / caminho


def planilhas_do_app(
    spreadsheet_id_do_terminal: str | None, arquivo_env: Path = ARQUIVO_ENV
) -> set[str]:
    """IDs que o app pode estar usando: o do terminal (se havia) e o do `.env`."""
    do_arquivo = ArquivoEnv(_env_file=arquivo_env).spreadsheet_id  # type: ignore[call-arg]
    return {id_ for id_ in (_limpo(spreadsheet_id_do_terminal), _limpo(do_arquivo)) if id_}


def mesma_planilha_do_app(planilha_teste: str, planilhas_do_app: Iterable[str]) -> bool:
    """A trava de §3.2.3: nunca escrever na planilha que guarda os dados do usuário."""
    return planilha_teste.strip() in set(planilhas_do_app)


def _marcada(valor: Any) -> bool:
    return isinstance(valor, str) and valor.startswith(MARCAS)


def _blocos(indices: list[int]) -> list[tuple[int, int]]:
    """Índices de linha (base 0) → intervalos `[início, fim)` contíguos, como a API pede."""
    blocos: list[list[int]] = []
    for indice in indices:
        if blocos and blocos[-1][1] == indice:
            blocos[-1][1] = indice + 1
        else:
            blocos.append([indice, indice + 1])
    return [(inicio, fim) for inicio, fim in blocos]


def apagar_linhas_marcadas(documento: Any) -> int:
    """Apaga, numa única chamada, toda linha com marca de teste em `id`, `descricao` ou `nome`.

    Usada antes e depois da suíte (borda 10, CA-F15.9). Aba que não existe é
    ignorada (planilha ainda sem bootstrap). Devolve quantas linhas apagou.
    """
    abas = {aba.title: aba for aba in documento.worksheets()}
    pedidos: list[dict[str, Any]] = []
    apagadas = 0
    for esquema in ABAS_MARCADAS:
        aba = abas.get(esquema.nome)
        if aba is None:
            continue
        linhas = aba.get_all_values(value_render_option=ValueRenderOption.unformatted)
        if not linhas:
            continue
        colunas = [i for i, nome in enumerate(linhas[0]) if nome in COLUNAS_MARCADAS]
        indices = [
            indice
            for indice, valores in enumerate(linhas)
            if indice > 0 and any(i < len(valores) and _marcada(valores[i]) for i in colunas)
        ]
        apagadas += len(indices)
        # De baixo para cima: apagar um bloco não desloca os que vêm antes.
        pedidos.extend(
            {
                "deleteDimension": {
                    "range": {
                        "sheetId": aba.id,
                        "dimension": "ROWS",
                        "startIndex": inicio,
                        "endIndex": fim,
                    }
                }
            }
            for inicio, fim in reversed(_blocos(indices))
        )
    if pedidos:
        documento.batch_update({"requests": pedidos})
    return apagadas
