"""Testes de `Settings` (CA-F01.9, CA-F01.10)."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings, obter_settings

VARIAVEIS = (
    "SPREADSHEET_ID",
    "GOOGLE_CREDENTIALS_PATH",
    "CACHE_TTL_SEGUNDOS",
    "CORS_ORIGINS",
    "SPREADSHEET_ID_TESTE",
)


@pytest.fixture
def ambiente_limpo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove as variáveis de `02` §6 para isolar o teste do ambiente."""
    for variavel in VARIAVEIS:
        monkeypatch.delenv(variavel, raising=False)


def test_settings_le_env__CA_F01_9(ambiente_limpo: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cada campo recebe o valor definido no ambiente."""
    monkeypatch.setenv("SPREADSHEET_ID", "1AbCplanilhaReal")
    monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", "C:/chaves/conta-servico.json")
    monkeypatch.setenv("CACHE_TTL_SEGUNDOS", "90")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:4300")
    monkeypatch.setenv("SPREADSHEET_ID_TESTE", "1XyZplanilhaTeste")

    settings = Settings(_env_file=None)

    assert settings.spreadsheet_id == "1AbCplanilhaReal"
    assert settings.google_credentials_path == "C:/chaves/conta-servico.json"
    assert settings.cache_ttl_segundos == 90
    assert settings.cors_origins == ["http://localhost:4300"]
    assert settings.spreadsheet_id_teste == "1XyZplanilhaTeste"


def test_settings_aplica_padroes__CA_F01_9(
    ambiente_limpo: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Com apenas `SPREADSHEET_ID`, os padrões de `02` §6 valem."""
    monkeypatch.setenv("SPREADSHEET_ID", "1AbCplanilhaReal")

    settings = Settings(_env_file=None)

    assert settings.google_credentials_path == "../credentials.json"
    assert settings.cache_ttl_segundos == 30
    assert settings.cors_origins == ["http://localhost:4200"]
    assert settings.spreadsheet_id_teste is None


def test_cors_origins_aceita_lista__CA_F01_9(
    ambiente_limpo: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mais de uma origem, separada por vírgula, vira `list[str]` (borda 11)."""
    monkeypatch.setenv("SPREADSHEET_ID", "1AbCplanilhaReal")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:4200, http://127.0.0.1:4200")

    settings = Settings(_env_file=None)

    assert settings.cors_origins == ["http://localhost:4200", "http://127.0.0.1:4200"]


def test_settings_exige_spreadsheet_id__CA_F01_10(ambiente_limpo: None) -> None:
    """Sem `SPREADSHEET_ID` a configuração falha citando a variável."""
    with pytest.raises(ValidationError) as erro:
        Settings(_env_file=None)

    assert "spreadsheet_id" in str(erro.value).lower()


def test_obter_settings_mensagem_em_portugues__CA_F01_10(
    ambiente_limpo: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Na inicialização o erro sai em pt-BR, citando a variável (F-01 §7)."""
    monkeypatch.chdir(tmp_path)  # garante que nenhum .env real seja lido
    obter_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError) as erro:
            obter_settings()
    finally:
        obter_settings.cache_clear()

    assert "SPREADSHEET_ID" in str(erro.value)
    assert "backend/.env" in str(erro.value)
