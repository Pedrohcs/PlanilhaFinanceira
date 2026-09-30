# F-12 — Parcelamentos

| Campo | Valor |
|---|---|
| Feature | F-12 |
| Marco | M3 |
| Status | Concluída |
| Requisitos | REQ-07 (CA-07.1 a CA-07.3), REQ-08 (CA-08.1, CA-08.2) |
| Regras | RN-07, RN-08; RN-01..06 (mesmas do registro), RN-03, RN-14 |
| Depende de | F-08 (**Concluída**) |
| Tarefas | T-026, T-027 |
| Atualizado em | 2026-09-30 |

> **IDs de critério:** herdados de `01` mantêm o ID original (**CA-07.1** …). Os refinados usam **`CA-F12.y`**.

---

## 1. Objetivo

Registrar uma compra parcelada uma vez só — informando o valor total e o número de parcelas — e ver cada parcela no seu mês, podendo depois mexer numa parcela isolada ou apagar o parcelamento inteiro de uma vez.

---

## 2. Escopo

**Inclui**
- `parcelamento_service.criar(entrada)` e `excluir(parcelamento_id)`; `POST /api/parcelamentos` → `201 {parcelamento_id, lancamentos}` e `DELETE /api/parcelamentos/{parcelamento_id}` → `204` (`03` §6.1).
- Todas as parcelas gravadas numa **única** chamada à API do Google (`append_rows`, `02` §5.5 "Escritas em lote"; critério de conclusão de F-12 em `04`).
- No diálogo de F-06: opção **"Compra parcelada"** com nº de parcelas e prévia do valor das parcelas (só em **gasto novo**, `03` §8.3).
- Na listagem (F-07/F-08): ação **"Excluir parcelamento inteiro"** nas parcelas; o "k/N" já existe (F-07).
- `ParcelamentosApi.criar` e `excluir`.

**Não inclui** (e onde será tratado)
- Editar o parcelamento como um todo (mudar o total ou o nº de parcelas depois de criado) — fora de escopo: REQ-08 prevê editar **uma parcela** (F-08, RN-08) ou excluir **o parcelamento inteiro**. Para refazer, exclui-se o parcelamento e registra-se de novo.
- Receita parcelada — REQ-07 fala só de gasto; `ParcelamentoEntrada` não tem `tipo`.
- Juros, entrada ou parcelas de valores diferentes — RN-07 define a divisão.
- Mês da fatura do cartão — RN-03/P-02: a parcela conta no mês da **sua data**.

---

## 3. Comportamento detalhado

### 3.1 Backend — `criar` (T-026)

1. Entrada `ParcelamentoEntrada` (`03` §6.3): `data` (da compra), `descricao`, `valor_total`, `parcelas`, `categoria_id`, `forma_pagamento`, `observacao`. Schema: `data`, `descricao` e `observacao` como em `LancamentoEntrada` (RN-02, RN-06); `valor_total` é `Dinheiro` (> 0, 2 casas — RN-01); `parcelas` inteiro de **2 a 48** (RN-07) → fora disso, 422 no campo `parcelas`.
2. O **tipo é sempre `GASTO`** (REQ-07). Categoria e forma validadas pela **mesma regra** do registro (F-06 §3.5): categoria existente (senão 422 no campo), ativa (409 `CATEGORIA_INATIVA`), de gasto (409 `CATEGORIA_TIPO_INCOMPATIVEL`); forma obrigatória (422 no campo). Qualquer forma de pagamento é aceita (RN-05; `01` não restringe o parcelamento ao cartão).
3. **Valores** (RN-07, P-03 confirmada): `dividir_em_parcelas(valor_total, parcelas)` (domínio, F-03) — total ÷ N truncado no centavo, a sobra de centavos toda na **1ª** parcela; a soma é exatamente o total. Total menor que N × R$ 0,01 → 422 no campo `valor_total`: "10 parcelas exigem um valor total de no mínimo R$ 0,10.".
4. **Datas** (RN-07): `data_da_parcela(data, k)` (domínio, F-03) — parcela *k* = data da compra + (k−1) meses, sempre contando **a partir da compra**; dia inexistente → último dia do mês (31/01 em 3× → 31/01, 28/02, **31/03**).
5. Cada parcela é um `Lancamento` comum (RN-08): `id` próprio, `tipo = GASTO`, a **descrição original** (sem sufixo — CA-07.3), mesma categoria, forma e observação, `parcelamento_id` comum (`uuid4().hex`, `02` §3), `parcela_numero` = k, `parcela_total` = N, `recorrencia_id` vazio, `criado_em = atualizado_em` = o mesmo instante para todas.
6. Grava as N linhas com **um** `inserir([...])` do repositório (F-03: um `append_rows`, RAW, `INSERT_ROWS`). Falha do Google → 503 e nada é gravado (a chamada é única).
7. Resposta `201 {parcelamento_id, lancamentos: [Lancamento]}`, parcelas em ordem de `parcela_numero`, com `categoria_nome`/`categoria_cor`.

### 3.2 Backend — `excluir` (T-026)

1. Lista os lançamentos com aquele `parcelamento_id` — em **qualquer mês**, inclusive parcelas editadas depois (data, valor, até categoria: RN-08 só liga pelo `parcelamento_id`).
2. Nenhum → 404 `NAO_ENCONTRADO`: "Parcelamento não encontrado." (inclui o caso de todas as parcelas já terem sido excluídas uma a uma).
3. Remove todas com **um** `remover(ids)` (F-03: relê a aba, localiza pelos `id`, um `batch_update` de baixo para cima, tudo ou nada) → `204`. Parcelas já excluídas individualmente não impedem nada: só as restantes existem.
4. **Planilha mudou desde a última leitura** (parcela apagada à mão dentro do TTL do cache): o `remover` levanta `NaoEncontrado` sem apagar nada e invalida o cache (F-03). O serviço **relista e tenta uma única vez mais**; se ainda falhar, 404.

### 3.3 Diálogo — "Compra parcelada" (T-027)

1. Só em **"Registrar gasto"** (`03` §8.3): caixa de seleção **"Compra parcelada"** logo abaixo do valor. Não aparece em "Registrar receita" nem no modo edição (uma parcela se edita como lançamento comum — CA-08.1).
2. Marcada:
   - o rótulo **Valor** vira **"Valor total"** e **Data** vira **"Data da compra"**;
   - aparece o campo **"Nº de parcelas"** (numérico, vazio de início): obrigatório, inteiro de 2 a 48 — erro "Informe de 2 a 48 parcelas.";
   - com valor total e nº de parcelas válidos, aparece a **prévia** (Q1): "3× — 1ª de R$ 333,34 e 2× de R$ 333,33" ou, se todas iguais, "10× de R$ 100,00". Total pequeno demais para N parcelas → erro no Valor total: "10 parcelas exigem um valor total de no mínimo R$ 0,10.".
3. Desmarcada: o campo de parcelas some (e sai da validação) e o diálogo volta ao registro comum.
4. Salvar marcado → `POST /api/parcelamentos` com `{data, descricao, valor_total, parcelas, categoria_id, forma_pagamento, observacao}` e `TRATAMENTO_LOCAL` (F-06 Q3). Erros como no registro (F-06 §3.4): o diálogo fica aberto com os dados; 422 em `valor_total` marca o campo Valor total; em `parcelas`, o Nº de parcelas; 409 de categoria, o campo Categoria.
5. Sucesso → diálogo fecha, aviso (Q3) e `DadosStore.incrementar()`. Aviso: "Compra parcelada registrada: 10 parcelas, de setembro de 2026 a junho de 2027." — meses tirados da **1ª e da última parcela da resposta** (o frontend não calcula datas).

### 3.4 Listagem — "Excluir parcelamento inteiro" (T-027)

1. O "k/N" e a descrição original já aparecem (F-07, CA-07.3).
2. No menu ⋮ (F-08 Q2) de uma **parcela**, depois de Editar e Excluir, o item **"Excluir parcelamento inteiro"** (Q2). Lançamentos que não são parcela não têm o item.
3. Confirmação (`confirmacao-dialog`):
   - título "Excluir parcelamento inteiro?";
   - mensagem: `"Geladeira" — todas as parcelas restantes deste parcelamento em 10×, em todos os meses, serão excluídas.`;
   - botão "Excluir parcelas".
   Confirmado → `DELETE /api/parcelamentos/{parcelamento_id}`; sucesso → aviso "Parcelamento excluído." e `DadosStore.incrementar()`.
4. 404 → mensagem do interceptor ("Parcelamento não encontrado.") e a lista recarrega; 503/backend fora → banner, a lista continua (F-08 borda 12).
5. "Excluir" (só esta parcela) continua como em F-08 §3.3.

---

## 4. Critérios de aceite

**Herdados de `01`**

- [x] **CA-07.1** Dado um gasto de R$ 1.000,00 em 3 parcelas com data 15/01, quando confirmado, então são criados 3 lançamentos: R$ 333,34 em 15/01, R$ 333,33 em 15/02 e R$ 333,33 em 15/03 (ver RN-07).
- [x] **CA-07.2** Dado uma compra em 31/01 em 2 parcelas, então a 2ª parcela fica em 28/02 (ou 29/02 em ano bissexto).
- [x] **CA-07.3** Dado parcelas criadas, quando listadas, então cada uma exibe "k/N" e a descrição original. *(T-026: a API devolve `parcela_numero`/`parcela_total` e a descrição original; o "k/N" na tela já existia desde F-07.)*
- [x] **CA-08.1** Dado uma parcela, quando o usuário a edita, então apenas aquela parcela muda.
- [x] **CA-08.2** Dado uma parcela, quando o usuário escolhe "excluir parcelamento inteiro" e confirma, então todas as parcelas daquele parcelamento são removidas, em qualquer mês. *(T-026: remoção na API; T-027: ação "Excluir parcelamento inteiro" na listagem.)*

**Refinados — backend (T-026)**

- [x] **CA-F12.1** Dado `POST /api/parcelamentos` válido com N parcelas, então 201 com `parcelamento_id` e N lançamentos em ordem: todos `GASTO`, mesma descrição/categoria/forma/observação, `parcelamento_id` comum, `parcela_numero` 1..N, `parcela_total` N, `id` distintos, mesmo `criado_em`; a soma dos valores é exatamente o total.
- [x] **CA-F12.2** Dado o `POST` válido, então as N linhas são gravadas com **uma** chamada de escrita (`append_rows` RAW + `INSERT_ROWS`) — verificado na planilha falsa.
- [x] **CA-F12.3** Dado `parcelas` fora de 2..48, ou `valor_total` menor que N × R$ 0,01, então 422 no campo (`parcelas` / `valor_total`) e nada é gravado.
- [x] **CA-F12.4** Dado categoria inexistente (422), inativa (409), de receita (409) ou gasto sem forma (422), então o erro é o mesmo do registro e nada é gravado.
- [x] **CA-F12.5** Dado um parcelamento de 3 parcelas em meses diferentes, quando `DELETE /api/parcelamentos/{id}`, então 204 e só aquelas 3 linhas somem — com **um** `batch_update` — inclusive depois de o usuário reordenar a planilha à mão; as listagens dos 3 meses recalculam os totais.
- [x] **CA-F12.6** Dado que uma parcela foi excluída e outra editada (data mudada de mês) antes, quando o parcelamento inteiro é excluído, então as restantes — inclusive a editada — somem; 204.
- [x] **CA-F12.7** Dado `parcelamento_id` inexistente (ou com todas as parcelas já excluídas), então 404 "Parcelamento não encontrado." e nada muda.
- [x] **CA-F12.8** Dado que uma parcela foi apagada à mão depois da última leitura (cache), quando o parcelamento é excluído, então as restantes são removidas mesmo assim (uma nova tentativa com a aba relida).
- [x] **CA-F12.9** Dado a planilha inacessível, então `POST`/`DELETE` → 503 com a causa e nada é gravado ou removido.

**Refinados — frontend (T-027)**

- [x] **CA-F12.10** Dado "Registrar gasto", então a caixa "Compra parcelada" aparece; em "Registrar receita" e em "Editar …" ela não aparece.
- [x] **CA-F12.11** Dado "Compra parcelada" marcada, então os rótulos viram "Valor total" e "Data da compra", aparece "Nº de parcelas" e, com 1 e 49, o erro "Informe de 2 a 48 parcelas."; desmarcada, o campo some e o registro volta a ser comum.
- [x] **CA-F12.12** Dado R$ 1.000,00 em 3, então a prévia é "3× — 1ª de R$ 333,34 e 2× de R$ 333,33"; dado R$ 1.000,00 em 10, "10× de R$ 100,00"; dado R$ 0,05 em 10, erro "10 parcelas exigem um valor total de no mínimo R$ 0,10." e nenhuma prévia (Q1).
- [x] **CA-F12.13** Dado o parcelado salvo, então sai **um** `POST /api/parcelamentos` com o corpo de §3.3.4, o diálogo fecha, o aviso é "Compra parcelada registrada: 3 parcelas, de janeiro de 2026 a março de 2026." e `DadosStore.versao` aumenta; num 422/409, o diálogo fica aberto com os dados e o campo certo marcado (Q3).
- [x] **CA-F12.14** Dado a listagem, então o menu ⋮ de uma parcela tem "Excluir parcelamento inteiro" e o de um lançamento comum não (Q2).
- [x] **CA-F12.15** Dado "Excluir parcelamento inteiro", então a confirmação mostra o texto de §3.4.3; "Cancelar" não envia nada; confirmar envia o `DELETE /api/parcelamentos/{id}`, avisa "Parcelamento excluído." e a lista recarrega; num 404 a lista recarrega; num 503 não.

---

## 5. Casos de borda

| # | Caso | Comportamento esperado | Regra |
|---|---|---|---|
| 1 | R$ 1.000,00 em 3, 15/01/2026 | 333,34 (15/01), 333,33 (15/02), 333,33 (15/03). | CA-07.1 |
| 2 | 31/01/2026 em 2 · 31/01/2028 em 2 | 2ª em 28/02/2026 · 29/02/2028. | CA-07.2 |
| 3 | 31/01/2026 em 3 | 31/01, 28/02, **31/03** (conta da compra, não da parcela anterior). | RN-07 |
| 4 | 15/12/2026 em 3 | 15/12/2026, 15/01/2027, 15/02/2027 (vira o ano). | RN-07 |
| 5 | R$ 0,10 em 3 | 0,04 + 0,03 + 0,03. | RN-07 |
| 6 | R$ 0,05 em 10 | 422 `valor_total`: mínimo R$ 0,10. | RN-07 |
| 7 | 1 ou 49 parcelas | 422 `parcelas`. | RN-07 |
| 8 | R$ 100,00 em 48 | 48 lançamentos de 2,08, a 1ª com 2,24 (100,00 − 47 × 2,08). Uma chamada de escrita. | RN-07 |
| 9 | Categoria de receita ou inativa | 409; nada gravado. | RN-04 |
| 10 | Planilha fora ao salvar | 503; nada gravado; diálogo aberto com os dados. | RNF-06 |
| 11 | Parcela 3/10 editada (valor ou data) | Só ela muda; continua "3/10" e no parcelamento. | RN-08, CA-08.1 |
| 12 | Parcela 3/10 excluída; depois "excluir parcelamento inteiro" | Remove as 9 restantes; 204. | RN-08 |
| 13 | Todas as parcelas já excluídas uma a uma | 404 "Parcelamento não encontrado." | — |
| 14 | Parcela apagada à mão dentro do TTL do cache | Uma nova tentativa com a aba relida; as restantes somem. | RN-14 |
| 15 | Linha com `parcelamento_id` copiado à mão para outro lançamento | Passa a fazer parte do parcelamento e é excluída junto (o vínculo é só o `parcelamento_id`). | RN-08, RN-14 |
| 16 | Descrição `=SOMA(A1:A3)` | Gravada como texto em todas as parcelas (RAW). | ADR-04 |
| 17 | Duplo clique em "Salvar" | Um só `POST` (guarda de F-06). | — |
| 18 | "Compra parcelada" marcada, nº preenchido, depois desmarcada | Sai `POST /api/lancamentos` com o valor digitado, como gasto comum. | — |

---

## 6. Contrato e dados

**API** (`03` §6.1, sem alteração de caminho)

| Método | Caminho | Entrada | Saída |
|---|---|---|---|
| POST | `/api/parcelamentos` | `ParcelamentoEntrada` | `201 {parcelamento_id, lancamentos: [Lancamento]}` · `409` · `422` · `503` |
| DELETE | `/api/parcelamentos/{parcelamento_id}` | — | `204` · `404` · `503` |

```jsonc
// ParcelamentoEntrada (03 §6.3)
{ "data": "2026-01-15", "descricao": "Geladeira", "valor_total": 1000.00, "parcelas": 3,
  "categoria_id": "moradia", "forma_pagamento": "CREDITO", "observacao": null }

// 201
{ "parcelamento_id": "a71b...",
  "lancamentos": [
    { "id": "...", "data": "2026-01-15", "tipo": "GASTO", "descricao": "Geladeira", "valor": 333.34,
      "categoria_id": "moradia", "categoria_nome": "Moradia", "categoria_cor": "#...",
      "forma_pagamento": "CREDITO", "observacao": null,
      "parcelamento_id": "a71b...", "parcela_numero": 1, "parcela_total": 3,
      "recorrencia_id": null, "criado_em": "...", "atualizado_em": "..." },
    ... ] }
```

Erros de campo em `detalhes[].campo`: `valor_total`, `parcelas`, `categoria_id`, `forma_pagamento`, `data`, `descricao`, `observacao`.

**Planilha** — aba `Lancamentos` (`03` §5.1): colunas I (`parcelamento_id`), J (`parcela_numero`), K (`parcela_total`) já existem; N linhas num `append_rows`; exclusão por `batch_update` com `deleteDimension`. Leitura de `Categorias` (cache) para RN-04. **Nenhuma coluna nova**, `versao_schema` inalterada.

---

## 7. Interface

- **Onde:** diálogo "Registrar gasto" (F-06) e página `/lancamentos` (F-07/F-08).
- **Componentes:** `lancamento-form.dialog` (caixa "Compra parcelada", campo de parcelas, prévia), `abrir-lancamento.ts` (aviso do parcelado), `LancamentosPage` (item do menu ⋮ e confirmação), `core/api/parcelamentos.api.ts`, função pura de prévia em `core/utils/` (Q1).
- **Estados:** "Salvando…" e erros como em F-06; confirmação e 404/503 como em F-08.
- **Mensagens (pt-BR):** "Compra parcelada"; "Valor total"; "Data da compra"; "Nº de parcelas"; "Informe de 2 a 48 parcelas."; "N parcelas exigem um valor total de no mínimo R$ X."; "3× — 1ª de R$ 333,34 e 2× de R$ 333,33"; "10× de R$ 100,00"; "Compra parcelada registrada: N parcelas, de <mês> a <mês>."; "Excluir parcelamento inteiro"; "Excluir parcelamento inteiro?"; `"<descrição>" — todas as parcelas restantes deste parcelamento em N×, em todos os meses, serão excluídas.`; "Excluir parcelas"; "Parcelamento excluído."; "Parcelamento não encontrado." (backend).

---

## 8. Plano de testes

| Teste | Nível | Cobre |
|---|---|---|
| `tests/unit/test_parcelamento_service.py::test_criar_mil_em_tres__CA_07_1` | unitário BE | CA-07.1, CA-F12.1, borda 1 |
| `…::test_datas_fim_de_mes_e_bissexto__CA_07_2` (parametrizado) | unitário BE | CA-07.2, bordas 2–4 |
| `…::test_centavos_na_primeira__RN_07` (parametrizado: 0,10 em 3; 100 em 48) | unitário BE | RN-07, bordas 5, 8 |
| `…::test_limites_de_parcelas_e_valor_minimo__RN_07` | unitário BE | CA-F12.3, bordas 6–7 |
| `…::test_regras_de_categoria_e_forma__RN_04_RN_05` | unitário BE | CA-F12.4, borda 9 |
| `…::test_excluir_restantes_inclusive_editada__CA_08_2` | unitário BE | CA-08.2, CA-F12.6, borda 12 |
| `…::test_excluir_inexistente_404__CA_F12_7` | unitário BE | CA-F12.7, borda 13 |
| `…::test_excluir_tenta_de_novo_apos_mudanca_manual__CA_F12_8` | unitário BE | CA-F12.8, borda 14 |
| `tests/api/test_parcelamentos.py::test_post_uma_escrita__CA_F12_2` (planilha falsa) | API BE | CA-F12.1, CA-F12.2, borda 16 |
| `…::test_post_validacoes__CA_F12_3` e `test_valor_minimo_mensagem__RN_07` | API BE | CA-F12.3, CA-F12.4 |
| `…::test_delete_apos_linha_apagada_a_mao__CA_F12_8` (planilha falsa com cache) | API BE | CA-F12.8, borda 14 |
| `…::test_delete_404__CA_F12_7` | API BE | CA-F12.7 |
| `…::test_delete_so_as_parcelas_apos_reordenacao__CA_F12_5` (planilha falsa) | API BE | CA-08.2, CA-F12.5 |
| `…::test_listagem_mostra_k_de_n__CA_07_3` | API BE | CA-07.3 |
| `…::test_editar_parcela_so_ela__CA_08_1` | API BE | CA-08.1, borda 11 |
| `…::test_post_delete_503__CA_F12_9` | API BE | CA-F12.9, borda 10 |
| `tests/api/test_app.py` (guarda de rotas) | API BE | `POST`/`DELETE /api/parcelamentos` |
| `frontend/…/core/utils/parcelas.spec.ts` › `previa__RN_07` e `textos__CA_F12_12` | unitário FE | CA-F12.12 |
| `…/core/api/parcelamentos.api.spec.ts` › `criar_e_excluir__F12` | unitário FE | §6 |
| `…/features/lancamentos/lancamento-form.dialog.spec.ts` › `parcelada_so_em_gasto_novo__CA_F12_10` e `parcelada_nao_aparece_na_edicao__CA_F12_10` | unitário FE | CA-F12.10 |
| `…` › `campos_e_validacao_da_parcelada__CA_F12_11` | unitário FE | CA-F12.11, borda 18 |
| `…` › `previa_das_parcelas__CA_F12_12` | unitário FE | CA-F12.12 |
| `…` › `salva_parcelada__CA_F12_13` e `erro_marca_campo_da_parcelada__CA_F12_13` | unitário FE | CA-F12.13, borda 17 |
| `…` › `desmarcada_envia_lancamento_comum__borda_18` | unitário FE | borda 18 |
| `…/features/lancamentos/abrir-lancamento.spec.ts` › `aviso_da_parcelada__CA_F12_13` | unitário FE | CA-F12.13 |
| `…/features/lancamentos/lancamentos.page.spec.ts` › `menu_da_parcela__CA_F12_14` | unitário FE | CA-F12.14 |
| `…` › `excluir_parcelamento_inteiro__CA_08_2` (inclui cancelar) e `excluir_parcelamento_404_e_503__CA_F12_15` | unitário FE | CA-08.2, CA-F12.15 |

---

## 9. Divisão em tarefas

| Tarefa | Escopo nesta feature | Arquivos principais |
|---|---|---|
| **T-026** (BE) | `parcelamento_service` (criar/excluir, validação compartilhada com `lancamento_service`), `ParcelamentoEntrada`/saída, router, dependência, guarda de rotas. | `backend/app/services/parcelamento_service.py`, `backend/app/api/routers/parcelamentos.py`, `backend/app/api/{schemas.py,deps.py}`, `backend/app/main.py`, `backend/tests/unit/test_parcelamento_service.py`, `backend/tests/api/{test_parcelamentos.py,test_app.py}` |
| **T-027** (FE) | `ParcelamentosApi`; prévia; caixa "Compra parcelada" no diálogo; aviso; item "Excluir parcelamento inteiro" com confirmação. | `frontend/src/app/core/api/parcelamentos.api.ts`, `frontend/src/app/core/models/parcelamento.ts`, `frontend/src/app/core/utils/parcelas.ts`, `frontend/src/app/features/lancamentos/{lancamento-form.dialog.ts,abrir-lancamento.ts,lancamentos.page.*}` + specs |

Ordem: T-026 → T-027 (T-027 também depende de T-020, concluída).

---

## 10. Decisões tomadas nesta feature

| Decisão | Motivo | Virou ADR? |
|---|---|---|
| Parcela = lançamento `GASTO` comum com a descrição original, sem sufixo "(k/N)". | CA-07.3 ("a descrição original"); o "k/N" vem das colunas J/K. | Não |
| Validação de categoria e forma **reusa** a do `lancamento_service` (mesmas mensagens e códigos): o antigo método `_validar` virou a função `validar_categoria_e_forma` do módulo (T-026). | Uma regra só para RN-04/RN-05 (F-08 §10), sem um serviço depender do outro. | Não |
| Limites de parcelas e de valor checados **antes** da categoria (T-026). | Não precisam ler a planilha; uma entrada com os dois problemas recebe 422 no campo, não 409. | Não |
| Qualquer forma de pagamento é aceita no parcelamento. | RN-05 e REQ-07 não restringem ao cartão (ex.: boleto parcelado). | Não |
| Excluir parcelamento remove as parcelas **restantes**; 404 só quando não resta nenhuma. | RN-08: as parcelas são independentes; já ter excluído uma não deve impedir excluir o resto. | Não |
| Na exclusão, se a planilha mudou dentro do TTL, **uma** nova tentativa com a aba relida. | O `remover` é tudo ou nada e invalida o cache ao falhar (F-03); sem a nova tentativa, uma edição manual recente daria um 404 enganoso. | Não |
| Aviso do parcelado usa as datas da 1ª e da última parcela **da resposta**. | O frontend não calcula datas; a resposta já as traz. | Não |
| Prévia dos valores calculada no frontend só para exibição (Q1). | Resposta imediata enquanto digita, sem endpoint novo; não é total (a regra de `03` §4.2 continua valendo), e o valor gravado é sempre o do backend. | Não |
| "Excluir parcelamento inteiro" como item do menu ⋮ das parcelas (Q2). | Ação destrutiva maior separada da exclusão de uma parcela; mesmo padrão de F-08 Q2. | Não |
| Aviso com o intervalo de meses (Q3). | Deixa claro que foram criados lançamentos em meses futuros, fora da lista aberta. | Não |
| O diálogo fecha com um `Lancamento` ou um `Parcelamento` (guarda `ehParcelamento`); a mensagem do mínimo por parcela é a mesma da API e vem pronta no erro do campo Valor total, revalidado quando o nº de parcelas ou a caixa mudam (T-027). | Um só diálogo (`03` §8.3) e um só texto para o mesmo erro, venha do cliente ou do servidor. | Não |
| Aceito +1,7 kB no pacote inicial (475,94 kB) trazidos pelo `mat-checkbox`: o `_MatInternalFormField` vem de `@angular/material/core`, já usado no pacote inicial (T-027). | Mesmo caso do `MatOption` (F-06); dentro do orçamento de 500 kB; trocar por checkbox nativo quebraria o padrão visual. | Não |
| "Compra parcelada" só em gasto novo; parcela editada como lançamento comum. | `03` §8.3; CA-08.1. | Não |

---

## 11. Questões em aberto

**Respondidas em 2026-09-30 — nenhuma em aberto.** Em todas, o usuário escolheu a opção recomendada.

- [x] **Q1** → prévia calculada no **frontend**, só para exibir, por uma função pura em `core/utils/parcelas.ts` que espelha RN-07; o backend continua calculando o que é gravado, e os dois lados são testados com os mesmos exemplos (§3.3.2).
- [x] **Q2** → item próprio **"Excluir parcelamento inteiro"** no menu ⋮ das parcelas, com confirmação própria (§3.4.2).
- [x] **Q3** → aviso com os meses: "Compra parcelada registrada: 10 parcelas, de setembro de 2026 a junho de 2027." (§3.3.5).

---

## Revisões

| Data | Alteração |
|---|---|
| 2026-09-30 | Criação (`/especificar-feature F-12`). Status `Rascunho` — 3 questões em aberto. |
| 2026-09-30 | Q1–Q3 respondidas (todas na opção recomendada) → status **Aprovada**. Três decisões em §10. |
| 2026-09-30 | T-026 concluída: CA-07.1, CA-07.2, CA-07.3, CA-08.1 e CA-F12.1 a .9 verificados por teste (inclui planilha reordenada e linha apagada à mão com cache "quente"); CA-08.2 com a parte da API. Duas decisões em §10. |
| 2026-09-30 | T-027 concluída → feature **Concluída**. CA-08.2 e CA-F12.10 a .15 verificados por teste; plano de testes com os nomes finais. Duas decisões em §10. |
