"""Testes de `Settings` (CA-F01.9, CA-F01.10) e da configuração da Pluggy (F-16 §3.1)."""

from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import ConfiguracaoPluggy, Settings, obter_settings

VARIAVEIS = (
    "SPREADSHEET_ID",
    "GOOGLE_CREDENTIALS_PATH",
    "CACHE_TTL_SEGUNDOS",
    "CORS_ORIGINS",
    "SPREADSHEET_ID_TESTE",
    "PLUGGY_CLIENT_ID",
    "PLUGGY_CLIENT_SECRET",
    "PLUGGY_ITEM_IDS",
    "PLUGGY_DATA_INICIAL",
    "PLUGGY_ITEM_ID_TESTE",
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


# Meu Pluggy (F-16 §3.1) ----------------------------------------------------------

SEGREDO = "segredo-inventado-7f3a"


def settings_com(monkeypatch: pytest.MonkeyPatch, **pluggy: str) -> Settings:
    monkeypatch.setenv("SPREADSHEET_ID", "1AbCplanilhaReal")
    for nome, valor in pluggy.items():
        monkeypatch.setenv(f"PLUGGY_{nome.upper()}", valor)
    return Settings(_env_file=None)


def test_configuracao_pluggy_ligada_desligada_incompleta__CA_F16_1(
    ambiente_limpo: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Três vazias → desligada, sem aviso (CA-17.6); três preenchidas → ligada."""
    desligada = settings_com(monkeypatch).pluggy
    assert desligada == ConfiguracaoPluggy(ligada=False, erro=None)

    # Só a data inicial não liga nem gera aviso: as três obrigatórias seguem vazias.
    assert settings_com(monkeypatch, data_inicial="12/11/2026").pluggy == desligada

    ligada = settings_com(
        monkeypatch,
        client_id=" id-1 ",
        client_secret=f" {SEGREDO} ",
        item_ids="itm-1, itm-2",
        data_inicial="2026-10-01",
    ).pluggy
    assert (ligada.ligada, ligada.erro) == (True, None)
    assert ligada.client_id == "id-1"
    assert ligada.client_secret.get_secret_value() == SEGREDO
    assert ligada.item_ids == ("itm-1", "itm-2")
    assert ligada.data_inicial == date(2026, 10, 1)


def test_configuracao_pluggy_sem_data_inicial_e_valida__CA_F16_1(
    ambiente_limpo: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RN-23: sem a variável, quem decide o dia 1º do mês corrente é a importação."""
    configuracao = settings_com(
        monkeypatch, client_id="id-1", client_secret=SEGREDO, item_ids="itm-1"
    ).pluggy

    assert (configuracao.ligada, configuracao.data_inicial) == (True, None)


@pytest.mark.parametrize(
    ("pluggy", "erro"),
    [
        ({"client_id": "id-1"}, "Falta PLUGGY_CLIENT_SECRET no backend/.env."),
        ({"client_secret": SEGREDO}, "Falta PLUGGY_CLIENT_ID no backend/.env."),
        ({"item_ids": "itm-1"}, "Falta PLUGGY_CLIENT_ID no backend/.env."),
        (
            {"client_id": "id-1", "item_ids": "itm-1"},
            "Falta PLUGGY_CLIENT_SECRET no backend/.env.",
        ),
        (
            {"client_id": "id-1", "client_secret": SEGREDO},
            "Falta PLUGGY_ITEM_IDS no backend/.env.",
        ),
        (
            {"client_id": "id-1", "client_secret": SEGREDO, "item_ids": " , ,"},
            "Falta PLUGGY_ITEM_IDS no backend/.env.",
        ),
        (
            {
                "client_id": "id-1",
                "client_secret": SEGREDO,
                "item_ids": "itm-1",
                "data_inicial": "12/11/2026",
            },
            "PLUGGY_DATA_INICIAL deve estar no formato AAAA-MM-DD.",
        ),
        (
            {
                "client_id": "id-1",
                "client_secret": SEGREDO,
                "item_ids": "itm-1",
                "data_inicial": "2026-02-30",
            },
            "PLUGGY_DATA_INICIAL deve estar no formato AAAA-MM-DD.",
        ),
        # A falta de uma obrigatória vem antes da data inválida (F-16 §3.1.3).
        (
            {"client_id": "id-1", "data_inicial": "ontem"},
            "Falta PLUGGY_CLIENT_SECRET no backend/.env.",
        ),
    ],
)
def test_configuracao_pluggy_ligada_desligada_incompleta__CA_F16_2(
    ambiente_limpo: None, monkeypatch: pytest.MonkeyPatch, pluggy: dict[str, str], erro: str
) -> None:
    """Incompleta ou inválida: desligada, com a primeira causa — e o backend sobe do mesmo jeito."""
    configuracao = settings_com(monkeypatch, **pluggy).pluggy

    assert configuracao == ConfiguracaoPluggy(ligada=False, erro=erro)


def test_pluggy_item_ids_sem_espacos_nem_repetidos__CA_F16_1(
    ambiente_limpo: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Borda 27: a ordem do `.env` é mantida."""
    settings = settings_com(monkeypatch, item_ids=" itm-2 ,itm-1,, itm-2 , itm-3")

    assert settings.pluggy_item_ids == ["itm-2", "itm-1", "itm-3"]


def test_segredo_da_pluggy_nao_aparece_em_repr__CA_F16_12(
    ambiente_limpo: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RNF-05: nem `Settings` nem a configuração resolvida mostram o Client Secret."""
    settings = settings_com(monkeypatch, client_id="id-1", client_secret=SEGREDO, item_ids="itm-1")

    for texto in (repr(settings), str(settings), repr(settings.pluggy), settings.model_dump_json()):
        assert SEGREDO not in texto


def test_suite_roda_com_a_pluggy_desligada__CA_F16_1() -> None:
    """`SPECS/02` §8: o `conftest` zera as `PLUGGY_*` — o `.env` real não liga a integração."""
    obter_settings.cache_clear()
    try:
        configuracao = obter_settings().pluggy
    finally:
        obter_settings.cache_clear()

    assert configuracao == ConfiguracaoPluggy(ligada=False, erro=None)
