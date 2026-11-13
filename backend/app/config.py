"""Configuração da aplicação, lida de `backend/.env` (SPECS/02 §6)."""

import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from typing import Annotated

from pydantic import Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

ORIGEM_PADRAO = "http://localhost:4200"

MENSAGEM_CONFIGURACAO_INVALIDA = (
    "Configuração inválida do backend: verifique {variaveis}. "
    "Copie backend/.env.example para backend/.env e preencha os valores."
)


_DATA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# F-16 §3.1.3: a primeira causa, nesta ordem.
FALTA_PLUGGY_CLIENT_ID = "Falta PLUGGY_CLIENT_ID no backend/.env."
FALTA_PLUGGY_CLIENT_SECRET = "Falta PLUGGY_CLIENT_SECRET no backend/.env."
FALTA_PLUGGY_ITEM_IDS = "Falta PLUGGY_ITEM_IDS no backend/.env."
PLUGGY_DATA_INICIAL_INVALIDA = "PLUGGY_DATA_INICIAL deve estar no formato AAAA-MM-DD."


@dataclass(frozen=True)
class ConfiguracaoPluggy:
    """Integração com o Meu Pluggy como ficou configurada (`SPECS/02` §6; F-16 §3.1).

    `ligada` só com as três variáveis obrigatórias preenchidas e a data inicial
    vazia ou válida. Com as três vazias, desligada e sem `erro`. Qualquer outro
    caso: desligada, com a primeira causa em `erro`. O segredo fica em
    `SecretStr`: não aparece em `repr` nem em log (RNF-05).
    """

    ligada: bool
    erro: str | None = None
    client_id: str = ""
    client_secret: SecretStr = SecretStr("")
    item_ids: tuple[str, ...] = ()
    data_inicial: date | None = None


def _data_iso(texto: str) -> date | None:
    if not _DATA_ISO.fullmatch(texto):
        return None
    try:
        return date.fromisoformat(texto)
    except ValueError:
        return None


class Settings(BaseSettings):
    """Variáveis de configuração do backend.

    O caminho da credencial é apenas guardado — nem o arquivo nem seu
    conteúdo são lidos aqui (RNF-05); isso acontece em T-004.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    spreadsheet_id: str = Field(min_length=1)
    google_credentials_path: str = "../credentials.json"
    cache_ttl_segundos: int = Field(default=30, gt=0)
    cors_origins: Annotated[list[str], NoDecode] = [ORIGEM_PADRAO]
    spreadsheet_id_teste: str | None = None

    # Meu Pluggy (F-16). Nada aqui é obrigatório nem impede o backend de subir:
    # o que estiver errado aparece em `pluggy.erro`.
    pluggy_client_id: str = ""
    pluggy_client_secret: SecretStr = SecretStr("")
    pluggy_item_ids: Annotated[list[str], NoDecode] = []
    pluggy_data_inicial: str = ""
    pluggy_item_id_teste: str | None = None

    @field_validator("pluggy_client_id", "pluggy_data_inicial", mode="before")
    @classmethod
    def _aparar(cls, valor: object) -> object:
        return valor.strip() if isinstance(valor, str) else valor

    @field_validator("pluggy_client_secret", mode="before")
    @classmethod
    def _aparar_segredo(cls, valor: object) -> object:
        return valor.strip() if isinstance(valor, str) else valor

    @field_validator("pluggy_item_ids", mode="before")
    @classmethod
    def _separar_itens(cls, valor: object) -> object:
        """Separados por vírgula; espaços e repetidos descartados, mantendo a ordem."""
        if isinstance(valor, str):
            itens = [item.strip() for item in valor.split(",")]
            return list(dict.fromkeys(item for item in itens if item))
        return valor

    @property
    def pluggy(self) -> ConfiguracaoPluggy:
        """Ligada, desligada ou incompleta (F-16 §3.1)."""
        segredo = self.pluggy_client_secret.get_secret_value()
        if not (self.pluggy_client_id or segredo or self.pluggy_item_ids):
            return ConfiguracaoPluggy(ligada=False)
        data_inicial = _data_iso(self.pluggy_data_inicial) if self.pluggy_data_inicial else None
        if not self.pluggy_client_id:
            erro = FALTA_PLUGGY_CLIENT_ID
        elif not segredo:
            erro = FALTA_PLUGGY_CLIENT_SECRET
        elif not self.pluggy_item_ids:
            erro = FALTA_PLUGGY_ITEM_IDS
        elif self.pluggy_data_inicial and data_inicial is None:
            erro = PLUGGY_DATA_INICIAL_INVALIDA
        else:
            return ConfiguracaoPluggy(
                ligada=True,
                client_id=self.pluggy_client_id,
                client_secret=self.pluggy_client_secret,
                item_ids=tuple(self.pluggy_item_ids),
                data_inicial=data_inicial,
            )
        return ConfiguracaoPluggy(ligada=False, erro=erro)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _separar_origens(cls, valor: object) -> object:
        """Aceita uma lista ou várias origens separadas por vírgula."""
        if isinstance(valor, str):
            return [origem.strip() for origem in valor.split(",") if origem.strip()]
        return valor


@lru_cache
def obter_settings() -> Settings:
    """Devolve a instância única de `Settings`, criada na primeira chamada.

    A criação é preguiçosa de propósito: importar o módulo não exige um
    `.env` configurado. Configuração faltando vira mensagem em português
    citando a variável de ambiente.
    """
    try:
        return Settings()
    except ValidationError as erro:
        variaveis = ", ".join(
            str(detalhe["loc"][0]).upper() if detalhe["loc"] else "(configuração)"
            for detalhe in erro.errors()
        )
        raise RuntimeError(MENSAGEM_CONFIGURACAO_INVALIDA.format(variaveis=variaveis)) from erro
