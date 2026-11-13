"""Cliente da Pluggy (`SPECS/02` §11; F-16 CA-F16.8 a CA-F16.12).

Tudo com `httpx.MockTransport`: nenhuma chamada de rede. O segredo e a `apiKey`
usados aqui são inventados — o teste de vazamento procura exatamente por eles.
"""

import logging
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest

from app.api.erros import status_de
from app.domain.enums import SituacaoConexao
from app.domain.erros import (
    ErroPlanilha,
    ImportacaoEmAndamento,
    PluggyCredenciaisInvalidas,
    PluggyIndisponivel,
    PluggyNaoConfigurada,
)
from app.domain.pluggy import CartaoPluggy, ConexaoPluggy, TransacaoPluggy
from app.infra.pluggy_client import PluggyClient, calcular_espera
from app.services.importacao_service import FontePluggy

CLIENT_ID = "id-de-teste"
SEGREDO = "segredo-inventado-7f3a"
CHAVE = "apikey-inventada-91bc"
AGORA = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)

Resposta = httpx.Response | Callable[[httpx.Request], httpx.Response]


class PluggyDeMentira:
    """Servidor falso: respostas em fila por `MÉTODO /caminho`; a última se repete."""

    def __init__(self) -> None:
        self.requisicoes: list[httpx.Request] = []
        self.chaves_emitidas = 0
        self._filas: dict[str, list[Resposta]] = {}

    def responder(self, rota: str, *respostas: Resposta) -> None:
        self._filas[rota] = list(respostas)

    def __call__(self, requisicao: httpx.Request) -> httpx.Response:
        self.requisicoes.append(requisicao)
        rota = f"{requisicao.method} {requisicao.url.path}"
        if rota not in self._filas and rota == "POST /auth":
            self.chaves_emitidas += 1
            return httpx.Response(200, json={"apiKey": f"{CHAVE}-{self.chaves_emitidas}"})
        fila = self._filas[rota]
        resposta = fila.pop(0) if len(fila) > 1 else fila[0]
        return resposta(requisicao) if callable(resposta) else resposta

    def chamadas(self, rota: str) -> list[httpx.Request]:
        return [r for r in self.requisicoes if f"{r.method} {r.url.path}" == rota]


class Relogio:
    def __init__(self) -> None:
        self.segundos = 1000.0

    def __call__(self) -> float:
        return self.segundos


@pytest.fixture
def servidor() -> PluggyDeMentira:
    return PluggyDeMentira()


@pytest.fixture
def relogio() -> Relogio:
    return Relogio()


@pytest.fixture
def esperas() -> list[float]:
    return []


@pytest.fixture
def cliente(servidor: PluggyDeMentira, relogio: Relogio, esperas: list[float]) -> PluggyClient:
    return PluggyClient(
        CLIENT_ID,
        SEGREDO,
        transporte=httpx.MockTransport(servidor),
        dormir=esperas.append,
        relogio=relogio,
        agora=lambda: AGORA,
    )


def item(**campos: Any) -> httpx.Response:
    corpo: dict[str, Any] = {
        "id": "itm-9",
        "status": "UPDATED",
        "executionStatus": "SUCCESS",
        "lastUpdatedAt": "2026-11-13T06:10:00.000Z",
        "consentExpiresAt": "2027-10-30T12:00:00.000Z",
        "connector": {"id": 200, "name": "Nubank"},
    }
    corpo.update(campos)
    return httpx.Response(200, json=corpo)


def transacao(id_: str, **campos: Any) -> dict[str, Any]:
    corpo: dict[str, Any] = {
        "id": id_,
        "description": f"Compra {id_}",
        "amount": 59.9,
        "currencyCode": "BRL",
        "date": "2026-11-12T01:30:00.000Z",
        "status": "POSTED",
    }
    corpo.update(campos)
    return corpo


def pagina(*transacoes: dict[str, Any], proxima: str | None = None) -> httpx.Response:
    return httpx.Response(200, json={"results": list(transacoes), "next": proxima})


# Autenticação (CA-F16.8, CA-F16.9) -----------------------------------------------


def test_pluggy_client_autentica_uma_vez_e_guarda_a_chave__CA_F16_8(
    cliente: PluggyClient, servidor: PluggyDeMentira, relogio: Relogio
) -> None:
    """Duas chamadas de dados em menos de 1 h 50 min: um só `POST /auth`."""
    servidor.responder("GET /items/itm-9", item())

    cliente.obter_conexao("itm-9")
    relogio.segundos += 109 * 60
    cliente.obter_conexao("itm-9")

    assert len(servidor.chamadas("POST /auth")) == 1
    corpo = servidor.chamadas("POST /auth")[0].read()
    assert CLIENT_ID.encode() in corpo and SEGREDO.encode() in corpo  # clientId/clientSecret
    assert [r.headers["X-API-KEY"] for r in servidor.chamadas("GET /items/itm-9")] == [
        f"{CHAVE}-1",
        f"{CHAVE}-1",
    ]
    assert "X-API-KEY" not in servidor.chamadas("POST /auth")[0].headers


def test_pluggy_client_nao_autentica_ao_ser_criado__CA_F16_8(servidor: PluggyDeMentira) -> None:
    """F-16 §3.1.4: a `apiKey` só é pedida na primeira necessidade."""
    PluggyClient(CLIENT_ID, SEGREDO, transporte=httpx.MockTransport(servidor))

    assert servidor.requisicoes == []


def test_pluggy_client_renova_a_chave_com_1h50__CA_F16_8(
    cliente: PluggyClient, servidor: PluggyDeMentira, relogio: Relogio
) -> None:
    servidor.responder("GET /items/itm-9", item())

    cliente.obter_conexao("itm-9")
    relogio.segundos += 110 * 60
    cliente.obter_conexao("itm-9")

    assert len(servidor.chamadas("POST /auth")) == 2
    assert servidor.chamadas("GET /items/itm-9")[-1].headers["X-API-KEY"] == f"{CHAVE}-2"


def test_pluggy_client_401_renova_e_repete_uma_vez__CA_F16_8(
    cliente: PluggyClient, servidor: PluggyDeMentira
) -> None:
    """`401` numa chamada de dados: nova autenticação e **uma** nova tentativa."""
    servidor.responder("GET /items/itm-9", httpx.Response(401), item())

    conexao = cliente.obter_conexao("itm-9")

    assert conexao.situacao is SituacaoConexao.OK
    assert len(servidor.chamadas("POST /auth")) == 2
    assert [r.headers["X-API-KEY"] for r in servidor.chamadas("GET /items/itm-9")] == [
        f"{CHAVE}-1",
        f"{CHAVE}-2",
    ]


def test_pluggy_client_401_repetido_nao_entra_em_laco__CA_F16_8(
    cliente: PluggyClient, servidor: PluggyDeMentira, esperas: list[float]
) -> None:
    servidor.responder("GET /items/itm-9", httpx.Response(401))

    with pytest.raises(PluggyIndisponivel):
        cliente.obter_conexao("itm-9")

    assert len(servidor.chamadas("GET /items/itm-9")) == 2
    assert esperas == []  # 401 não é falha transitória


@pytest.mark.parametrize("status", [401, 403])
def test_pluggy_client_credenciais_invalidas__CA_F16_9(
    cliente: PluggyClient, servidor: PluggyDeMentira, esperas: list[float], status: int
) -> None:
    """`POST /auth` → 401/403: erro imediato, sem novas tentativas → 502 na API."""
    servidor.responder("POST /auth", httpx.Response(status, json={"message": "Unauthorized"}))

    with pytest.raises(PluggyCredenciaisInvalidas) as erro:
        cliente.obter_conexao("itm-9")

    assert erro.value.codigo == "PLUGGY_CREDENCIAIS_INVALIDAS"
    assert erro.value.mensagem == (
        "Client ID ou Client Secret da Pluggy inválidos. Confira o backend/.env."
    )
    assert status_de(erro.value.codigo) == 502
    assert len(servidor.chamadas("POST /auth")) == 1
    assert esperas == []


def test_pluggy_client_auth_sem_chave_na_resposta__CA_F16_9(
    cliente: PluggyClient, servidor: PluggyDeMentira
) -> None:
    servidor.responder("POST /auth", httpx.Response(200, json={"outra": "coisa"}))

    with pytest.raises(PluggyIndisponivel):
        cliente.obter_conexao("itm-9")


# Tentativas (CA-F16.9; `02` §11.5) -----------------------------------------------


def test_pluggy_client_429_nas_quatro_tentativas__CA_F16_9(
    cliente: PluggyClient, servidor: PluggyDeMentira, esperas: list[float]
) -> None:
    servidor.responder("GET /accounts", httpx.Response(429, json={"code": 429}))

    with pytest.raises(PluggyIndisponivel) as erro:
        cliente.listar_cartoes("itm-9")

    assert erro.value.codigo == "PLUGGY_INDISPONIVEL"
    assert erro.value.mensagem == "Meu Pluggy indisponível no momento. Tente novamente mais tarde."
    assert status_de(erro.value.codigo) == 502
    assert len(servidor.chamadas("GET /accounts")) == 4
    assert len(esperas) == 3
    assert [2 <= esperas[0] < 3, 4 <= esperas[1] < 5, 8 <= esperas[2] < 9] == [True] * 3


@pytest.mark.parametrize("falha", [500, 502, 503, 504, "timeout", "rede"])
def test_pluggy_client_falha_transitoria_e_recuperada__CA_F16_9(
    cliente: PluggyClient, servidor: PluggyDeMentira, esperas: list[float], falha: int | str
) -> None:
    def quebrar(requisicao: httpx.Request) -> httpx.Response:
        if falha == "timeout":
            raise httpx.ReadTimeout("tempo esgotado", request=requisicao)
        if falha == "rede":
            raise httpx.ConnectError("sem rede", request=requisicao)
        return httpx.Response(int(falha))

    servidor.responder("GET /items/itm-9", quebrar, quebrar, item())

    conexao = cliente.obter_conexao("itm-9")

    assert conexao.situacao is SituacaoConexao.OK
    assert len(servidor.chamadas("GET /items/itm-9")) == 3
    assert len(esperas) == 2


@pytest.mark.parametrize("status", [400, 403, 404, 422])
def test_pluggy_client_demais_4xx_falham_na_hora__CA_F16_9(
    cliente: PluggyClient, servidor: PluggyDeMentira, esperas: list[float], status: int
) -> None:
    servidor.responder("GET /accounts", httpx.Response(status, json={"message": "x"}))

    with pytest.raises(PluggyIndisponivel):
        cliente.listar_cartoes("itm-9")

    assert len(servidor.chamadas("GET /accounts")) == 1
    assert esperas == []


def test_pluggy_client_resposta_que_nao_e_json__CA_F16_9(
    cliente: PluggyClient, servidor: PluggyDeMentira
) -> None:
    servidor.responder("GET /accounts", httpx.Response(200, text="<html>manutenção</html>"))

    with pytest.raises(PluggyIndisponivel):
        cliente.listar_cartoes("itm-9")


def test_espera_respeita_o_rate_limit_reset_e_o_teto() -> None:
    """`min(RateLimit-Reset, 2^n + aleatório, 16 s)` (`02` §11.5)."""
    assert calcular_espera(1, "1") == 1.0
    assert 2 <= calcular_espera(1, "60") < 3
    assert 2 <= calcular_espera(1, "não é número") < 3
    assert 2 <= calcular_espera(1, "-5") < 3
    assert calcular_espera(4) == calcular_espera(9) == 16.0


def test_falha_da_pluggy_nao_e_falha_da_planilha__RNF_09() -> None:
    """502, e nunca o 503 que aciona o banner da planilha (`02` §11.6)."""
    for erro in (PluggyCredenciaisInvalidas(), PluggyIndisponivel(), PluggyNaoConfigurada()):
        assert not isinstance(erro, ErroPlanilha)
    assert status_de("PLUGGY_NAO_CONFIGURADA") == status_de("IMPORTACAO_EM_ANDAMENTO") == 409
    assert PluggyNaoConfigurada().mensagem == (
        "Integração com o Meu Pluggy não configurada. Preencha PLUGGY_CLIENT_ID, "
        "PLUGGY_CLIENT_SECRET e PLUGGY_ITEM_IDS no backend/.env."
    )
    assert ImportacaoEmAndamento().mensagem == "Já existe uma busca nos cartões em andamento."


# Transações (CA-F16.10; `02` §11.3–11.4) -----------------------------------------


def test_pluggy_client_tres_paginas_na_ordem__CA_F16_10(
    cliente: PluggyClient, servidor: PluggyDeMentira
) -> None:
    """O `next` de cada página é a query string da seguinte; para no `next: null`."""
    servidor.responder(
        "GET /v2/transactions",
        pagina(transacao("t1"), transacao("t2"), proxima="?accountId=acc-1&after=cursor%2F1"),
        pagina(transacao("t3"), proxima="?accountId=acc-1&after=cursor%2F2"),
        pagina(transacao("t4")),
    )

    transacoes = cliente.listar_transacoes("acc-1", date(2026, 10, 1))

    assert [t.id for t in transacoes] == ["t1", "t2", "t3", "t4"]
    chamadas = servidor.chamadas("GET /v2/transactions")
    assert [dict(r.url.params) for r in chamadas] == [
        {"accountId": "acc-1", "dateFrom": "2026-10-01"},  # sem `dateTo` (RN-23)
        {"accountId": "acc-1", "after": "cursor/1"},
        {"accountId": "acc-1", "after": "cursor/2"},
    ]
    assert str(chamadas[1].url).endswith("?accountId=acc-1&after=cursor%2F1")  # usado como veio
    assert len(servidor.chamadas("POST /auth")) == 1


def test_pluggy_client_cursor_repetido_ou_fora_do_formato__CA_F16_10(
    cliente: PluggyClient, servidor: PluggyDeMentira
) -> None:
    servidor.responder("GET /v2/transactions", pagina(transacao("t1"), proxima="?after=igual"))
    with pytest.raises(PluggyIndisponivel):
        cliente.listar_transacoes("acc-1", date(2026, 10, 1))
    assert len(servidor.chamadas("GET /v2/transactions")) == 2

    servidor.responder("GET /v2/transactions", pagina(transacao("t1"), proxima="cursor-solto"))
    with pytest.raises(PluggyIndisponivel):
        cliente.listar_transacoes("acc-1", date(2026, 10, 1))


def test_pluggy_client_le_os_campos_da_transacao__RN_18(
    cliente: PluggyClient, servidor: PluggyDeMentira
) -> None:
    """Campos de `02` §11.4, crus: o mapeamento para lançamento é da importação."""
    servidor.responder(
        "GET /v2/transactions",
        pagina(
            transacao(
                "t1",
                description="  LOJA X PARC 03/10 ",
                amount=120,
                amountInAccountCurrency=650.37,
                currencyCode="USD",
                providerId="prov-1",
                operationType="OUTROS",
                status="PENDING",
                creditCardMetadata={"installmentNumber": 3, "totalInstallments": 10},
            ),
            transacao("t2", amount=-59.9, operationType="ESTORNO", description=None),
            transacao("t3", amount=0.1, creditCardMetadata=None, providerId=None),
        ),
    )

    t1, t2, t3 = cliente.listar_transacoes("acc-1", date(2026, 10, 1))

    assert t1 == TransacaoPluggy(
        id="t1",
        instante=datetime(2026, 11, 12, 1, 30, tzinfo=UTC),
        valor=Decimal("120"),
        descricao="LOJA X PARC 03/10",
        provider_id="prov-1",
        valor_na_moeda_da_conta=Decimal("650.37"),
        moeda="USD",
        tipo_operacao="OUTROS",
        status="PENDING",
        parcela_numero=3,
        parcela_total=10,
    )
    assert (t2.valor, t2.tipo_operacao, t2.descricao) == (Decimal("-59.9"), "ESTORNO", "")
    assert (t3.valor, t3.provider_id, t3.parcela_numero, t3.parcela_total) == (
        Decimal("0.1"),
        None,
        None,
        None,
    )
    assert t3.valor_na_moeda_da_conta is None


@pytest.mark.parametrize(
    "quebrada",
    [
        transacao("t1", date=None),
        transacao("t1", date="ontem"),
        transacao("t1", amount=None),
        transacao("t1", amount="abc"),
        transacao(""),
        "não é objeto",
    ],
)
def test_pluggy_client_transacao_fora_do_formato__CA_F16_9(
    cliente: PluggyClient, servidor: PluggyDeMentira, quebrada: Any
) -> None:
    """Resposta que o app não sabe ler → `PluggyIndisponivel` (`02` §11.6), nada pela metade."""
    servidor.responder("GET /v2/transactions", pagina(transacao("ok"), quebrada))

    with pytest.raises(PluggyIndisponivel):
        cliente.listar_transacoes("acc-1", date(2026, 10, 1))


# Cartões (`02` §11.3–11.4) --------------------------------------------------------


def test_pluggy_client_lista_so_cartoes_de_credito_de_todas_as_paginas(
    cliente: PluggyClient, servidor: PluggyDeMentira
) -> None:
    def conta(id_: str, subtype: str, number: Any, name: str = "Ultravioleta") -> dict[str, Any]:
        return {"id": id_, "type": "CREDIT", "subtype": subtype, "number": number, "name": name}

    servidor.responder(
        "GET /accounts",
        httpx.Response(
            200,
            json={
                "page": 1,
                "totalPages": 2,
                "results": [
                    conta("acc-1", "CREDIT_CARD", "5234 **** **** 0123"),
                    conta("acc-x", "CHECKING_ACCOUNT", "0001/12345-6"),
                ],
            },
        ),
        httpx.Response(
            200,
            json={"page": 2, "totalPages": 2, "results": [conta("acc-2", "CREDIT_CARD", None)]},
        ),
    )

    cartoes = cliente.listar_cartoes("itm-9")

    assert cartoes == [
        CartaoPluggy(id="acc-1", nome="Ultravioleta", final="0123"),
        CartaoPluggy(id="acc-2", nome="Ultravioleta", final=None),
    ]
    assert [dict(r.url.params) for r in servidor.chamadas("GET /accounts")] == [
        {"itemId": "itm-9", "type": "CREDIT", "page": "1"},
        {"itemId": "itm-9", "type": "CREDIT", "page": "2"},
    ]


# Conexões (CA-F16.11; `02` §11.4) --------------------------------------------------


def test_pluggy_client_conexao_inexistente_sem_excecao__CA_F16_11(
    cliente: PluggyClient, servidor: PluggyDeMentira
) -> None:
    servidor.responder("GET /items/errado", httpx.Response(404, json={"code": 404}))

    conexao = cliente.obter_conexao("errado")

    assert conexao == ConexaoPluggy(item_id="errado", situacao=SituacaoConexao.NAO_ENCONTRADA)
    assert conexao.situacao.importa is False


def test_pluggy_client_le_os_campos_da_conexao__CA_F16_11(
    cliente: PluggyClient, servidor: PluggyDeMentira
) -> None:
    servidor.responder("GET /items/itm-9", item())

    assert cliente.obter_conexao("itm-9") == ConexaoPluggy(
        item_id="itm-9",
        situacao=SituacaoConexao.OK,
        banco="Nubank",
        ultima_atualizacao=datetime(2026, 11, 13, 3, 10),  # UTC−3, sem fuso
        autorizacao_expira_em=date(2027, 10, 30),
        aviso_validade=False,
    )


@pytest.mark.parametrize(
    ("campos", "situacao"),
    [
        ({"status": "UPDATED"}, SituacaoConexao.OK),
        ({"status": "UPDATED", "executionStatus": "PARTIAL_SUCCESS"}, SituacaoConexao.PARCIAL),
        ({"status": "UPDATING"}, SituacaoConexao.ATUALIZANDO),
        ({"status": "WAITING_USER_INPUT"}, SituacaoConexao.ATUALIZANDO),
        ({"status": "OUTDATED"}, SituacaoConexao.DESATUALIZADA),
        ({"status": "LOGIN_ERROR"}, SituacaoConexao.ERRO_LOGIN),
        ({"status": "ALGO_NOVO"}, SituacaoConexao.DESATUALIZADA),
        # A validade vem antes do status: vencida, as leituras voltam vazias (RN-24).
        (
            {"status": "UPDATED", "consentExpiresAt": "2026-11-12T12:00:00.000Z"},
            SituacaoConexao.AUTORIZACAO_VENCIDA,
        ),
        (
            {"status": "LOGIN_ERROR", "consentExpiresAt": "2026-11-13T12:00:00.000Z"},
            SituacaoConexao.AUTORIZACAO_VENCIDA,
        ),
        ({"status": "UPDATED", "consentExpiresAt": None}, SituacaoConexao.OK),
    ],
)
def test_pluggy_client_situacao_da_conexao__CA_F16_11(
    cliente: PluggyClient,
    servidor: PluggyDeMentira,
    campos: dict[str, Any],
    situacao: SituacaoConexao,
) -> None:
    servidor.responder("GET /items/itm-9", item(**campos))

    assert cliente.obter_conexao("itm-9").situacao is situacao


@pytest.mark.parametrize(
    ("expira_em", "aviso"),
    [
        (AGORA - timedelta(days=1), True),  # ontem: vencida, e avisa
        (AGORA + timedelta(days=1), True),
        (AGORA + timedelta(days=30), True),
        (AGORA + timedelta(days=30, seconds=1), False),
        (AGORA + timedelta(days=31), False),
        (None, False),
    ],
)
def test_pluggy_client_aviso_de_validade_a_30_dias__CA_F16_11(
    cliente: PluggyClient, servidor: PluggyDeMentira, expira_em: datetime | None, aviso: bool
) -> None:
    """CA-20.1: avisa com 30 dias ou menos; com 31, não."""
    texto = expira_em.isoformat().replace("+00:00", "Z") if expira_em else None
    servidor.responder("GET /items/itm-9", item(consentExpiresAt=texto))

    assert cliente.obter_conexao("itm-9").aviso_validade is aviso


def test_pluggy_client_item_sem_campos_opcionais__CA_F16_11(
    cliente: PluggyClient, servidor: PluggyDeMentira
) -> None:
    servidor.responder("GET /items/itm-9", httpx.Response(200, json={"status": "UPDATED"}))

    assert cliente.obter_conexao("itm-9") == ConexaoPluggy(
        item_id="itm-9", situacao=SituacaoConexao.OK
    )


# Contrato e segredos ---------------------------------------------------------------


def test_pluggy_client_implementa_a_fonte_da_importacao(cliente: PluggyClient) -> None:
    """`SPECS/03` §4.2: a importação recebe o cliente pelo Protocol `FontePluggy`."""
    fonte: FontePluggy = cliente  # conferido pelo tipo; abaixo, pelos nomes

    for metodo in ("obter_conexao", "listar_cartoes", "listar_transacoes"):
        assert callable(getattr(fonte, metodo))
        assert hasattr(FontePluggy, metodo)


def test_pluggy_client_nao_vaza_segredo_nem_chave__CA_F16_12(
    cliente: PluggyClient, servidor: PluggyDeMentira, caplog: pytest.LogCaptureFixture
) -> None:
    """RNF-05: nem log (em DEBUG, todos os loggers), nem mensagem, nem `repr` de exceção."""
    textos: list[str] = []

    def tentar(acao: Callable[[], Any]) -> None:
        try:
            acao()
        except Exception as erro:  # noqa: BLE001 — qualquer exceção entra na conferência
            atual: BaseException | None = erro
            while atual is not None:
                textos.extend([str(atual), repr(atual), str(getattr(atual, "mensagem", ""))])
                atual = atual.__cause__ or atual.__context__

    with caplog.at_level(logging.DEBUG):
        servidor.responder("GET /items/itm-9", item())
        servidor.responder("GET /v2/transactions", pagina(transacao("t1")))
        tentar(lambda: cliente.obter_conexao("itm-9"))  # caminho feliz
        tentar(lambda: cliente.listar_transacoes("acc-1", date(2026, 10, 1)))
        servidor.responder("GET /accounts", httpx.Response(500))
        tentar(lambda: cliente.listar_cartoes("itm-9"))  # tentativas esgotadas
        servidor.responder("GET /accounts", httpx.Response(400, json={"message": SEGREDO}))
        tentar(lambda: cliente.listar_cartoes("itm-9"))  # corpo de erro nunca é logado
        servidor.responder("GET /items/itm-9", httpx.Response(401))
        tentar(lambda: cliente.obter_conexao("itm-9"))  # 401 → renova → 401
        servidor.responder("POST /auth", httpx.Response(401, json={"message": SEGREDO}))
        outro = PluggyClient(CLIENT_ID, SEGREDO, transporte=httpx.MockTransport(servidor))
        tentar(lambda: outro.obter_conexao("itm-9"))  # credenciais recusadas

    registrado = "\n".join([caplog.text, *textos, repr(cliente), str(vars(cliente).keys())])
    assert "Pluggy" in caplog.text  # houve log para conferir
    assert len(textos) >= 4 * 3
    assert SEGREDO not in registrado
    assert CHAVE not in registrado
