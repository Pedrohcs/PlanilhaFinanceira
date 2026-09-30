# F-09 — Resumo mensal

| Campo | Valor |
|---|---|
| Feature | F-09 |
| Marco | M2 |
| Status | Aprovada |
| Requisitos | REQ-12 (CA-12.1, CA-12.2); dados de REQ-13 (acumulado diário, usado em F-10) |
| Regras | RN-03, RN-13, RN-14, RN-16 |
| Depende de | F-06 (**Concluída**); T-022 também usa o seletor de mês de F-04 (T-011, **Concluída**) |
| Tarefas | T-021, T-022 |
| Atualizado em | 2026-09-30 |

> **IDs de critério:** herdados de `01` mantêm o ID original (**CA-12.1** …). Os refinados usam **`CA-F09.y`**.

---

## 1. Objetivo

Abrir o aplicativo e ver, num relance, como está o mês: quanto saiu, quanto entrou, o saldo, onde o dinheiro foi (por categoria) e como foi pago (por forma de pagamento) — com números que batem centavo a centavo com a planilha.

---

## 2. Escopo

**Inclui**
- `resumo_service.mensal(mes)` e `GET /api/resumo/mensal?mes=YYYY-MM` → `200 ResumoMensal` (`03` §6.1, §6.3), **inclusive** `gasto_acumulado_diario` (o contrato é um só; quem o desenha é F-10).
- Página `/resumo` (hoje provisória, F-04): seletor de mês, cards de **Gastos**, **Receitas** e **Saldo** (negativo destacado) e tabelas **Gastos por categoria** e **Gastos por forma de pagamento** (valor e %).
- `ResumoApi.mensal`.

**Não inclui** (e onde será tratado)
- Gráficos (rosca por categoria, barras por forma, linha do acumulado diário) — **F-10** (T-023). Aqui o `/resumo` só tem cards e tabelas.
- Histórico de vários meses — **F-11**.
- Aviso de linhas ignoradas na tela (CA-16.3) — **F-14**. A API já devolve `linhas_ignoradas`.
- Receitas por categoria — REQ-12 pede só **gasto** por categoria.
- Clicar numa categoria para abrir a listagem filtrada — fora de escopo (anotar como sugestão).

---

## 3. Comportamento detalhado

### 3.1 Backend — `resumo_service.mensal` (T-021)

1. Entrada: `mes` no formato `YYYY-MM`, **obrigatório** (como em `GET /api/lancamentos`); ausente ou inválido → 422 no campo `mes`.
2. Lançamentos do mês = os de data nesse mês (RN-03), lidos com **uma leitura por aba** pelo cache (`02` §5.5). Linhas inválidas ficam de fora e são contadas em `linhas_ignoradas` (RN-14, CA-16.3).
3. **Totais** (RN-13, RN-16): `total_gastos`, `total_receitas` e `saldo = receitas − gastos`, em `Decimal` — a mesma função `totalizar` de F-07, para o resumo e a listagem sem filtro darem **exatamente** os mesmos números. Saldo pode ser negativo.
4. **`por_categoria`** — só gastos (`03` §6.3):
   - um item por `categoria_id` que tem gasto no mês; categorias sem gasto não aparecem;
   - `nome` e `cor` **atuais** da categoria (CA-11.2), inclusive de categoria inativa; categoria apagada à mão → "Categoria não encontrada" e `#9E9E9E` (F-07 §3.1.6);
   - ordem: `total` decrescente; empate → nome em ordem alfabética sem acento/caixa (a mesma chave de F-05).
5. **`por_forma_pagamento`** — só gastos: um item por forma com gasto; `nome` = rótulo de RN-05 ("Pix", "Cartão de crédito"…); ordem: `total` decrescente; empate → ordem de RN-05.
6. **`percentual`** = `total` ÷ `total_gastos` × 100, número de 0 a 100 com **1 casa** (`03` §6.3), calculado em `Decimal` com arredondamento `ROUND_HALF_UP`, **cada um sozinho** (Q1): a soma pode dar 99,9 ou 100,1.
7. **`gasto_acumulado_diario`** — **todos os dias do mês** (Q2), também no mês corrente: um item por dia do mês (1 a 28/29/30/31), `total` = soma dos gastos com data até aquele dia (inclusive). Mês sem gastos → todos os dias com 0.
8. Mês sem lançamentos → 200 com totais 0, listas vazias e o acumulado todo em 0 (não é erro).
9. Planilha inacessível → 503 com a causa (F-02).

### 3.2 Página `/resumo` (T-022)

1. Título "Resumo" e o **seletor de mês** de F-04 (mês na URL `?mes=`, compartilhado com a listagem — CA-04.2).
2. **Cards** Gastos, Receitas e Saldo, formatados como na listagem de F-07 (`R$ 1.234,56`; negativo `− R$ 60,00`); **saldo negativo destacado** com a cor de erro do tema (CA-12.2). Mesmo componente visual da listagem (ver §10).
3. **Gastos por categoria**: tabela com a bolinha da cor, o nome, o valor e o percentual (`45,3%`), na ordem da API.
4. **Gastos por forma de pagamento**: tabela com nome, valor e percentual, na ordem da API.
5. Em ≥ 960 px as duas tabelas ficam lado a lado; abaixo disso, uma sobre a outra. Em 360 px nada corta nem rola na horizontal (RNF-07).
6. **Mês sem lançamentos**: cards com R$ 0,00 e, no lugar das tabelas, o estado vazio "Nenhum lançamento em setembro de 2026." (mesmo padrão de F-07). Mês **só com receitas**: cards preenchidos e, no lugar das tabelas, "Nenhum gasto em setembro de 2026.".
7. **Recarga**: ao trocar de mês e quando `DadosStore.versao` muda (registro, edição, exclusão, parcelamento — CA-01.5); resposta de busca antiga é descartada (F-07 borda 15). Durante a recarga o conteúdo anterior fica esmaecido.
8. **Carregando** na primeira carga (componente de F-04); **erro** → "Não foi possível carregar o resumo." (a causa vai para o banner/aviso pelo interceptor, F-04).
9. O frontend **não soma nada**: cards, valores e percentuais vêm prontos da API (`03` §4.2, §8.2.1).

---

## 4. Critérios de aceite

**Herdados de `01`**

- [~] **CA-12.1** Dado os lançamentos de um mês, então os totais exibidos batem, centavo a centavo, com a soma dos lançamentos da planilha naquele mês. *(T-021: a API soma centavo a centavo, com os mesmos totais da listagem; a tela é T-022.)*
- [ ] **CA-12.2** Dado um saldo negativo, então ele é destacado visualmente.

**Refinados — backend (T-021)**

- [x] **CA-F09.1** Dado lançamentos de setembro (gastos e receitas, inclusive parcelas e recorrentes) e de outros meses, quando `GET /api/resumo/mensal?mes=2026-09`, então `total_gastos`, `total_receitas` e `saldo` são os mesmos de `GET /api/lancamentos?mes=2026-09` sem filtros, e só os de setembro contam (RN-03, RN-13).
- [x] **CA-F09.2** Dado 0,10 + 0,20 somados 3 vezes (valores que dão erro em ponto flutuante), então os totais saem exatos: R$ 0,90 (RN-16).
- [x] **CA-F09.3** Dado gastos em 3 categorias e 2 formas, então `por_categoria` e `por_forma_pagamento` trazem só gastos, um item por categoria/forma com gasto, com nome e cor atuais, ordenados do maior para o menor (empates pela regra de §3.1.4–5), e `percentual` com 1 casa.
- [x] **CA-F09.4** Dado uma categoria inativa com gasto no mês e outra apagada à mão, então a inativa aparece com seu nome e a apagada como "Categoria não encontrada" (`#9E9E9E`).
- [x] **CA-F09.5** Dado gastos nos dias 1, 15 e 30 de setembro, então `gasto_acumulado_diario` tem 30 itens, cresce nesses dias e fica constante entre eles; fevereiro de 2028 tem 29 itens (Q2).
- [x] **CA-F09.6** Dado um mês sem lançamentos, então 200 com totais 0, listas vazias e acumulado zerado.
- [x] **CA-F09.7** Dado `mes` ausente ou fora do formato, então 422 no campo `mes`; dado a planilha inacessível, então 503 com a causa.
- [x] **CA-F09.8** Dado uma linha inválida na aba, então ela não entra em nenhuma soma e `linhas_ignoradas` = 1 (CA-16.3).
- [x] **CA-F09.9** Dado o resumo pedido, então há uma leitura de cada aba (pelo cache), sem escrita (RNF-04).

**Refinados — frontend (T-022)**

- [ ] **CA-F09.10** Dado a resposta da API, então os cards mostram Gastos, Receitas e Saldo com os números dela, sem nenhuma conta no frontend (CA-12.1).
- [ ] **CA-F09.11** Dado saldo negativo, então o card de Saldo fica destacado e mostra `− R$ 60,00` (CA-12.2).
- [ ] **CA-F09.12** Dado a resposta, então as tabelas por categoria (com a cor) e por forma mostram nome, valor e percentual (`45,3%`) na ordem da API.
- [ ] **CA-F09.13** Dado um mês sem lançamentos, então os cards mostram R$ 0,00 e aparece "Nenhum lançamento em <mês>."; dado um mês só com receitas, "Nenhum gasto em <mês>.".
- [ ] **CA-F09.14** Dado a troca de mês no seletor, ou `DadosStore.versao` incrementada, então o resumo é buscado de novo; uma resposta antiga que chega depois é descartada.
- [ ] **CA-F09.15** Dado um erro de carga, então aparece "Não foi possível carregar o resumo." e nenhum card com números velhos.
- [ ] **CA-F09.16** Dado a janela de 360 px e a de 1280 px, então as tabelas ficam uma sobre a outra / lado a lado, sem rolagem horizontal (RNF-07).

---

## 5. Casos de borda

| # | Caso | Comportamento esperado | Regra |
|---|---|---|---|
| 1 | Gasto em 30/09 e parcela em 01/10 | Só o de 30/09 conta em setembro. | RN-03 |
| 2 | Gastos 0,10 + 0,20 (×3) | 0,90 exato. | RN-16 |
| 3 | Só receitas no mês | Totais de receita e saldo positivos; `por_categoria`/`por_forma_pagamento` vazios; acumulado zerado. | REQ-12 |
| 4 | Só gastos no mês | Saldo negativo, destacado. | RN-13, CA-12.2 |
| 5 | Uma única categoria com gasto | `percentual` 100,0. | — |
| 6 | Três categorias com R$ 10,00 cada | 33,3% cada; a soma dá 99,9 (Q1). | — |
| 7 | Duas categorias com o mesmo total | Ordem pelo nome, sem acento/caixa. | §3.1.4 |
| 8 | Categoria renomeada depois dos lançamentos | Aparece com o nome novo. | CA-11.2 |
| 9 | Categoria inativa com gasto no mês | Aparece normalmente. | RN-12 |
| 10 | Categoria apagada à mão na planilha | "Categoria não encontrada", `#9E9E9E`. | RN-14 |
| 11 | Linha com valor inválido na planilha | Ignorada nas somas; `linhas_ignoradas` = 1. | CA-16.3 |
| 12 | Fevereiro de 2028 / abril | Acumulado com 29 / 30 dias. | Q2 |
| 13 | Gasto com data futura dentro do mês corrente | Entra nos totais e no acumulado do dia dele; a curva vai até o último dia do mês (Q2). | RN-03 |
| 14 | `?mes=2026-13` ou sem `mes` | 422 no campo `mes`. | — |
| 15 | Troca rápida de mês (resposta de agosto chega depois da de setembro) | Fica a de setembro. | F-07 borda 15 |
| 16 | Registro pelo botão da barra com o resumo aberto | O resumo recarrega. | CA-01.5 |

---

## 6. Contrato e dados

**API** (`03` §6.1)

| Método | Caminho | Entrada | Saída |
|---|---|---|---|
| GET | `/api/resumo/mensal` | `?mes=YYYY-MM` (**obrigatório**) | `200 ResumoMensal` · `422` · `503` |

```jsonc
// ResumoMensal (03 §6.3), exemplo de setembro de 2026
{ "mes": "2026-09", "total_gastos": 1500.00, "total_receitas": 5000.00, "saldo": 3500.00,
  "por_categoria": [
    { "categoria_id": "moradia", "nome": "Moradia", "cor": "#4FC3F7", "total": 1000.00, "percentual": 66.7 },
    { "categoria_id": "alimentacao", "nome": "Alimentação", "cor": "#E57373", "total": 500.00, "percentual": 33.3 } ],
  "por_forma_pagamento": [
    { "forma_pagamento": "CREDITO", "nome": "Cartão de crédito", "total": 1200.00, "percentual": 80.0 },
    { "forma_pagamento": "PIX", "nome": "Pix", "total": 300.00, "percentual": 20.0 } ],
  "gasto_acumulado_diario": [ { "dia": 1, "total": 0.00 }, ..., { "dia": 30, "total": 1500.00 } ],
  "linhas_ignoradas": 0 }
```

A única precisão sobre `03` é que `mes` é **obrigatório** (a tabela de §6.1 não dizia); T-021 marca "(obrig.)" em `03` §6.1, como já está em `GET /api/lancamentos`.

**Planilha** — leitura de `Lancamentos` e `Categorias` (cache). Nenhuma escrita, nenhuma coluna nova.

---

## 7. Interface

- **Rota:** `/resumo?mes=YYYY-MM` (F-04).
- **Componentes:** `ResumoPage` (substitui a provisória), `ResumoApi`, cards de totais compartilhados com a listagem (§10), `SeletorMes`, `EstadoVazio`, `Carregando` (F-04).
- **Estados:** carregando (1ª carga) · recarregando (esmaecido) · vazio (sem lançamentos / sem gastos) · erro · sucesso.
- **Mensagens (pt-BR):** "Resumo"; "Gastos"; "Receitas"; "Saldo"; "Gastos por categoria"; "Gastos por forma de pagamento"; "Nenhum lançamento em <mês>."; "Nenhum gasto em <mês>."; "Não foi possível carregar o resumo.".
- **Acessibilidade:** tabelas com `<th scope="col">` (Categoria/Forma, Valor, %); a bolinha de cor é decorativa (`aria-hidden`); percentuais com `%` no texto.

---

## 8. Plano de testes

| Teste | Nível | Cobre |
|---|---|---|
| `tests/unit/test_resumo_service.py::test_totais_iguais_aos_da_listagem__CA_12_1` | unitário BE | CA-12.1, CA-F09.1, borda 1 |
| `…::test_somas_exatas_em_centavos__RN_16` | unitário BE | CA-F09.2, borda 2 |
| `…::test_por_categoria_e_forma_ordenados__CA_F09_3` | unitário BE | CA-F09.3, bordas 5–7 |
| `…::test_categoria_inativa_renomeada_e_apagada__CA_F09_4` | unitário BE | CA-F09.4, bordas 8–10 |
| `…::test_acumulado_diario__CA_F09_5` (parametrizado: set/2026, fev/2028) | unitário BE | CA-F09.5, bordas 12–13 |
| `…::test_empate_de_forma_segue_rn_05` | unitário BE | §3.1.5 |
| `tests/unit/test_datas.py::test_dias_no_mes` | unitário BE | §3.1.7 |
| `…::test_mes_vazio_e_so_receitas__CA_F09_6` | unitário BE | CA-F09.6, borda 3 |
| `…::test_percentuais_arredondados__Q1` | unitário BE | borda 6 |
| `tests/api/test_resumo.py::test_get_formato__CA_12_1` | API BE | contrato §6 |
| `…::test_get_422_mes__CA_F09_7` · `test_get_503__CA_F09_7` | API BE | CA-F09.7, borda 14 |
| `…::test_linha_invalida_ignorada__CA_16_3` (planilha falsa) | API BE | CA-F09.8, borda 11 |
| `…::test_uma_leitura_por_aba__RNF_04` (planilha falsa) | API BE | CA-F09.9 |
| `tests/api/test_app.py` (guarda de rotas) | API BE | `GET /api/resumo/mensal` |
| `frontend/…/core/api/resumo.api.spec.ts` › `mensal` | unitário FE | §6 |
| `…/features/resumo/resumo.page.spec.ts` › `cards_com_numeros_da_api__CA_12_1` | unitário FE | CA-F09.10 |
| `…` › `saldo_negativo_destacado__CA_12_2` | unitário FE | CA-F09.11 |
| `…` › `tabelas_por_categoria_e_forma__CA_F09_12` | unitário FE | CA-F09.12 |
| `…` › `vazio_e_so_receitas__CA_F09_13` | unitário FE | CA-F09.13 |
| `…` › `recarrega_por_mes_e_versao__CA_F09_14` (inclui resposta antiga descartada) | unitário FE | CA-F09.14, bordas 15–16 |
| `…` › `erro_de_carga__CA_F09_15` | unitário FE | CA-F09.15 |
| `…` › `tabelas_lado_a_lado_ou_empilhadas__CA_F09_16` + conferência visual em 360 px | unitário FE + manual | CA-F09.16 |

---

## 9. Divisão em tarefas

| Tarefa | Escopo nesta feature | Arquivos principais |
|---|---|---|
| **T-021** (BE) | `resumo_service.mensal`, schemas `ResumoMensalSaida`, router `GET /api/resumo/mensal`, dependência, guarda de rotas; `03` §6.1 com "(obrig.)". | `backend/app/services/resumo_service.py`, `backend/app/api/routers/resumo.py`, `backend/app/api/{schemas.py,deps.py}`, `backend/app/main.py`, `backend/tests/unit/test_resumo_service.py`, `backend/tests/api/{test_resumo.py,test_app.py}` |
| **T-022** (FE) | `ResumoApi`, modelo, página `/resumo` (cards, tabelas, vazio, erro, recarga), cards de totais compartilhados com a listagem. | `frontend/src/app/core/api/resumo.api.ts`, `frontend/src/app/core/models/resumo.ts`, `frontend/src/app/features/resumo/resumo.page.*`, `frontend/src/app/shared/components/totais/`, `frontend/src/app/features/lancamentos/lancamentos.page.*` + specs |

Ordem: T-021 → T-022 (T-022 também depende de T-011, concluída).

---

## 10. Decisões tomadas nesta feature

| Decisão | Motivo | Virou ADR? |
|---|---|---|
| Totais do resumo pela mesma `totalizar` da listagem. | Resumo e listagem sem filtro nunca podem divergir (CA-12.1). | Não |
| `mes` obrigatório em `GET /api/resumo/mensal`. | Mesmo padrão de `GET /api/lancamentos`; o frontend sempre sabe o mês. | Não |
| Empates: categoria pelo nome (chave de F-05), forma pela ordem de RN-05. | Ordem estável entre recargas. | Não |
| Categoria inativa aparece; apagada à mão vira "Categoria não encontrada". | Mesmo tratamento de F-07 (CA-11.2, RN-14). | Não |
| Mês sem lançamentos: cards com R$ 0,00 + estado vazio no lugar das tabelas. | Mesmo padrão da listagem de F-07. | Não |
| Cards de Gastos/Receitas/Saldo viram um componente compartilhado (`shared/components/totais`), usado pelo resumo e pela listagem. | Mesmo visual e o mesmo destaque do saldo negativo nas duas telas, sem duplicar código. | Não |
| `gasto_acumulado_diario` entregue já em T-021. | O contrato `ResumoMensal` é um só (`03` §6.3); F-10 só desenha. | Não |
| Percentual arredondado linha a linha, sem forçar soma 100 (Q1). | Cada linha é fiel ao próprio valor; linhas de mesmo valor têm o mesmo percentual. | Não |
| Acumulado diário com todos os dias do mês (Q2). | Coerente com os totais, que já incluem gastos com data futura no mês (RN-03). | Não |
| `dias_no_mes(mes)` em `domain/datas.py` (T-021). | Aritmética de calendário fica no domínio, ao lado de `ajustar_dia`. | Não |

---

## 11. Questões em aberto

**Respondidas em 2026-09-30 — nenhuma em aberto.** Nas duas, o usuário escolheu a opção recomendada.

- [x] **Q1** → cada percentual arredondado **sozinho** (1 casa, `ROUND_HALF_UP`); a soma pode dar 99,9 ou 100,1 (§3.1.6).
- [x] **Q2** → acumulado com **todos os dias do mês**, também no mês corrente (§3.1.7).

---

## Revisões

| Data | Alteração |
|---|---|
| 2026-09-30 | Criação (`/especificar-feature F-09`). Status `Rascunho` — 2 questões em aberto. |
| 2026-09-30 | Q1–Q2 respondidas (ambas na opção recomendada) → status **Aprovada**. Duas decisões em §10. |
| 2026-09-30 | T-021 concluída: CA-F09.1 a .9 verificados por teste (inclui 5.000 linhas com uma leitura por aba); CA-12.1 com a parte da API. `03` §6.1 com `mes` obrigatório. |
