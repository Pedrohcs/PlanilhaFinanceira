# F-10 — Gráficos do mês

| Campo | Valor |
|---|---|
| Feature | F-10 |
| Marco | M2 |
| Status | Concluída |
| Requisitos | REQ-13 (CA-13.1, CA-13.2) |
| Regras | RN-16 (nada é somado no frontend) |
| Depende de | F-09 (**Concluída**) |
| Tarefas | T-023 |
| Atualizado em | 2026-09-30 |

> **IDs de critério:** herdados de `01` mantêm o ID original (**CA-13.1** …). Os refinados usam **`CA-F10.y`**.

---

## 1. Objetivo

Ver o mês de relance: a proporção dos gastos por categoria (nas cores de cada categoria), quanto saiu por cada forma de pagamento e como o gasto foi se acumulando dia a dia.

---

## 2. Escopo

**Inclui**
- No `/resumo` (F-09): **rosca** de gastos por categoria, **barras** de gastos por forma de pagamento e **linha** do gasto acumulado dia a dia (REQ-13).
- Dados **só** do `ResumoMensal` que a página já busca (`por_categoria`, `por_forma_pagamento`, `gasto_acumulado_diario`) — nenhuma chamada nova, nenhuma conta (`03` §8.2.1).
- Uso da `GraficoDirective` de F-04 (ADR-11); um ajuste pequeno em `grafico.config.ts` para ler a **cor de destaque** do tema (barras e linha).
- Estado vazio em vez de gráfico quando o mês não tem gastos (CA-13.2).

**Não inclui** (e onde será tratado)
- Gráficos do histórico — **F-11**.
- Comparação com o mês anterior — fora de escopo (Q2).
- Clique no gráfico para filtrar a listagem — fora de escopo (mesma sugestão de F-09).
- Exportar/baixar o gráfico — fora de escopo.

---

## 3. Comportamento detalhado

### 3.1 Onde ficam (Q1: gráfico acima da tabela)

1. **Gastos por categoria**: a rosca entra na seção de F-09, **acima da tabela**, que continua com valores e percentuais exatos.
2. **Gastos por forma de pagamento**: as barras entram na seção de F-09, acima da tabela.
3. **Gasto acumulado no mês**: nova seção, de largura inteira, **abaixo** das duas seções, com título "Gasto acumulado no mês".
4. Em ≥ 960 px as seções de categoria e de forma continuam lado a lado (F-09 §3.2.5); abaixo disso, empilhadas. Os gráficos acompanham a largura do contêiner (`responsive`, sem rolagem horizontal em 360 px — RNF-07), com altura fixa (rosca e barras 240 px; linha 220 px).

### 3.2 Rosca — gastos por categoria

1. Um arco por item de `por_categoria`, na ordem da API; **cor do arco = `cor` da categoria** (CA-13.1), inclusive o cinza `#9E9E9E` de "Categoria não encontrada".
2. Rótulos = `nome`; valor = `total`. Tooltip dos padrões de F-04: "Alimentação: R$ 1.234,56".
3. **Sem legenda do Chart.js**: a tabela logo abaixo, com a bolinha da cor, faz esse papel.

### 3.3 Barras — gastos por forma de pagamento

1. Barras **horizontais** (`indexAxis: 'y'`, nomes longos como "Cartão de crédito" cabem em 360 px), uma por item de `por_forma_pagamento`, na ordem da API.
2. Uma só cor: a de **destaque do tema** (`--mat-sys-primary`, lida como as outras cores do tema em F-04 Q6) — formas de pagamento não têm cor própria.
3. Eixo de valores em reais; tooltip "Pix: R$ 50,00" (padrões de F-04). Sem legenda (uma série só).

### 3.4 Linha — gasto acumulado dia a dia

1. Só o mês selecionado (Q2). Um ponto por item de `gasto_acumulado_diario` (todos os dias do mês — F-09 Q2); rótulos do eixo = número do dia (`1`…`30`).
2. Cor de destaque do tema; área abaixo da linha **sem** preenchimento; pontos pequenos.
3. Tooltip: título "Dia 15", linha "Gasto acumulado: R$ 1.234,56". Eixo de valores em reais, começando em zero. Sem legenda.

### 3.5 Estados

1. **Mês sem gastos** (lançamentos zero ou só receitas): nenhum gráfico; fica o estado vazio de F-09 ("Nenhum lançamento em …" / "Nenhum gasto em …") — CA-13.2. O acumulado (todo zero) também não é desenhado.
2. **Carregando** e **erro**: como em F-09 (nenhum gráfico com dado velho).
3. **Recarga** (troca de mês, `versao`): os gráficos são **atualizados** na mesma instância (a diretiva faz isso — CA-F04.9), não recriados.
4. **Tema claro/escuro**: textos, grades e cor de destaque acompanham o tema (a diretiva relê as cores — CA-F04.30).

### 3.6 Acessibilidade

1. Cada `<canvas>` tem `role="img"` e `aria-label`: "Gráfico de rosca dos gastos por categoria. Os valores estão na tabela abaixo.", "Gráfico de barras dos gastos por forma de pagamento. Os valores estão na tabela abaixo." e "Gráfico de linha do gasto acumulado dia a dia em setembro de 2026: R$ 1.500,00 no fim do mês." (este último com o total do último dia, vindo da API).

---

## 4. Critérios de aceite

**Herdados de `01`**

- [x] **CA-13.1** Dado categorias com cores definidas, então os gráficos usam essas cores.
- [x] **CA-13.2** Dado um mês sem gastos, então os gráficos exibem estado vazio em vez de erro.

**Refinados (T-023)**

- [x] **CA-F10.1** Dado a resposta da API, então a rosca tem os rótulos, os valores e as cores de `por_categoria`, na mesma ordem, sem legenda (CA-13.1).
- [x] **CA-F10.2** Dado a resposta, então as barras são horizontais, com rótulos e valores de `por_forma_pagamento` na ordem da API e a cor de destaque do tema.
- [x] **CA-F10.3** Dado setembro (30 dias), então a linha tem 30 pontos com rótulos `1`…`30` e os valores de `gasto_acumulado_diario`; tooltip "Dia 15" / "Gasto acumulado: R$ …".
- [x] **CA-F10.4** Dado um mês sem lançamentos ou só com receitas, então nenhum `<canvas>` é criado e aparece o estado vazio de F-09 (CA-13.2).
- [x] **CA-F10.5** Dado a troca de mês ou `versao` incrementada, então os mesmos gráficos são atualizados com os dados novos (nenhum gráfico novo é criado).
- [x] **CA-F10.6** Dado os três gráficos, então cada `<canvas>` tem `role="img"` e o `aria-label` de §3.6.
- [x] **CA-F10.7** Dado o tema, então a cor de destaque vem de `--mat-sys-primary` resolvida pelo navegador (como texto e grade em F-04).
- [x] **CA-F10.8** Dado a abertura do app em outra rota, então o Chart.js **não** está no pacote inicial (só no pedaço do `/resumo`), e o pacote inicial não cresce além do orçamento de 500 kB.
- [~] **CA-F10.9** Dado a janela de 360 px e a de 1280 px, então os gráficos cabem sem rolagem horizontal (conferência visual) e as seções seguem o layout de F-09. *(T-023: layout das seções verificado por teste em F-09; "sem rolagem horizontal" e claro/escuro ficam para a conferência visual do usuário.)*

---

## 5. Casos de borda

| # | Caso | Comportamento esperado | Regra |
|---|---|---|---|
| 1 | Uma só categoria com gasto | Rosca com um arco inteiro. | — |
| 2 | Categoria apagada à mão | Arco cinza `#9E9E9E`, rótulo "Categoria não encontrada". | RN-14 |
| 3 | Duas categorias com a mesma cor | Arcos da mesma cor (a tabela desfaz a dúvida). | CA-13.1 |
| 4 | Mês só com receitas | Sem gráficos; "Nenhum gasto em …". | CA-13.2 |
| 5 | Mês sem lançamentos | Sem gráficos; "Nenhum lançamento em …". | CA-13.2 |
| 6 | Fevereiro de 2028 | Linha com 29 pontos. | F-09 Q2 |
| 7 | Mês corrente com gastos só até o dia 10 | Linha sobe até o dia 10 e fica constante até o fim do mês. | F-09 Q2 |
| 8 | Troca rápida de mês | Os gráficos mostram o último mês pedido (resposta antiga descartada — F-09). | F-07 borda 15 |
| 9 | Troca do tema do sistema com o resumo aberto | Cores de texto, grade e destaque mudam sem recarregar. | F-04 Q6 |
| 10 | Nome de forma longo em 360 px | Barras horizontais: o rótulo cabe no eixo vertical. | RNF-07 |

---

## 6. Contrato e dados

**API** — nenhuma chamada nova: `GET /api/resumo/mensal` (F-09, `03` §6.3). Mapeamento:

| Gráfico | `labels` | `data` | cores |
|---|---|---|---|
| Rosca | `por_categoria[].nome` | `por_categoria[].total` | `por_categoria[].cor` |
| Barras | `por_forma_pagamento[].nome` | `por_forma_pagamento[].total` | destaque do tema |
| Linha | `gasto_acumulado_diario[].dia` (texto) | `gasto_acumulado_diario[].total` | destaque do tema |

**Planilha** — nada.

---

## 7. Interface

- **Rota:** `/resumo` (F-09).
- **Componentes:** `ResumoPage` (monta os `ChartData`/`ChartOptions` com `computed`), `GraficoDirective` e `grafico.config.ts` (F-04; ganha a cor de destaque).
- **Estados:** vazio · carregando · erro · recarregando (como F-09) · sucesso.
- **Mensagens (pt-BR):** "Gasto acumulado no mês"; "Dia <n>"; "Gasto acumulado"; `aria-label`s de §3.6.

---

## 8. Plano de testes

| Teste | Nível | Cobre |
|---|---|---|
| `shared/grafico/grafico.config.spec.ts` › `cor_de_destaque_do_tema__CA_F10_7` | unitário FE | CA-F10.7 |
| `features/resumo/resumo.page.spec.ts` › `rosca_com_cores_das_categorias__CA_13_1` (fábrica de gráfico falsa) | unitário FE | CA-13.1, CA-F10.1, borda 2 |
| `…` › `barras_por_forma__CA_F10_2` | unitário FE | CA-F10.2 |
| `…` › `linha_do_acumulado__CA_F10_3` | unitário FE | CA-F10.3, bordas 6–7 |
| `…` › `sem_gastos_sem_graficos__CA_13_2` | unitário FE | CA-13.2, CA-F10.4, bordas 4–5 |
| `…` › `recarga_atualiza_os_mesmos_graficos__CA_F10_5` | unitário FE | CA-F10.5, borda 8 |
| `…` › `graficos_acessiveis__CA_F10_6` | unitário FE | CA-F10.6 |
| `npm run build` (nomes dos pedaços): Chart.js só no pedaço `resumo-page` (193 kB brutos), pacote inicial 476,21 kB | build | CA-F10.8 |
| `shared/grafico/grafico.directive.spec.ts` › `acompanha_troca_de_tema__CA_F04_30` (agora também a cor de destaque) | unitário FE | CA-F10.7, borda 9 |
| Conferência visual em 360 px e 1280 px, claro e escuro | manual | CA-F10.9, bordas 9–10 |

---

## 9. Divisão em tarefas

| Tarefa | Escopo nesta feature | Arquivos principais |
|---|---|---|
| **T-023** (FE) | Rosca, barras e linha no `/resumo`; cor de destaque do tema; estados vazios. | `frontend/src/app/features/resumo/resumo.page.{ts,html,scss,spec.ts}`, `frontend/src/app/shared/grafico/grafico.config{.ts,.spec.ts}`, `frontend/src/app/shared/grafico/grafico.directive.spec.ts` |

---

## 10. Decisões tomadas nesta feature

| Decisão | Motivo | Virou ADR? |
|---|---|---|
| Barras horizontais para formas de pagamento. | Rótulos longos ("Cartão de crédito") cabem em 360 px. | Não |
| Cor única de destaque do tema (`--mat-sys-primary`) para barras e linha; `CoresDoTema` ganha `destaque`. | Formas e dias não têm cor própria; segue o tema claro/escuro como texto e grade (F-04 Q6). | Não |
| Sem legenda do Chart.js nos três gráficos. | Rosca: a tabela com a bolinha da cor já é a legenda; barras e linha têm uma série só. | Não |
| Mês sem gastos: nenhum gráfico, só o estado vazio de F-09. | CA-13.2; uma linha toda em zero não informa nada. | Não |
| `aria-label` descritivo em cada `<canvas>`, apontando para a tabela. | O canvas não é lido por leitor de tela; os valores exatos estão nas tabelas (RNF-07). | Não |
| Gráficos acima das tabelas, que continuam (Q1). | Visão rápida + valores exatos; a tabela é a legenda e a alternativa acessível. | Não |
| Acumulado só do mês selecionado (Q2). | O que REQ-13 pede, sem chamada extra. | Não |
| Cor de destaque posta em `options.elements` (bar/line/point) dos padrões, não nos `datasets` (T-023). | A diretiva refaz as opções na troca de tema; cor nos dados não acompanharia claro/escuro. | Não |

---

## 11. Questões em aberto

**Respondidas em 2026-09-30 — nenhuma em aberto.** Nas duas, o usuário escolheu a opção recomendada.

- [x] **Q1** → gráfico **acima** da tabela em cada seção; as tabelas de F-09 continuam (§3.1).
- [x] **Q2** → a linha mostra **só o mês selecionado**, sem comparação com o mês anterior (§3.4).

---

## Revisões

| Data | Alteração |
|---|---|
| 2026-09-30 | Criação (`/especificar-feature F-10`). Status `Rascunho` — 2 questões em aberto. |
| 2026-09-30 | Q1–Q2 respondidas (ambas na opção recomendada) → status **Aprovada**. Duas decisões em §10. |
| 2026-09-30 | T-023 concluída → feature **Concluída**. CA-13.1, CA-13.2 e CA-F10.1 a .8 verificados por teste/build; CA-F10.9 depende da conferência visual. Uma decisão em §10. |
