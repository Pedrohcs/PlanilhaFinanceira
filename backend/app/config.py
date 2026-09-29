"""Configuração da aplicação, lida de `backend/.env` (SPECS/02 §6)."""

from functools import lru_cache
from typing import Annotated

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

ORIGEM_PADRAO = "http://localhost:4200"

MENSAGEM_CONFIGURACAO_INVALIDA = (
    "Configuração inválida do backend: verifique {variaveis}. "
    "Copie backend/.env.example para backend/.env e preencha os valores."
)


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
