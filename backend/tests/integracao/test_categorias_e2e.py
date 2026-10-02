"""Ciclo de vida de uma categoria pelo app real (CA-11.1 a CA-11.4, RN-12; F-15 §3.2.5)."""

from contextlib import suppress
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.integracao.ambiente import nova_marca

MES = "2098-06"
COR = "#5C6BC0"


@pytest.mark.integracao
def test_ciclo_de_categoria__RN_12(cliente_teste: TestClient) -> None:
    marca = nova_marca()
    categoria_id: str | None = None
    lancamento_id: str | None = None

    def lancamento(categoria: str) -> Any:
        return cliente_teste.post(
            "/api/lancamentos",
            json={
                "data": f"{MES}-10",
                "tipo": "GASTO",
                "descricao": f"{marca} compra",
                "valor": 15,
                "categoria_id": categoria,
                "forma_pagamento": "DINHEIRO",
            },
        )

    def do_mes() -> list[dict[str, Any]]:
        itens = cliente_teste.get(f"/api/lancamentos?mes={MES}").json()["itens"]
        return [i for i in itens if i["descricao"].startswith(marca)]

    try:
        criada = cliente_teste.post(
            "/api/categorias", json={"nome": marca, "tipo": "GASTO", "cor": COR}
        )
        assert criada.status_code == 201, criada.text
        categoria_id = criada.json()["id"]
        registrado = lancamento(categoria_id)
        assert registrado.status_code == 201, registrado.text
        lancamento_id = registrado.json()["id"]

        # CA-11.2: renomear vale também para o lançamento antigo.
        novo_nome = f"{marca}-novo"
        renomeada = cliente_teste.put(
            f"/api/categorias/{categoria_id}", json={"nome": novo_nome, "cor": COR, "ativa": True}
        )
        assert renomeada.status_code == 200, renomeada.text
        assert [i["categoria_nome"] for i in do_mes()] == [novo_nome]

        # CA-11.1: mesmo nome com maiúsculas e acento é duplicado.
        parecido = novo_nome.replace("teste-integracao", "TESTE-INTEGRAÇÃO")
        duplicada = cliente_teste.post(
            "/api/categorias", json={"nome": parecido, "tipo": "GASTO", "cor": COR}
        )
        assert duplicada.status_code == 409
        assert duplicada.json()["erro"]["codigo"] == "CATEGORIA_DUPLICADA"

        # CA-11.3: com lançamento, não exclui.
        em_uso = cliente_teste.delete(f"/api/categorias/{categoria_id}")
        assert em_uso.status_code == 409
        assert em_uso.json()["erro"]["codigo"] == "CATEGORIA_EM_USO"

        # CA-11.4: desativada some para novos lançamentos, mas continua na listagem.
        desativada = cliente_teste.put(
            f"/api/categorias/{categoria_id}", json={"nome": novo_nome, "cor": COR, "ativa": False}
        )
        assert desativada.status_code == 200, desativada.text
        recusado = lancamento(categoria_id)
        assert recusado.status_code == 409
        assert recusado.json()["erro"]["codigo"] == "CATEGORIA_INATIVA"
        assert [i["categoria_nome"] for i in do_mes()] == [novo_nome]

        # RN-12: sem lançamentos, pode excluir.
        assert cliente_teste.delete(f"/api/lancamentos/{lancamento_id}").status_code == 204
        lancamento_id = None
        assert cliente_teste.delete(f"/api/categorias/{categoria_id}").status_code == 204
        todas = cliente_teste.get("/api/categorias?incluir_inativas=true").json()
        assert categoria_id not in {c["id"] for c in todas}
        categoria_id = None
    finally:
        with suppress(Exception):
            if lancamento_id:
                cliente_teste.delete(f"/api/lancamentos/{lancamento_id}")
            if categoria_id:
                cliente_teste.delete(f"/api/categorias/{categoria_id}")
