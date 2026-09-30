# F-07 — Listagem mensal

| Campo | Valor |
|---|---|
| Feature | F-07 |
| Marco | M1 |
| Status | Aprovada |
| Requisitos | REQ-03 (CA-03.1 a CA-03.3), REQ-04 (CA-04.1, CA-04.2 — já com a parte de F-04), CA-01.5 (exibição), CA-11.2 (exibição) |
| Regras | RN-03, RN-13, RN-14, RN-16 |
| Depende de | F-06 (**Concluída**) |
| Tarefas | T-017, T-018 |
| Atualizado em | 2026-09-30 |

> **IDs de critério:** herdados de `01` mantêm o ID original (**CA-03.1** …). Os refinados usam **`CA-F07.y`**.

---

## 1. Objetivo

Ver, mês a mês, tudo o que entrou e saiu — com filtros por tipo, categoria e forma de pagamento e os totais do que está na tela, calculados sem erro de centavos.

---

## 2. Escopo

**Inclui**
- `lancamento_service.listar(mes, filtros)`: filtra pelo mês de referência (RN-03) e pelos filtros, ordena e totaliza em `Decimal` (RN-13, RN-16); devolve `linhas_ignoradas`.
- `GET /api/lancamentos?mes=YYYY-MM&tipo=&categoria_id=&forma_pagamento=` → `ListaLancamentos` (`03` §6.1, §6.3).
- Página `/lancamentos`: seletor de mês (já existe, F-04), filtros, cartões de totais, lista de lançamentos, estados carregando/vazio/erro; recarrega quando mês, filtros ou `DadosStore.versao` mudam.
- `LancamentosApi.listar`.

**Não inclui** (e onde será tratado)
- Editar e excluir (ações na lista) — **F-08** / T-019–T-020.
- Aviso de `linhas_ignoradas` na interface — **F-14** / T-032 (a API já devolve o número; CA-16.3).
- Excluir parcelamento inteiro — **F-12**.
- Resumo por categoria/forma e gráficos — **F-09/F-10**.

---

## 3. Comportamento detalhado

### 3.1 Backend — `listar` (T-017)

1. `mes` obrigatório, `YYYY-MM` válido; ausente ou inválido → 422 no campo `mes`.
2. Seleciona os lançamentos **válidos** (F-03) cuja `data` cai no mês (RN-03): `mes_de(data) == mes`.
3. Filtros opcionais, combinados com **E**:
   - `tipo` (`GASTO`/`RECEITA`; outro valor → 422);
   - `categoria_id` (qualquer texto; inexistente → lista vazia, não erro);
   - `forma_pagamento` (enum; outro valor → 422). Receita sem forma não aparece quando o filtro de forma está ativo.
4. **Ordem:** `data` decrescente (mais recente primeiro — REQ-03); na mesma data, `criado_em` decrescente (o registrado por último primeiro); empate final pelo `id`, para a ordem ser estável.
5. **Totais do que foi filtrado** (CA-03.2): `gastos` = soma dos gastos, `receitas` = soma das receitas, `saldo = receitas − gastos` (RN-13) — tudo em `Decimal`, 2 casas (RN-16). Sem itens → `0.00` em todos.
6. Cada item leva `categoria_nome` e `categoria_cor` da categoria atual (renomear reflete em todos — CA-11.2). Categoria que não existe mais (apagada à mão na planilha) → `categoria_nome: "Categoria não encontrada"`, `categoria_cor: "#9E9E9E"`.
7. `linhas_ignoradas` = o número da leitura da aba `Lancamentos` (a aba inteira, não só o mês).
8. Leituras: **uma** da aba `Lancamentos` e **uma** da `Categorias` (ambas pelo cache); filtragem em memória (`02` §5.5, RNF-04).
9. Planilha inacessível → 503 com o código da causa.

### 3.2 Página `/lancamentos` (T-018)

1. **Cabeçalho:** título "Lançamentos" e o seletor de mês (F-04).
2. **Filtros** (em linha no desktop, empilhados em janela estreita):
   - Tipo: "Todos" · "Gastos" · "Receitas";
   - Categoria: "Todas" + as categorias (ativas e inativas, com a cor) do tipo escolhido; com tipo "Todos", agrupadas em Gastos/Receitas. Trocar o tipo limpa uma categoria de outro tipo;
   - Forma de pagamento: "Todas" + as 6 de RN-05;
   - "Limpar filtros" aparece quando há algum ativo.
   - **Filtros na URL (Q1):** `?tipo=&categoria_id=&forma_pagamento=` ao lado do `?mes=`, gravados com `replaceUrl` (como o mês, F-04 §3.4): sobrevivem ao recarregar a página e ao voltar pelo histórico. Valor inválido na URL (ex.: `tipo=OUTRO`) é descartado e a URL corrigida. O link "Lançamentos" do menu leva só o `?mes=` — os filtros começam limpos.
3. **Totais** do que está filtrado, vindos prontos do backend (o frontend não soma — `02` §4): cartões **Gastos**, **Receitas** e **Saldo**; saldo negativo em destaque (cor de erro). Com filtro ativo, legenda "Totais dos lançamentos filtrados".
4. **Lista** — cada lançamento mostra (CA-03.1): data (`dd/mm/aaaa`), descrição, categoria (bolinha com a cor + nome), forma de pagamento (rótulo, ou "—" se não informada), valor, e:
   - parcela: "3/10" quando `parcela_numero` existe;
   - recorrência: ícone `event_repeat` com a dica "Lançamento recorrente" quando `recorrencia_id` existe;
   - observação, quando houver, em texto secundário.
   - **Valor (Q2):** gasto como "− R$ 42,50" na cor de texto normal; receita como "+ R$ 5.000,00" em verde — `light-dark(#2E7D32, #81C784)`, legível nos dois temas; alinhado à direita, com algarismos de largura fixa. O `aria-label` do valor diz "gasto de R$ 42,50" / "receita de R$ 5.000,00" (a cor não é a única pista).
   - **Layout (Q3):** a partir de **600 px**, tabela com as colunas Data · Descrição · Categoria · Forma · Valor (parcela/recorrência e observação dentro da célula Descrição); abaixo de 600 px, **cartões**: 1ª linha descrição (+ "3/10"/ícone) e valor; 2ª linha data · categoria · forma; observação abaixo, se houver. Mesma quebra do shell (F-04 Q1).
5. **Estados:**
   - carregando (primeira carga do mês): `carregando`;
   - recarga (mês, filtro ou `versao` mudou): o conteúdo anterior continua visível, esmaecido, até a resposta — sem piscar;
   - vazio sem filtro: "Nenhum lançamento em setembro de 2026." (CA-03.3);
   - vazio com filtro: "Nenhum lançamento com esses filtros." + "Limpar filtros";
   - erro (503/backend fora): banner de F-04 e, no lugar da lista, "Não foi possível carregar os lançamentos.".
6. **Recarga automática:** a página busca de novo quando o mês, algum filtro ou `DadosStore.versao` muda — um lançamento recém-registrado aparece sem ação do usuário (CA-01.5).
7. O mês vem do `MesSelecionadoStore` (F-04): abre no mês corrente (CA-04.1) e mantém o mês ao ir e voltar do Resumo (CA-04.2).

---

## 4. Critérios de aceite

**Herdados de `01`**

- [ ] **CA-03.1** Dado um mês com lançamentos, quando a listagem abre, então mostra data, descrição, categoria, forma de pagamento, valor e indicação de parcela (ex.: "3/10") ou de recorrência.
- [ ] **CA-03.2** Dado um filtro aplicado, quando a lista atualiza, então o total exibido corresponde à soma dos itens visíveis (gastos e receitas separados).
- [ ] **CA-03.3** Dado um mês sem lançamentos, quando a listagem abre, então uma mensagem de "nenhum lançamento" é exibida.
- [x] **CA-04.1** / [x] **CA-04.2** *(já verificados em F-04 com a página provisória; em F-07 continuam valendo com a página real — teste de regressão.)*
- [ ] **CA-01.5** *(exibição)* Dado um gasto recém-registrado, quando o usuário vê a listagem do mês, então o gasto já aparece e os totais já o consideram.
- [~] **CA-11.2** *(exibição)* Dado uma categoria renomeada, então todos os lançamentos dela exibem o novo nome, inclusive os antigos. *(T-017: API devolve o nome atual; a tela é T-018.)*

**Refinados — backend (T-017)**

- [x] **CA-F07.1** Dado lançamentos em agosto, setembro e outubro, quando `GET ?mes=2026-09`, então só os de setembro vêm — inclusive os de 01/09 e 30/09 (RN-03).
- [x] **CA-F07.2** Dado lançamentos em datas variadas, então a ordem é data decrescente; na mesma data, o registrado por último primeiro.
- [x] **CA-F07.3** Dado filtros `tipo`, `categoria_id` e `forma_pagamento`, isolados e combinados, então só os itens que atendem a **todos** vêm; e os totais somam só esses itens (CA-03.2).
- [x] **CA-F07.4** Dado gastos 0,10 + 0,20 e uma receita de 1.000,00, então `gastos = 0.30`, `receitas = 1000.00`, `saldo = 999.70`, exatos (RN-13, RN-16); e mês vazio → `0.0` nos três.
- [x] **CA-F07.5** Dado `mes` ausente, `2026-13` ou `setembro`, ou `tipo`/`forma_pagamento` fora do enum, então 422 no campo; `categoria_id` inexistente → 200 com lista vazia.
- [x] **CA-F07.6** Dado uma categoria renomeada, então `categoria_nome` dos lançamentos antigos vem com o nome novo (CA-11.2); e dado um lançamento cuja categoria não existe mais, então `categoria_nome` = "Categoria não encontrada" e `categoria_cor` = `#9E9E9E`.
- [x] **CA-F07.7** Dado uma linha inválida na aba, então ela não entra na lista nem nos totais e `linhas_ignoradas` a conta (CA-16.3).
- [x] **CA-F07.8** Dado 5.000 lançamentos, então a listagem faz uma leitura de cada aba (Lancamentos, Categorias) e responde em menos de 3 s (RNF-04; medição formal em T-032).
- [x] **CA-F07.9** Dado a planilha inacessível, então 503 com o código da causa.

**Refinados — frontend (T-018)**

- [ ] **CA-F07.10** Dado a resposta da API, quando a página renderiza, então cada item mostra os campos de CA-03.1 formatados em pt-BR ("30/09/2026", "R$ 1.234,56"), "3/10" nas parcelas, o ícone nos recorrentes e "—" na forma não informada.
- [ ] **CA-F07.11** Dado um filtro trocado, quando a página recarrega, então a requisição leva os parâmetros certos e os cartões mostram os totais **da resposta** (o frontend não soma nada).
- [ ] **CA-F07.12** Dado saldo negativo, então o cartão Saldo aparece em destaque de erro.
- [ ] **CA-F07.13** Dado mês sem lançamentos, então "Nenhum lançamento em <mês por extenso>."; com filtros ativos e sem resultado, "Nenhum lançamento com esses filtros." e o botão "Limpar filtros" (CA-03.3).
- [ ] **CA-F07.14** Dado um lançamento registrado pelo diálogo (F-06), então a lista recarrega sozinha e o mostra (CA-01.5).
- [ ] **CA-F07.15** Dado a troca de mês pelo seletor, então a lista busca o mês novo, mantendo os filtros; e durante a recarga o conteúdo anterior continua visível.
- [ ] **CA-F07.16** Dado o tipo "Receitas" escolhido, então o filtro de categoria só oferece categorias de receita; e uma categoria de gasto escolhida antes é limpa.
- [ ] **CA-F07.17** Dado falha ao carregar, então aparece "Não foi possível carregar os lançamentos." (e o banner de F-04, se for 503/sem backend).
- [ ] **CA-F07.18** Dado a janela com menos de 600 px (ex.: 360 px), então a lista aparece em cartões, sem rolagem horizontal e com todos os dados de CA-03.1; e a partir de 600 px, em tabela (RNF-07, Q3).
- [ ] **CA-F07.19** Dado filtros escolhidos, então a URL passa a ter `tipo`/`categoria_id`/`forma_pagamento` (sem nova entrada no histórico); recarregar a página mantém os filtros; valor inválido na URL é descartado; e o link "Lançamentos" do menu abre sem filtros (Q1).
- [ ] **CA-F07.20** Dado um gasto de 42,50 e uma receita de 5.000,00, então aparecem "− R$ 42,50" e "+ R$ 5.000,00", a receita com a classe de cor de receita, e cada valor com `aria-label` que diz o tipo (Q2).

---

## 5. Casos de borda

| # | Caso | Comportamento esperado | Regra |
|---|---|---|---|
| 1 | Lançamento em 31/12/2026 e outro em 01/01/2027 | Um em cada mês. | RN-03 |
| 2 | Gasto no cartão de crédito em 28/09, fatura em outubro | Conta em setembro (mês da compra). | RN-03, P-02 |
| 3 | Dois lançamentos na mesma data | O registrado por último vem primeiro. | §3.1.4 |
| 4 | Filtro de forma ativo e uma receita sem forma no mês | A receita não aparece. | §3.1.3 |
| 5 | `categoria_id=nao-existe` | 200, lista vazia, totais zero. | §3.1.3 |
| 6 | Categoria renomeada de "Mercado" para "Supermercado" | Lançamentos de anos atrás mostram "Supermercado". | CA-11.2 |
| 7 | Categoria inativa | Lançamentos dela continuam na lista, com nome e cor; a categoria aparece no filtro. | CA-11.4 |
| 8 | Categoria apagada à mão na planilha | "Categoria não encontrada", cor cinza. | RN-14 |
| 9 | Linha inválida no mês (valor `0`) | Fora da lista e dos totais; conta em `linhas_ignoradas`. | CA-16.3 |
| 10 | Mil gastos de 0,01 | Total `10.00` exato. | RN-16 |
| 11 | Só receitas no mês | `gastos = 0.00`, saldo = receitas. | RN-13 |
| 12 | Saldo negativo | Cartão Saldo com destaque de erro; valor com sinal de menos. | CA-F07.12 |
| 13 | Registrar um lançamento de **outro** mês estando na listagem | A lista recarrega (versão mudou) mas ele não aparece — é de outro mês. | RN-03 |
| 14 | Descrição muito longa (100 caracteres) | Quebra de linha; sem rolagem horizontal. | RNF-07 |
| 15 | Trocar mês duas vezes rápido | Vale a última resposta; uma resposta antiga que chegue depois é descartada. | §3.2.6 |

---

## 6. Contrato e dados

**API** (`03` §6.1, sem alteração)

| Método | Caminho | Entrada | Saída |
|---|---|---|---|
| GET | `/api/lancamentos` | `?mes=YYYY-MM` (obrig.) `&tipo=&categoria_id=&forma_pagamento=` | `200 ListaLancamentos` · `422` · `503` |

```jsonc
// ListaLancamentos (03 §6.3)
{ "mes": "2026-09", "itens": [Lancamento],
  "totais": { "gastos": 1234.56, "receitas": 5000.00, "saldo": 3765.44 },
  "linhas_ignoradas": 0 }
```

`saldo` pode ser **negativo** (é o único valor monetário que pode). `Lancamento` como em F-06 §6.

**Planilha** — leitura das abas `Lancamentos` e `Categorias` pelo cache; nada é escrito.

---

## 7. Interface

- **Rota:** `/lancamentos?mes=YYYY-MM&tipo=&categoria_id=&forma_pagamento=` (filtros opcionais, Q1).
- **Componentes:** `LancamentosPage` (substitui o placeholder), reuso de `SeletorMes`, `EstadoVazio`, `Carregando`, `CategoriasStore`, `FormasPagamentoStore`, `MesSelecionadoStore`, `DadosStore`. `LancamentosApi.listar`.
- **Mensagens (pt-BR):** "Nenhum lançamento em <mês>.", "Nenhum lançamento com esses filtros.", "Limpar filtros", "Totais dos lançamentos filtrados", "Não foi possível carregar os lançamentos.", "Lançamento recorrente", "Categoria não encontrada".

---

## 8. Plano de testes

| Teste | Nível | Cobre |
|---|---|---|
| `tests/unit/test_lancamento_service.py::test_listar_filtra_pelo_mes__RN_03` | unitário BE | CA-F07.1, bordas 1–2 |
| `…::test_ordem_data_e_criacao_decrescentes__REQ_03` | unitário BE | CA-F07.2, borda 3 |
| `…::test_filtros_combinados_e_totais__CA_03_2` (parametrizado) | unitário BE | CA-03.2, CA-F07.3, bordas 4–5 |
| `…::test_totais_exatos__RN_13_RN_16` | unitário BE | CA-F07.4, bordas 10–12 |
| `…::test_nome_atual_e_categoria_inexistente__CA_11_2` | unitário BE | CA-11.2, CA-F07.6, bordas 6–8 |
| `tests/api/test_lancamentos.py::test_get_formato_de_lista__CA_03_1` | API BE | CA-03.1 (contrato) |
| `…::test_get_422__CA_F07_5` (parametrizado) | API BE | CA-F07.5 |
| `…::test_get_ignora_linha_invalida__CA_16_3` (planilha falsa) | API BE | CA-F07.7, borda 9 |
| `…::test_get_uma_leitura_por_aba__RNF_04` (planilha falsa, 5.000 linhas) | API BE | CA-F07.8 |
| `…::test_get_503__CA_F07_9` | API BE | CA-F07.9 |
| `…::test_post_e_get_ponta_a_ponta__CA_01_5` | API BE | CA-01.5 (API) |
| `frontend/…/core/api/lancamentos.api.spec.ts` › `listar_com_filtros` | unitário FE | §6 |
| `…/features/lancamentos/lancamentos.page.spec.ts` › `mostra_itens_formatados__CA_03_1` | unitário FE | CA-03.1, CA-F07.10 |
| `…` › `filtros_e_totais_da_api__CA_03_2` | unitário FE | CA-03.2, CA-F07.11 |
| `…` › `saldo_negativo_em_destaque__CA_F07_12` | unitário FE | CA-F07.12 |
| `…` › `vazio_com_e_sem_filtro__CA_03_3` | unitário FE | CA-03.3, CA-F07.13 |
| `…` › `recarrega_apos_registro__CA_01_5` | unitário FE | CA-01.5, CA-F07.14, borda 13 |
| `…` › `troca_de_mes_mantem_filtros__CA_F07_15` e `resposta_antiga_descartada` | unitário FE | CA-F07.15, borda 15 |
| `…` › `categoria_depende_do_tipo__CA_F07_16` | unitário FE | CA-F07.16 |
| `…` › `erro_de_carga__CA_F07_17` | unitário FE | CA-F07.17 |
| `…` › `filtros_na_url__CA_F07_19` (inclui valor inválido e recarga) | unitário FE | CA-F07.19 |
| `…` › `valor_com_sinal_e_cor__CA_F07_20` | unitário FE | CA-F07.20 |
| `…` › `tabela_ou_cartoes_por_largura__CA_F07_18` (`BreakpointObserver` simulado) | unitário FE | CA-F07.18 (parte automatizável) |
| `app.spec.ts` (regressão de CA-04.1/04.2 com a página real) | unitário FE | CA-04.1, CA-04.2 |
| Página em 360 px, temas claro e escuro | manual FE | CA-F07.18, borda 14 |

---

## 9. Divisão em tarefas

| Tarefa | Escopo nesta feature | Arquivos principais |
|---|---|---|
| **T-017** (BE) | `lancamento_service.listar` (mês, filtros, ordem, totais em `Decimal`, nome/cor atuais, `linhas_ignoradas`), schema `ListaLancamentosSaida`, `GET /api/lancamentos`, guarda de rotas. | `backend/app/services/lancamento_service.py`, `backend/app/api/{schemas.py,routers/lancamentos.py}`, `backend/tests/unit/test_lancamento_service.py`, `backend/tests/api/{test_lancamentos.py,test_app.py}` |
| **T-018** (FE) | `LancamentosApi.listar`, modelo `ListaLancamentos`, `LancamentosPage` (filtros, totais, lista, estados, recarga). | `frontend/src/app/core/{api/lancamentos.api.ts,models/lancamento.ts}`, `frontend/src/app/features/lancamentos/lancamentos.page.ts` + specs |

Ordem: T-017 → T-018 (T-018 também depende de T-016, concluída).

---

## 10. Decisões tomadas nesta feature

| Decisão | Motivo | Virou ADR? |
|---|---|---|
| Totais calculados sobre os itens **filtrados**. | CA-03.2: "o total exibido corresponde à soma dos itens visíveis". | Não |
| Desempate da ordem por `criado_em` decrescente, depois `id`. | REQ-03 só fixa "data, mais recente primeiro"; o último registrado no topo é o que o usuário espera ver após registrar. | Não |
| Categoria inexistente num lançamento → "Categoria não encontrada", cor `#9E9E9E`. | O contrato exige `categoria_nome`/`categoria_cor`; a linha continua válida (o `categoria_id` é texto) e não pode sumir (RN-14). | Não |
| `categoria_id` desconhecido no filtro → lista vazia (200), não erro. | É um filtro, não uma referência a recurso. | Não |
| Filtro de categoria mostra ativas **e** inativas. | Lançamentos de categorias inativas continuam na listagem (CA-11.4); o usuário precisa poder filtrá-los. | Não |
| Tipo `Montante` (2 casas, zero ou negativo) para `totais` (T-017). | O `Dinheiro` exige > 0 (RN-01) e não serve para saldo; o mesmo tipo atende o resumo de F-09. `02` → 1.10. | Não |
| `LancamentoComCategoria` guarda `categoria_nome`/`categoria_cor` em vez do objeto `Categoria` (T-017, ajuste interno de T-015). | Um lançamento com categoria apagada não tem `Categoria` a montar; criar e listar passam a usar a mesma estrutura, sem mudar a API. | Não |
| Recarga mantém o conteúdo anterior esmaecido; resposta antiga é descartada. | Evita piscar e evita que uma resposta lenta de outro mês sobrescreva a atual. | Não |
| Filtros na URL com `replaceUrl`; o menu leva só o mês (Q1). | Mesmo comportamento do `?mes=` (F-04); recarregar não perde o que o usuário escolheu, e navegar pelo menu recomeça limpo. `03` → 1.20 (§8.1). | Não |
| Valor com sinal e receita em verde, com `aria-label` do tipo (Q2). | O tipo é o que dá direção ao valor (RN-01); cor sozinha não basta para acessibilidade. | Não |
| Tabela a partir de 600 px, cartões abaixo (Q3). | Tabela é mais fácil de varrer no desktop; cartões garantem 360 px sem rolagem horizontal (RNF-07). Mesma quebra do shell. | Não |

---

## 11. Questões em aberto

**Respondidas em 2026-09-30 — nenhuma em aberto.** Em todas, o usuário escolheu a opção recomendada.

- [x] **Q1** → filtros na URL com `replaceUrl`; menu leva só o `?mes=` (§3.2.2). `03` → 1.20.
- [x] **Q2** → "− R$" no gasto, "+ R$" em verde na receita, `aria-label` com o tipo (§3.2.4).
- [x] **Q3** → tabela a partir de 600 px, cartões abaixo (§3.2.4).

---

## Revisões

| Data | Alteração |
|---|---|
| 2026-09-30 | Criação (`/especificar-feature F-07`). Status `Rascunho` — 3 questões em aberto. |
| 2026-09-30 | Q1–Q3 respondidas → status **Aprovada**. CA-F07.18 detalhado; CA-F07.19 (filtros na URL) e CA-F07.20 (sinal e cor do valor) acrescentados. `03` → 1.20. |
| 2026-09-30 | T-017 concluída: CA-F07.1 a .9 verificados por teste (serviço em memória; API com planilha falsa, inclusive 5.000 linhas com uma leitura por aba). CA-11.2 com a parte da API. Duas decisões em §10. `02` → 1.10, `03` → 1.21. |
