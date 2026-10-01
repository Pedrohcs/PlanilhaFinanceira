# F-11 — Histórico

| Campo | Valor |
|---|---|
| Feature | F-11 |
| Marco | M2 |
| Status | Concluída |
| Requisitos | REQ-14 (CA-14.1, CA-14.2, CA-14.3) |
| Regras | RN-03, RN-13, RN-14, RN-16; RNF-04, RNF-07 |
| Depende de | F-09 (**Concluída**); T-025 também usa o núcleo de F-04 (T-011, **Concluída**) e a `GraficoDirective` com a cor de destaque de F-10 (**Concluída**) |
| Tarefas | T-024, T-025 |
| Atualizado em | 2026-10-01 |

> **IDs de critério:** herdados de `01` mantêm o ID original (**CA-14.1** …). Os refinados usam **`CA-F11.y`**.
>
> Marcas **(Qn)** apontam a decisão de §11 que fixou aquele trecho.

---

## 1. Objetivo

Ver como o dinheiro evoluiu mês a mês num intervalo (por padrão, os últimos 12 meses até o corrente): quanto saiu, quanto entrou, o saldo de cada mês e como cada categoria de gasto pesou ao longo do tempo, com o total gasto no período e a média mensal.

---

## 2. Escopo

**Inclui**
- `resumo_service.historico(inicio, fim)` e `GET /api/resumo/historico?inicio=YYYY-MM&fim=YYYY-MM` → `200 ResumoHistorico` (`03` §6.1, §6.3), com padrão "últimos 12 meses até o corrente".
- Página `/historico?inicio=&fim=` (hoje provisória, F-04): seletor de intervalo, cards **Total gasto no período** e **Média mensal de gastos**, gráfico de **gastos × receitas** (barras) com a **linha de saldo**, e **barras empilhadas de gastos por categoria**.
- `ResumoApi.historico`.

**Não inclui** (e onde será tratado)
- Aviso de linhas ignoradas na tela (CA-16.3) — **F-14** (T-032). A API passa a devolver `linhas_ignoradas` também aqui **(Q6)**.
- Receitas por categoria — REQ-14 pede só a evolução de **gastos** por categoria.
- Filtro por tipo/categoria/forma no histórico — fora de escopo.
- Clicar num mês/barra para abrir o resumo ou a listagem daquele mês — fora de escopo (sugestão, como em F-09/F-10).
- Comparação entre períodos, projeções e exportação — fora de escopo.

---

## 3. Comportamento detalhado

### 3.1 Backend — `resumo_service.historico` (T-024)

1. **Entrada:** `inicio` e `fim` no formato `YYYY-MM`, **os dois ou nenhum** **(Q2)**.
   - Nenhum → padrão REQ-14: `fim` = mês corrente (relógio local do backend) e `inicio` = 11 meses antes. Ex.: em 01/10/2026, `2025-11`..`2026-10` (12 meses).
   - Só um deles → 422 `VALIDACAO` no campo que faltou: "Informe o início e o fim do período.".
   - Formato inválido → 422 no campo (`inicio` ou `fim`), como `mes` em F-07/F-09.
   - `inicio` depois de `fim` → 422 no campo `fim`: "O fim do período deve ser igual ou posterior ao início.".
   - Mais de **36 meses** → 422 no campo `fim`: "O período pode ter no máximo 36 meses." **(Q2)**.
   - Mês futuro é aceito (RN-02 aceita datas futuras; parcelas e recorrências podem estar lá).
2. **Leitura:** uma leitura de cada aba pelo cache (`02` §5.5), sem escrita. Linhas inválidas ficam de fora (RN-14).
3. **`meses`** — um item por mês de `inicio` a `fim`, inclusive, em ordem crescente (`meses_entre`, já em `domain/datas.py`), **mesmo sem lançamentos** (CA-14.1). Para cada mês: `total_gastos`, `total_receitas` e `saldo = receitas − gastos`, pela mesma `totalizar` da listagem e do resumo mensal (RN-03, RN-13): o mês `2026-09` do histórico tem **exatamente** os totais de `GET /api/resumo/mensal?mes=2026-09`.
4. **`por_categoria`** — só **gastos** do período:
   - um item por `categoria_id` que tem gasto em **algum** mês do período; categorias sem gasto no período não aparecem;
   - `valores`: um número por mês, **alinhado a `meses`** (mesmo tamanho e ordem), 0 nos meses sem gasto daquela categoria;
   - `nome` e `cor` **atuais** (CA-11.2), inclusive de categoria inativa; categoria apagada à mão → "Categoria não encontrada" e `#9E9E9E` (F-07 §3.1.6, F-09 §3.1.4) — duas categorias apagadas diferentes continuam como dois itens (agrupamento por `categoria_id`, como em F-09);
   - ordem: **total no período** decrescente; empate → nome sem acento/caixa (chave de F-05). Essa ordem é a do empilhamento e da legenda no gráfico.
   - todas as categorias com gasto entram, sem agrupar em "Outras" **(Q4)**.
5. **`total_gastos_periodo`** = soma dos `total_gastos` dos meses (em `Decimal`, RN-16).
6. **`media_mensal_gastos`** = `total_gastos_periodo` ÷ **número de meses do período** (incluindo os meses com zero e os futuros), arredondada para **2 casas** com `ROUND_HALF_UP` **(Q3)**. Ex.: R$ 100,00 em 3 meses → R$ 33,33.
7. **`linhas_ignoradas`** como no `ResumoMensal` **(Q6)**.
8. Período sem nenhum lançamento → 200 com todos os meses em 0, `por_categoria` vazio, total e média 0 (não é erro).
9. Planilha inacessível → 503 com a causa (F-02).
10. O "mês corrente" vem de `mes_corrente()` do domínio, recebido de forma que o teste possa fixar a data (ex.: argumento `hoje` opcional, como em `mes_corrente(hoje)`).

### 3.2 Página `/historico` (T-025)

1. Título "Histórico" e o **seletor de intervalo** **(Q1)**: dois seletores de mês, **"De"** e **"Até"**, cada um abrindo o datepicker na escolha ano → mês (mesmo comportamento do seletor de mês de F-04 Q7), e um botão **"Últimos 12 meses"** que volta ao padrão.
   - Escolher um "De" posterior ao "Até" leva o "Até" para o mesmo mês (e vice-versa); escolher um intervalo com mais de 36 meses **(Q2)** move a outra ponta para caber no limite. Assim a tela nunca pede um intervalo que a API recusaria.
2. **URL:** o intervalo escolhido vai para `?inicio=&fim=` (`03` §8.1) com `replaceUrl`, como os filtros de F-07. Sem parâmetros na URL, a página pede a API **sem** parâmetros e mostra nos seletores o `inicio`/`fim` da resposta (o padrão fica só no backend). Parâmetros inválidos, incompletos, invertidos ou acima do limite são **descartados** (a URL é limpa com `replaceUrl`) e vale o padrão — mesmo critério do `MesSelecionadoStore`.
   - O intervalo do histórico é **independente** do mês selecionado do resumo/listagem (`?mes=`).
3. **Cards** "Total gasto no período" e "Média mensal de gastos", com os números da API, formatados como os demais valores (`R$ 1.234,56`, `formatarMontante` de `core/utils/valor.ts`). Abaixo dos cards, o período por extenso: "De outubro de 2025 a setembro de 2026 (12 meses)." (a contagem é o tamanho de `meses`, não conta de valores).
4. **Gastos e receitas por mês** (CA-14.1): gráfico misto com **duas barras por mês** (Gastos e Receitas) e a **linha do saldo** sobre elas.
   - Rótulos do eixo: mês abreviado com ano, "out/25", "nov/25"… (todos os meses do período, inclusive os com zero).
   - Cores: Gastos = cor de erro do tema (`--mat-sys-error`); Receitas = verde de receita de F-07 (`light-dark(#2e7d32, #81c784)`), que passa a ser um token global (`--cor-receita`); Saldo = cor de destaque do tema (`--mat-sys-primary`, F-10), pelos padrões de `grafico.config.ts`. Gastos e Receitas são duas séries de barras do mesmo gráfico, e os padrões dão uma só cor a todas as barras: por isso a página passa os `dados` como **função das cores do tema** (`CoresDoTema` ganha `gasto` e `receita`), que a diretiva reavalia na troca claro/escuro (T-025; `02` §4).
   - Legenda do Chart.js **visível** (três séries). Tooltip "Gastos: R$ 1.234,56", com título "outubro de 2025". Eixo de valores em reais; o saldo pode ficar negativo, então o eixo não é forçado a começar em zero.
5. **Gastos por categoria ao longo dos meses** (REQ-14): barras **empilhadas**, um conjunto por item de `por_categoria`, na ordem da API, com a **cor da categoria** (CA-13.1 vale aqui também); mesmos rótulos de mês. Legenda visível (as categorias não têm tabela que a substitua). Tooltip "Alimentação: R$ 300,00", com título do mês.
6. **Tabela mês a mês** **(Q5)**, abaixo dos gráficos: colunas Mês, Gastos, Receitas, Saldo (saldo negativo destacado como em CA-12.2), uma linha por item de `meses`. É a alternativa acessível e os valores exatos dos gráficos.
7. **Layout:** em qualquer largura os blocos ficam um abaixo do outro (os gráficos de série temporal precisam da largura toda). Gráficos com altura fixa (260 px) e largura do contêiner; em 360 px nada corta nem rola na horizontal (RNF-07). Com 36 meses as barras afinam, sem rolagem.
8. **Estados:**
   - **Período sem lançamentos:** cards com R$ 0,00 e, no lugar dos gráficos e da tabela, o estado vazio "Nenhum lançamento de outubro de 2025 a setembro de 2026.".
   - **Período só com receitas:** o gráfico de gastos × receitas e a tabela aparecem; no lugar do gráfico por categoria, "Nenhum gasto no período.".
   - **Carregando** na primeira carga (componente de F-04); **recarga** com o conteúdo anterior esmaecido; **erro** → "Não foi possível carregar o histórico." sem números velhos (a causa vai para o banner/aviso pelo interceptor, F-04).
9. **Recarga** (CA-14.2): ao mudar o intervalo e quando `DadosStore.versao` muda; resposta de busca antiga é descartada (F-07 borda 15). Os gráficos são **atualizados** na mesma instância (CA-F04.9), não recriados.
10. O frontend **não soma nem divide nada**: totais, média, saldo e valores por categoria vêm prontos da API (`03` §4.2, §8.2.1). Montar rótulos de mês a partir de `meses[].mes` é formatação, não cálculo.
11. **Chart.js** só no pedaço da página `/historico` (lazy), nunca no pacote inicial (`03` §8.2.1).

---

## 4. Critérios de aceite

**Herdados de `01`**

- [x] **CA-14.1** Dado o intervalo padrão, então aparecem 12 meses, inclusive meses sem lançamentos (com zero). *(T-024: a API devolve os 12 meses com zero — CA-F11.1; T-025: gráfico e tabela com um item por mês da resposta, inclusive os zerados.)*
- [x] **CA-14.2** Dado que o usuário muda o intervalo, então gráficos e totais do período se atualizam.
- [x] **CA-14.3** Dado o período exibido, então são mostrados também total gasto no período e média mensal de gastos. *(T-024: a API devolve total e média — CA-F11.6; T-025: cards com os números da API.)*

**Refinados — backend (T-024)**

- [x] **CA-F11.1** Dado hoje = 01/10/2026 e nenhum parâmetro, quando `GET /api/resumo/historico`, então `inicio` = `2025-11`, `fim` = `2026-10` e `meses` tem 12 itens em ordem crescente, os sem lançamento com 0 (CA-14.1).
- [x] **CA-F11.2** Dado lançamentos em vários meses (gastos e receitas, inclusive parcelas e recorrentes) e lançamentos fora do período, então cada item de `meses` tem os mesmos `total_gastos`, `total_receitas` e `saldo` de `GET /api/resumo/mensal` daquele mês, e nada de fora do período conta (RN-03, RN-13).
- [x] **CA-F11.3** Dado 0,10 + 0,20 somados 3 vezes num mês, então o mês e o total do período saem exatos: R$ 0,90 (RN-16).
- [x] **CA-F11.4** Dado gastos de 3 categorias em meses diferentes, então `por_categoria` traz só gastos, um item por categoria com gasto no período, `valores` com o tamanho de `meses` e 0 onde não houve gasto, nome e cor atuais, em ordem de total no período (empate pelo nome).
- [x] **CA-F11.5** Dado uma categoria inativa com gasto no período e outra apagada à mão, então a inativa aparece com seu nome e a apagada como "Categoria não encontrada" (`#9E9E9E`).
- [x] **CA-F11.6** Dado R$ 100,00 de gastos em um período de 3 meses (dois deles sem lançamento), então `total_gastos_periodo` = 100.00 e `media_mensal_gastos` = 33.33 (Q3) (CA-14.3).
- [x] **CA-F11.7** Dado um período sem lançamentos, então 200 com todos os meses em 0, `por_categoria` vazio, total e média 0.
- [x] **CA-F11.8** Dado só `inicio` ou só `fim`, formato inválido, `inicio` > `fim` ou mais de 36 meses (Q2), então 422 `VALIDACAO` no campo indicado em §3.1.1; dado a planilha inacessível, então 503 com a causa.
- [x] **CA-F11.9** Dado uma linha inválida na aba, então ela não entra em nenhuma soma e `linhas_ignoradas` = 1 (Q6, CA-16.3).
- [x] **CA-F11.10** Dado o histórico de 36 meses com 5.000 lançamentos, então há uma leitura de cada aba (pelo cache), sem escrita (RNF-04).

**Refinados — frontend (T-025)**

- [x] **CA-F11.11** Dado a página aberta sem parâmetros, então a API é chamada sem `inicio`/`fim` e os seletores mostram o período da resposta; dado `?inicio=2026-01&fim=2026-06`, então a API é chamada com esse período.
- [x] **CA-F11.12** Dado parâmetros inválidos, incompletos, invertidos ou acima do limite na URL, então eles são descartados (URL limpa com `replaceUrl`) e vale o padrão.
- [x] **CA-F11.13** Dado a troca de "De"/"Até" ou o botão "Últimos 12 meses", então a URL muda com `replaceUrl`, a API é chamada de novo e gráficos, cards e tabela se atualizam (CA-14.2); "De" depois do "Até" puxa o "Até" junto, e o limite de 36 meses (Q2) é respeitado.
- [x] **CA-F11.14** Dado a resposta, então os cards mostram total e média do período com os números da API, sem conta no frontend (CA-14.3), e o período por extenso com a quantidade de meses.
- [x] **CA-F11.15** Dado a resposta, então o gráfico misto tem um rótulo por item de `meses` ("out/25"…), barras Gastos e Receitas e linha Saldo com os valores da API e as cores de §3.2.4, legenda visível.
- [x] **CA-F11.16** Dado a resposta, então as barras empilhadas têm um conjunto por item de `por_categoria`, na ordem da API, com a cor da categoria e os `valores` alinhados aos meses, legenda visível.
- [x] **CA-F11.17** Dado a resposta, então a tabela mês a mês mostra Mês, Gastos, Receitas e Saldo de cada item de `meses`, com saldo negativo destacado (Q5).
- [x] **CA-F11.18** Dado um período sem lançamentos, então os cards mostram R$ 0,00, nenhum `<canvas>` é criado e aparece "Nenhum lançamento de <início> a <fim>."; dado um período só com receitas, o gráfico por categoria dá lugar a "Nenhum gasto no período.".
- [x] **CA-F11.19** Dado `DadosStore.versao` incrementada, então o histórico é buscado de novo com o mesmo período; uma resposta antiga que chega depois é descartada; os gráficos são atualizados na mesma instância.
- [x] **CA-F11.20** Dado um erro de carga, então aparece "Não foi possível carregar o histórico." e nenhum número ou gráfico velho.
- [x] **CA-F11.21** Dado os dois gráficos, então cada `<canvas>` tem `role="img"` e o `aria-label` de §7.
- [x] **CA-F11.22** Dado a abertura do app em outra rota, então o Chart.js não está no pacote inicial e o pacote inicial fica abaixo do orçamento de 500 kB.
- [~] **CA-F11.23** Dado a janela de 360 px e a de 1280 px, nos temas claro e escuro, então nada corta nem rola na horizontal e as cores acompanham o tema (conferência visual).

---

## 5. Casos de borda

| # | Caso | Comportamento esperado | Regra |
|---|---|---|---|
| 1 | Padrão em janeiro (hoje 15/01/2027) | `2026-02`..`2027-01`: atravessa o ano. | REQ-14 |
| 2 | Gasto em 31/10 e parcela em 01/11 | Cada um no seu mês. | RN-03 |
| 3 | Gastos 0,10 + 0,20 (×3) num mês | 0,90 exato no mês e no período. | RN-16 |
| 4 | `inicio` = `fim` | Um mês só; média = total. | §3.1 |
| 5 | Exatamente 36 meses | Aceito. 37 → 422 no `fim`. | Q2 |
| 6 | Só `inicio` informado | 422 no `fim` ("Informe o início e o fim do período."). | Q2 |
| 7 | `?inicio=2026-09&fim=2026-01` | 422 no `fim`. Na página: descartado, vale o padrão. | §3.1.1, §3.2.2 |
| 8 | `fim` no futuro com parcelas lançadas lá | Os meses futuros mostram as parcelas; entram no total e na média. | RN-02, RN-03, Q3 |
| 9 | Total de R$ 100,00 em 3 meses | Média R$ 33,33 (o frontend não refaz a conta). | Q3, RN-16 |
| 10 | Período só com receitas | `por_categoria` vazio, total e média 0; saldo positivo nos meses. | REQ-14 |
| 11 | Mês só com gastos | Saldo negativo naquele mês; a linha desce abaixo de zero; na tabela, saldo destacado. | RN-13, CA-12.2 |
| 12 | Categoria renomeada no meio do período | Um item só, com o nome novo em todos os meses. | CA-11.2 |
| 13 | Categoria inativa com gasto no período | Aparece normalmente. | RN-12 |
| 14 | Duas categorias apagadas à mão | Dois itens "Categoria não encontrada" cinza (ids diferentes). | RN-14 |
| 15 | 15 categorias com gasto | 15 conjuntos empilhados e 15 entradas na legenda (Q4). | Q4 |
| 16 | Linha com valor inválido na planilha | Ignorada; `linhas_ignoradas` = 1. | CA-16.3 |
| 17 | Troca rápida de intervalo | Fica a resposta do último pedido. | F-07 borda 15 |
| 18 | Registro pelo botão da barra com o histórico aberto | O histórico recarrega com o mesmo período. | CA-01.5 |
| 19 | Link "Histórico" da navegação (sem parâmetros) depois de escolher outro período | Volta ao padrão (o período não é lembrado fora da URL). | §3.2.2 |
| 20 | 36 meses em 360 px | Barras finas, rótulos do eixo pulados pelo Chart.js (`autoSkip`), sem rolagem horizontal. | RNF-07 |

---

## 6. Contrato e dados

**API** (`03` §6.1)

| Método | Caminho | Entrada | Saída |
|---|---|---|---|
| GET | `/api/resumo/historico` | `?inicio=YYYY-MM&fim=YYYY-MM` (os dois ou nenhum; padrão: últimos 12 até o corrente; no máximo 36 meses) | `200 ResumoHistorico` · `422` · `503` |

```jsonc
// ResumoHistorico (03 §6.3), exemplo de 2026-07 a 2026-09
{ "inicio": "2026-07", "fim": "2026-09",
  "meses": [
    { "mes": "2026-07", "total_gastos": 0.00,    "total_receitas": 0.00,    "saldo": 0.00 },
    { "mes": "2026-08", "total_gastos": 1200.00, "total_receitas": 5000.00, "saldo": 3800.00 },
    { "mes": "2026-09", "total_gastos": 1500.00, "total_receitas": 1000.00, "saldo": -500.00 } ],
  "por_categoria": [
    { "categoria_id": "moradia",     "nome": "Moradia",     "cor": "#4FC3F7", "valores": [0.00, 1000.00, 1000.00] },
    { "categoria_id": "alimentacao", "nome": "Alimentação", "cor": "#E57373", "valores": [0.00, 200.00, 500.00] } ],
  "total_gastos_periodo": 2700.00, "media_mensal_gastos": 900.00,
  "linhas_ignoradas": 0 }   // (Q6) campo novo em 03 §6.3
```

**Precisões sobre `03`** (aprovadas; T-024 as aplica):
- §6.1: "os dois ou nenhum" e "no máximo 36 meses" na linha de `GET /api/resumo/historico` (Q2).
- §6.3: `linhas_ignoradas` no `ResumoHistorico` (Q6); regras de ordem de `por_categoria` e da média (§3.1.4–6) na nota abaixo dos esquemas.

**Planilha** — leitura de `Lancamentos` e `Categorias` (cache). Nenhuma escrita, nenhuma coluna nova.

---

## 7. Interface

- **Rota:** `/historico?inicio=YYYY-MM&fim=YYYY-MM` (`03` §8.1).
- **Componentes:** `HistoricoPage` (substitui a provisória; monta `ChartData`/`ChartOptions` com `computed`), `ResumoApi.historico`, modelo `ResumoHistorico` em `core/models/resumo.ts`, seletor de intervalo (Q1), `GraficoDirective` e `grafico.config.ts` (ganha as cores de gasto e receita do tema), `EstadoVazio`, `Carregando` (F-04).
- **Estados:** carregando (1ª carga) · recarregando (esmaecido) · vazio (sem lançamentos / sem gastos) · erro · sucesso.
- **Mensagens (pt-BR):** "Histórico"; "De"; "Até"; "Últimos 12 meses"; "Total gasto no período"; "Média mensal de gastos"; "De <mês> a <mês> (<n> meses)."; "Gastos e receitas por mês"; "Gastos por categoria ao longo dos meses"; "Gastos"; "Receitas"; "Saldo"; "Mês"; "Nenhum lançamento de <mês> a <mês>."; "Nenhum gasto no período."; "Não foi possível carregar o histórico.". Backend: "Informe o início e o fim do período."; "O fim do período deve ser igual ou posterior ao início."; "O período pode ter no máximo 36 meses.".
- **Acessibilidade:** `<canvas>` com `role="img"` e `aria-label`: "Gráfico de barras dos gastos e receitas por mês, com a linha do saldo, de outubro de 2025 a setembro de 2026. Os valores estão na tabela abaixo." e "Gráfico de barras empilhadas dos gastos por categoria em cada mês, de outubro de 2025 a setembro de 2026."; tabela com `<th scope="col">`; seletores com `aria-label` "Mês inicial do período" / "Mês final do período".

---

## 8. Plano de testes

| Teste | Nível | Cobre |
|---|---|---|
| `tests/unit/test_resumo_service.py::test_historico_padrao_ultimos_12__CA_14_1` (parametrizado: out/2026, jan/2027) | unitário BE | CA-14.1, CA-F11.1, borda 1 |
| `…::test_historico_meses_iguais_ao_mensal__CA_F11_2` | unitário BE | CA-F11.2, borda 2 |
| `…::test_historico_somas_exatas__RN_16` | unitário BE | CA-F11.3, borda 3 |
| `…::test_historico_por_categoria_alinhado__CA_F11_4` | unitário BE | CA-F11.4, bordas 12, 15 |
| `…::test_historico_categoria_inativa_e_apagada__CA_F11_5` | unitário BE | CA-F11.5, bordas 13–14 |
| `…::test_historico_total_e_media__CA_14_3` (inclui `inicio` = `fim` e meses futuros) | unitário BE | CA-14.3, CA-F11.6, bordas 4, 8, 9 |
| `…::test_historico_periodo_vazio_e_so_receitas__CA_F11_7` | unitário BE | CA-F11.7, borda 10 |
| `…::test_historico_intervalo_invalido__CA_F11_8` (parametrizado: só um, invertido, 37 meses) · `test_historico_36_meses_aceito__CA_F11_8` | unitário BE | CA-F11.8, bordas 5–7 |
| `tests/api/test_resumo.py::test_get_historico_formato__CA_14_1` · `test_get_historico_padrao__CA_14_1` | API BE | contrato §6, CA-F11.1 |
| `…::test_get_historico_422__CA_F11_8` · `test_get_historico_503__CA_F11_8` | API BE | CA-F11.8 |
| `…::test_historico_linha_invalida_ignorada__CA_16_3` (planilha falsa) | API BE | CA-F11.9, borda 16 |
| `…::test_historico_uma_leitura_por_aba__RNF_04` (planilha falsa, 5.000 linhas, 36 meses) | API BE | CA-F11.10 |
| `tests/api/test_app.py` (guarda de rotas) | API BE | `GET /api/resumo/historico` |
| `frontend/…/core/api/resumo.api.spec.ts` › `historico_com_e_sem_periodo__F11` | unitário FE | §6, CA-F11.11 |
| `…/core/utils/mes.spec.ts` › `mes_abreviado__F11` · `meses_no_periodo_e_somar_meses__F11` | unitário FE | rótulos "out/25"; contagem e ajuste de meses |
| `…/features/historico/periodo.spec.ts` › `sem_parametros_vale_o_padrao__CA_F11_11` · `periodo_valido_da_url__CA_F11_11` · `url_invalida_descartada__CA_F11_12` · `de_e_ate_se_ajustam__CA_F11_13` | unitário FE | CA-F11.11–13, bordas 4–7 |
| `…/shared/grafico/grafico.directive.spec.ts` › `dados_em_funcao_das_cores_do_tema__F11` | unitário FE | §3.2.4 (troca de tema) |
| `…/shared/grafico/grafico.config.spec.ts` › `cores_de_gasto_e_receita_do_tema__F11` (variáveis lidas: `--mat-sys-error`, `--cor-receita`) | unitário FE | §3.2.4 |
| `…/features/historico/historico.page.spec.ts` › `periodo_da_url_ou_padrao__CA_F11_11` | unitário FE | CA-F11.11, borda 19 |
| `…` › `url_invalida_descartada__CA_F11_12` | unitário FE | CA-F11.12, borda 7 |
| `…` › `troca_de_intervalo_recarrega__CA_14_2` | unitário FE | CA-14.2, CA-F11.13 |
| `…` › `total_e_media_da_api__CA_14_3` | unitário FE | CA-14.3, CA-F11.14 |
| `…` › `grafico_gastos_receitas_saldo__CA_14_1` (fábrica de gráfico falsa) | unitário FE | CA-14.1, CA-F11.15, borda 11 |
| `…` › `barras_empilhadas_por_categoria__CA_F11_16` | unitário FE | CA-F11.16, borda 15 |
| `…` › `tabela_mes_a_mes__CA_F11_17` | unitário FE | CA-F11.17, borda 11 |
| `…` › `vazio_e_so_receitas__CA_F11_18` | unitário FE | CA-F11.18, borda 10 |
| `…` › `recarrega_por_versao__CA_F11_19` (inclui resposta antiga descartada) | unitário FE | CA-F11.19, bordas 17–18 |
| `…` › `erro_de_carga__CA_F11_20` | unitário FE | CA-F11.20 |
| `…` › `graficos_acessiveis__CA_F11_21` | unitário FE | CA-F11.21 |
| `npm run build` (nomes dos pedaços): Chart.js só num pedaço lazy (186 kB brutos, compartilhado por resumo e histórico), pacote inicial 477,37 kB | build | CA-F11.22 |
| Conferência visual em 360 px e 1280 px, claro e escuro, com 12 e 36 meses | manual | CA-F11.23, borda 20 |

---

## 9. Divisão em tarefas

| Tarefa | Escopo nesta feature | Arquivos principais |
|---|---|---|
| **T-024** (BE) | `resumo_service.historico` (padrão, validação do intervalo, meses com zero, por categoria alinhado, total e média), schema `ResumoHistoricoSaida`, rota `GET /api/resumo/historico`, guarda de rotas; precisões em `03` §6.1/§6.3. | `backend/app/services/resumo_service.py`, `backend/app/api/routers/resumo.py`, `backend/app/api/schemas.py`, `backend/tests/unit/test_resumo_service.py`, `backend/tests/api/{test_resumo.py,test_app.py}` |
| **T-025** (FE) | `ResumoApi.historico`, modelo, página `/historico` (seletor de intervalo, cards, gráfico misto, barras empilhadas, tabela, vazio, erro, recarga), cores de gasto/receita no `grafico.config.ts`, rótulo de mês abreviado. | `frontend/src/app/core/api/resumo.api.ts`, `frontend/src/app/core/models/resumo.ts`, `frontend/src/app/core/utils/mes.ts`, `frontend/src/app/features/historico/historico.page.{ts,html,scss,spec.ts}`, `frontend/src/app/shared/grafico/grafico.config{.ts,.spec.ts}`, `frontend/src/styles.scss` (token global de receita), `frontend/src/app/features/lancamentos/lancamentos.page.scss` + specs |

Ordem: T-024 → T-025 (T-025 também depende de T-011, concluída).

---

## 10. Decisões tomadas nesta feature

| Decisão | Motivo | Virou ADR? |
|---|---|---|
| Totais de cada mês pela mesma `totalizar` da listagem e do resumo mensal. | Histórico, resumo e listagem nunca podem divergir para o mesmo mês (CA-12.1). | Não |
| Padrão do período calculado só no backend; sem parâmetros, a página mostra o `inicio`/`fim` da resposta. | Uma única fonte para "últimos 12 até o corrente". | Não |
| `por_categoria` agrupado por `categoria_id`, nome e cor atuais, ordem por total no período (empate pelo nome). | Mesmo tratamento de F-09; ordem estável e a categoria maior embaixo da pilha. | Não |
| Intervalo do histórico na URL (`inicio`/`fim`), independente do `?mes=` do resumo e da listagem. | `03` §8.1 já define a rota assim; os dois conceitos não se misturam. | Não |
| Período sem lançamentos: cards com R$ 0,00 e estado vazio no lugar dos gráficos e da tabela; só receitas: só o gráfico por categoria some. | Mesmo padrão de F-09/F-10 (CA-13.2). | Não |
| Gráfico misto (barras gastos/receitas + linha de saldo) num só canvas. | É o que T-025 descreve; os controladores de barra e linha já estão registrados (F-04), sem peso novo. | Não |
| Cores: Gastos = erro do tema, Receitas = verde de F-07 (vira token global), Saldo = destaque do tema. Gastos/Receitas por `dados` em função das cores do tema (a diretiva reavalia na troca de tema); Saldo pelos padrões de `grafico.config.ts`. | Gasto/receita reconhecíveis e coerentes com a listagem; acompanham claro/escuro (F-10 §10). Os padrões dão uma só cor a todas as barras, e cor fixa nos dados não acompanharia o tema (decidido com o usuário em T-025). | Não |
| Formato de `inicio`/`fim` validado na rota (`Query(pattern=MES_PADRAO)`, como `mes`); combinação, ordem e limite no serviço (`periodo_do_historico`), com `ErroValidacao.no_campo` (T-024). | Formato é entrada HTTP; as outras três são regras de F-11 Q2, que ficam em `services` (`03` §4.2). | Não |
| `historico(..., hoje=None)` recebe a data de hoje opcional, como `mes_corrente(hoje)` (T-024). | O padrão "12 meses até o corrente" fica testável com data fixa, inclusive na virada do ano. | Não |
| Lançamentos agrupados por mês uma única vez; `_nome_e_cor` compartilhado entre resumo mensal e histórico (T-024). | 36 meses × 5.000 linhas numa passada; nome/cor de categoria ausente com uma regra só. | Não |
| Legenda visível nos dois gráficos. | Três séries no misto e N categorias no empilhado, sem tabela de categorias que faça o papel de legenda. | Não |
| Regras do período no frontend como funções puras em `features/historico/periodo.ts` (`lerPeriodo`, `comInicio`, `comFim`); o seletor de intervalo fica na pasta da feature (T-025). | Testáveis sem datepicker; só o histórico usa o seletor. | Não |
| Sem período na URL, o seletor só aparece quando a resposta chega (mostra o `inicio`/`fim` dela) (T-025). | O padrão é só do backend (§10); antes da resposta o período não é conhecido. | Não |
| Tabela mês a mês com fonte menor e o nome do mês quebrando entre palavras abaixo de 600 px (T-025). | Quatro colunas com valores em reais em 360 px sem rolagem horizontal (RNF-07); conferência visual pendente. | Não |
| Seletores "De"/"Até" + "Últimos 12 meses" (Q1). | Qualquer intervalo com dois controles já conhecidos (o datepicker de F-04); o atalho cobre o caso mais comum. | Não |
| Intervalo com as duas pontas ou nenhuma, `inicio` ≤ `fim`, no máximo 36 meses (Q2). | Sem padrão "pela metade"; 3 anos ainda cabem legíveis em 360 px. | Não |
| Média dividida por todos os meses do período (Q3). | Coerente com CA-14.1, que mostra os meses zerados; a média é do período exibido. | Não |
| Todas as categorias no empilhado, sem "Outras" (Q4). | Contrato de `03` sem item sintético; cada categoria mantém a própria cor. | Não |
| Tabela mês a mês (Q5). | Valores exatos e alternativa acessível aos gráficos, como em F-09/F-10. | Não |
| `linhas_ignoradas` no `ResumoHistorico` (Q6). | Mesmo contrato do `ResumoMensal`; F-14 avisa em todas as telas. | Não |

---

## 11. Questões em aberto

**Respondidas em 2026-10-01 — nenhuma em aberto.** Em todas, o usuário escolheu a opção recomendada.

- [x] **Q1** → dois seletores de mês **"De"/"Até"** (datepicker ano → mês, como o de F-04) + botão **"Últimos 12 meses"** (§3.2.1).
- [x] **Q2** → `inicio` e `fim` **juntos ou nenhum**, `inicio` ≤ `fim`, no máximo **36 meses** (§3.1.1).
- [x] **Q3** → média dividida por **todos os meses do período**, inclusive os sem gasto e os futuros; 2 casas, `ROUND_HALF_UP` (§3.1.6).
- [x] **Q4** → **todas** as categorias com gasto no período, cada uma com sua cor; sem "Outras" (§3.1.4).
- [x] **Q5** → **tabela mês a mês** (Mês, Gastos, Receitas, Saldo) abaixo dos gráficos (§3.2.6).
- [x] **Q6** → `linhas_ignoradas` **no `ResumoHistorico`**, como no `ResumoMensal` (§3.1.7); T-024 atualiza `03` §6.3.

---

## Revisões

| Data | Alteração |
|---|---|
| 2026-10-01 | Criação (`/especificar-feature F-11`). Status `Rascunho` — 6 questões em aberto. |
| 2026-10-01 | Q1–Q6 respondidas (todas na opção recomendada) → status **Aprovada**. Seis decisões em §10. Precisões em `03` §6.1/§6.3 ficam para T-024. |
| 2026-10-01 | T-024 concluída: CA-F11.1 a .10 verificados por teste (inclui 5.000 linhas e 36 meses com uma leitura por aba); parte da API de CA-14.1 e CA-14.3. `03` → 1.29 (§6.1, §6.3). Três decisões em §10. |
| 2026-10-01 | T-025 (plano): cores de Gastos/Receitas por `dados` em função das cores do tema (§3.2.4, §10), aprovado pelo usuário; `02` → 1.11 (§4), `03` §8.2.1. |
| 2026-10-01 | T-025 concluída → feature **Concluída**. CA-14.1 a 14.3 e CA-F11.11 a .22 verificados por teste/build; CA-F11.23 depende da conferência visual (360 px e 1280 px, claro e escuro, 12 e 36 meses). Três decisões em §10. `03` → 1.30. |
