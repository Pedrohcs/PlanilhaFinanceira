# F-04 — Shell do frontend

| Campo | Valor |
|---|---|
| Feature | F-04 |
| Marco | M0 |
| Status | Concluída |
| Requisitos | REQ-01 (botão global, CA-01.1 parcial), REQ-04 (CA-04.1, CA-04.2), REQ-16 (CA-16.1, CA-16.2 no frontend), RNF-03, RNF-07 |
| Regras | — (nenhuma RN de negócio; o frontend não calcula totais, `02` §4) |
| Depende de | F-01 (**Concluída**), F-02 (**Concluída**) |
| Tarefas | T-010, T-011, T-012 |
| Atualizado em | 2026-09-30 |

> **IDs de critério:** herdados de `01` mantêm o ID original (**CA-01.1**, **CA-04.1**, …). Os refinados usam **`CA-F04.y`**.

---

## 1. Objetivo

Dar ao usuário um aplicativo que abre, se navega e se explica: as cinco telas acessíveis por um menu, a ação "Registrar gasto" sempre à mão, o mês escolhido preservado entre resumo e listagem e, quando a planilha ou o servidor não respondem, uma mensagem clara com "Tentar novamente" — sem travar o app. Também deixa pronta a infraestrutura comum (gráficos, erros, estado, componentes) que as telas de M1 e M2 vão usar.

---

## 2. Escopo

**Inclui**
- Shell (`app.ts`, classe `App`): barra superior com "Registrar gasto" (primário) e "Registrar receita", navegação lateral, área de conteúdo e banner de conexão (`03` §8.1).
- Rotas lazy das 5 páginas, como **placeholders** (`03` §8.1).
- `GraficoDirective` + `grafico.config.ts` em `shared/grafico/` (`02` §4, ADR-11).
- `core/`: modelos base (`ErroApi`, tipos dos enums, resposta do health), `erro.interceptor.ts`, `ConexaoStore`, `MesSelecionadoStore`, `DadosStore`, `utils/mes.ts`, serviço HTTP do health.
- Componentes compartilhados: `seletor-mes`, `confirmacao-dialog`, `estado-vazio`, `carregando`, banner de conexão.
- Verificação de conexão na abertura (`provideAppInitializer` → `GET /api/health`) e "Tentar novamente" (`03` §7.2).

**Não inclui** (e onde será tratado)
- Ação dos botões "Registrar gasto"/"Registrar receita" (abrir o formulário) — **F-06** / T-016. Em F-04 eles existem e ficam visíveis, sem ação.
- Conteúdo real das páginas (cards, tabelas, gráficos, formulários) — F-05, F-07, F-09, F-10, F-11, F-13.
- `CategoriasStore` — **F-05** / T-014 (`03` §8.2).
- Sincronização de recorrências na abertura (segunda metade de `03` §7.2) — **F-13** / T-030.
- Aviso de `linhas_ignoradas` na interface (CA-16.3) e botão "Recarregar dados" — **F-14** / T-032.
- Revisão final de acessibilidade, responsividade de cada tela e auto-hospedagem das fontes (sugestão de T-003) — **F-14** / T-031.
- Datepicker de **data** nos formulários — **F-06**. Aqui `provideNativeDateAdapter()` + `MAT_DATE_LOCALE = 'pt-BR'` (`02` §4) já entram, porque o seletor de mês usa o datepicker (Q7).

---

## 3. Comportamento detalhado

### 3.1 Shell e navegação (T-010)

1. O shell ocupa a janela toda: **barra superior** fixa, **navegação lateral** e a área de conteúdo com o `<router-outlet>` (`03` §8.1).
2. Barra superior, da esquerda para a direita: botão de menu ☰ (só quando a navegação está recolhida, item 7) · título "Planilha Financeira" · espaço · **"Registrar gasto"** (botão preenchido, cor primária) · "Registrar receita" (botão de contorno). Os dois botões aparecem **em todas as rotas** (REQ-01).
3. Navegação lateral, nesta ordem, com ícone Material Symbols e rótulo:

   | Rótulo | Rota | Ícone |
   |---|---|---|
   | Resumo | `/resumo` | `dashboard` |
   | Lançamentos | `/lancamentos` | `receipt_long` |
   | Histórico | `/historico` | `bar_chart` |
   | Categorias | `/categorias` | `sell` |
   | Recorrências | `/recorrencias` | `event_repeat` |

   O item da rota atual fica destacado e marcado com `aria-current="page"`.
4. Rotas (`03` §8.1), todas com `loadComponent` (lazy, `02` §4):
   - `/` → redireciona para `/resumo`;
   - `/resumo`, `/lancamentos`, `/historico`, `/categorias`, `/recorrencias` → página da feature;
   - rota desconhecida → redireciona para `/resumo` (Q2).
5. Título da aba do navegador por rota: `"<Página> · Planilha Financeira"` (ex.: "Lançamentos · Planilha Financeira"), via `title` da rota.
6. **Placeholders:** cada página mostra o nome dela como título (`<h1>`) e o texto "Esta tela ainda está em construção." Resumo e Lançamentos também mostram o `seletor-mes` (a partir de T-011), para que CA-04.1/CA-04.2 sejam verificáveis já em F-04.
7. **Janela estreita (RNF-07, Q1):** a partir de 360 px de largura, nada rola na horizontal e todas as ações continuam alcançáveis. Pontos de quebra, detectados com o `BreakpointObserver` do CDK:

   | Largura | Navegação lateral | Barra superior |
   |---|---|---|
   | ≥ 960 px | fixa, sempre aberta (`mode="side"`) | ☰ oculto · título · "Registrar gasto" · "Registrar receita" |
   | 600–959 px | recolhida; abre **por cima** do conteúdo pelo ☰ (`mode="over"`) e fecha ao escolher um item ou clicar fora | ☰ · título · "Registrar gasto" · "Registrar receita" |
   | < 600 px | igual à anterior | ☰ · **sem título** · "+ Gasto" (primário) · "+ Receita" — ícone `add` + rótulo curto; o `aria-label` mantém "Registrar gasto"/"Registrar receita" |

### 3.2 Gráficos — `GraficoDirective` (T-010)

Implementa exatamente `02` §4:

1. Diretiva standalone aplicada a um `<canvas>`, com entradas `input()`: `tipo` (`'doughnut' | 'bar' | 'line'`, obrigatória), `dados` (`ChartData`, obrigatória) e `opcoes` (`ChartOptions`, opcional).
2. Cria o `Chart` **uma vez**, em `afterNextRender`. Se a diretiva for destruída antes disso (navegação rápida), o gráfico não é criado.
3. Mudança em `dados` ou `opcoes` → atualiza a **mesma** instância (`chart.data = …; chart.options = …; chart.update()`), via `effect`. Mudança em `tipo` → destrói e recria.
4. Destruição da diretiva → `chart.destroy()` pelo `DestroyRef`.
5. `grafico.config.ts` registra **só** o necessário: controllers `DoughnutController`, `BarController`, `LineController`; elementos `ArcElement`, `BarElement`, `LineElement`, `PointElement`; escalas `CategoryScale`, `LinearScale`; plugins `Tooltip`, `Legend`. Nenhum `registerables`.
6. Padrões pt-BR no mesmo arquivo: valores em tooltips e no eixo de valores formatados como `R$ 1.234,56` (`Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })`), exportado como `formatarReais` para as páginas reaproveitarem. Só formata — nenhum total é calculado no frontend.
7. **Tema claro/escuro (F-01 Q2, Q6):** ao criar cada gráfico, `grafico.config.ts` lê do `document.body` as variáveis do tema Material — `--mat-sys-on-surface` para texto, legenda e rótulos dos eixos, e `--mat-sys-outline-variant` para a grade — e as aplica nas opções padrão. A diretiva escuta `matchMedia('(prefers-color-scheme: dark)')`: quando o sistema troca de tema com o app aberto, relê as cores e chama `update()` no **mesmo** gráfico. O ouvinte é removido na destruição. As cores das séries (categorias) vêm dos dados e não mudam.
8. A criação do `Chart` passa por um token de injeção (`FABRICA_GRAFICO`) cujo padrão é `new Chart(canvas, config)`. Motivo: o jsdom dos testes não tem `<canvas>` funcional, e trocar a fábrica por um dublê evita dependência nova (decisão §10).

### 3.3 Erros da API (T-011)

1. `erro.interceptor.ts` (funcional) converte toda resposta de erro em `ErroApi` e **relança** — quem chamou continua recebendo o erro:
   ```ts
   interface ErroApi {
     status: number;          // HTTP (0 quando não houve resposta)
     codigo: string;          // `03` §6.2, ou o local `BACKEND_INDISPONIVEL` (§3.3.4)
     mensagem: string;        // pt-BR, pronta para exibir
     detalhes: { campo: string; mensagem: string }[];
   }
   ```
2. Destino por tipo de erro (`03` §8.4):

   | Resposta | O que acontece |
   |---|---|
   | 503 (qualquer código de `03` §6.2) | `ConexaoStore` passa a "falha" com a `mensagem` → banner. Sem snackbar. |
   | 422 `VALIDACAO` | Nada global: o erro chega ao formulário, que marca os campos por `detalhes[].campo`. Sem snackbar. |
   | Demais (404, 409, 500) | Snackbar com a `mensagem`, botão "Fechar", 5 s. |
   | Sem resposta (status 0), ou 502/504 fora do formato §6.2 (backend desligado; o proxy do `ng serve` devolve **502** em `text/plain` — conferido em T-012) | `ErroApi` **local** com `codigo: "BACKEND_INDISPONIVEL"` e a mensagem de §3.3.4 → `ConexaoStore` em `'falha'` → **mesmo banner**, com "Tentar novamente". Sem snackbar (Q3). |
| Qualquer outro status com corpo fora do formato §6.2 (ex.: 500 com HTML) | Snackbar com "Erro interno. Consulte o log do servidor." (a mesma mensagem genérica do backend, `03` §6.2). |
3. A mensagem exibida é **a do backend, sem reescrita** — as de conexão foram escritas para isso (F-02 §7).
4. **Código local `BACKEND_INDISPONIVEL`** (Q3) — só existe no frontend, nunca vem da API. Mensagem: "O servidor do aplicativo não está respondendo. Verifique se o backend está rodando e tente novamente." Registrado em `03` §8.4.

### 3.4 Estado (T-011)

1. **`MesSelecionadoStore`** (`03` §8.2) — `signal<string>` no formato `YYYY-MM`:
   - Sem `?mes=` na URL → mês corrente do relógio local (CA-04.1).
   - `?mes=` válido → é o mês selecionado.
   - `?mes=` inválido (`2026-13`, `abc`, vazio) → mês corrente, e a URL é corrigida sem criar entrada no histórico.
   - Escolher o mês pelo datepicker (Q7) segue a mesma regra de troca abaixo.
   - Trocar o mês atualiza `?mes=` na URL **substituindo** a entrada do histórico (`replaceUrl`), para o botão Voltar não percorrer mês a mês (decisão §10).
   - Os links de Resumo e Lançamentos na navegação levam o `?mes=` atual, então trocar entre as duas telas mantém o mês (CA-04.2). Histórico, Categorias e Recorrências não recebem `?mes=`.
   - Qualquer mês válido é aceito, passado ou futuro (REQ-04 não limita).
2. **`DadosStore`** — `versao = signal(0)`, com `incrementar()`. As páginas reagem a ele para recarregar (`03` §7.1). Em F-04 quem incrementa é o "Tentar novamente" bem-sucedido (§3.6.5, Q5).
3. **`ConexaoStore`** — estado `'verificando' | 'ok' | 'falha'`, mais a `mensagem` da última falha. `'verificando'` é só interno: não há indicador na tela (Q4). Métodos: `verificar()` (chama o health), `registrarFalha(erro: ErroApi)`. É a única fonte do banner.

### 3.5 Utilitários de mês e componentes compartilhados (T-011)

1. `utils/mes.ts`: `mesCorrente()`, `proximoMes(m)`, `mesAnterior(m)`, `mesValido(m)`, `mesPorExtenso(m)` → `"setembro de 2026"` (RNF-03, `Intl.DateTimeFormat('pt-BR', { month: 'long', year: 'numeric' })`). Aritmética de mês no frontend é permitida — não é total.
2. **`seletor-mes`**: mostra o mês por extenso entre os botões "Mês anterior" (‹) e "Próximo mês" (›), ambos com `aria-label`. Lê e escreve no `MesSelecionadoStore`. **Escolher um mês (REQ-04, Q7):** o nome do mês é um botão (`aria-label` "Escolher mês") que abre o `mat-datepicker` com `startView="multi-year"`; o usuário escolhe o ano e depois o mês, e o datepicker **fecha ao escolher o mês** (evento `monthSelected`), sem passar pela visão de dias. O mês que já estava selecionado vem marcado ao abrir. Para isso, `app.config.ts` passa a ter `provideNativeDateAdapter()` e `MAT_DATE_LOCALE = 'pt-BR'` (`02` §4), com nomes de mês em português.
3. **`confirmacao-dialog`**: diálogo Material que recebe `{ titulo, mensagem, textoConfirmar }` e fecha com `true` (confirmar) ou `false` (cancelar, Esc ou clique fora). O foco inicial fica em **"Cancelar"**, para Enter não excluir nada por engano. Será usado por CA-06.1 (T-020).
4. **`estado-vazio`**: ícone + mensagem (`input()`), para as listas vazias (ex.: CA-03.3).
5. **`carregando`**: indicador de progresso com texto opcional, `role="status"`.
6. **Banner de conexão**: faixa no topo da área de conteúdo, abaixo da barra superior, visível quando `ConexaoStore` está em `'falha'`. Mostra a `mensagem` e o botão **"Tentar novamente"**. Não tem botão de fechar (`03` §7.2: "banner persistente").

### 3.6 Abertura do aplicativo e "Tentar novamente" (T-012)

1. Na abertura, `provideAppInitializer` dispara **um** `GET /api/health` (`03` §7.2) e **não espera** a resposta: o inicializador retorna na hora e as telas renderizam imediatamente, sem indicador de "verificando" (Q4). **A falha não impede o app de abrir.**
2. `status: "ok"` → `ConexaoStore` = `'ok'`; nenhum banner.
3. `status: "degradado"` → `ConexaoStore` = `'falha'` com `planilha.erro.mensagem` → banner. Ex.: "Compartilhe a planilha com robo@….iam.gserviceaccount.com como Editor." (CA-16.1).
4. Backend inalcançável → banner com a mensagem de `BACKEND_INDISPONIVEL` (§3.3.4).
5. "Tentar novamente" chama `GET /api/health` de novo, que no backend faz nova tentativa de conexão (F-02 §3.5). Durante a chamada, o botão fica desabilitado com o texto "Tentando…" — cliques repetidos não geram requisições em paralelo.
   - Sucesso (Q5) → o banner some, um snackbar mostra "Conexão com a planilha restabelecida." (4 s) e `DadosStore.incrementar()` faz a tela atual recarregar os dados. **Só o health tira o banner** — uma chamada de negócio bem-sucedida não o esconde.
   - Falha → o banner continua, com a mensagem nova (pode mudar, ex.: de "sem internet" para "sem permissão").
6. Um 503 de qualquer outra chamada durante o uso também põe o banner (§3.3). Só um banner existe por vez, e ele mostra a mensagem mais recente.

---

## 4. Critérios de aceite

**Herdados de `01`**

- [x] **CA-01.1** *(parcial — só a visibilidade)* Dado qualquer tela aberta, quando o usuário procura a ação, então "Registrar gasto" está visível. A abertura do formulário com a data de hoje é verificada em F-06 (T-016).
- [x] **CA-04.1** Dado o aplicativo recém-aberto, quando o usuário entra no resumo ou na listagem, então o mês corrente é exibido.
- [x] **CA-04.2** Dado um mês selecionado, quando o usuário troca entre resumo e listagem, então o mesmo mês permanece selecionado.
- [x] **CA-16.1** *(lado do frontend)* Dado que a planilha não foi compartilhada com o sistema, quando o app abre, então o banner mostra a mensagem do backend indicando que é preciso compartilhá-la, com o `client_email`.
- [x] **CA-16.2** *(lado do frontend)* Dado uma falha temporária, quando o usuário clica "Tentar novamente" e a planilha volta a responder, então o banner some sem reiniciar o aplicativo.

**Refinados — shell e gráficos (T-010)**

- [x] **CA-F04.1** Dado a URL `/`, quando o app abre, então a rota ativa é `/resumo`.
- [x] **CA-F04.2** Dado cada uma das 5 rotas de `03` §8.1, quando é acessada, então a página correspondente abre com seu título, e o componente dela é carregado sob demanda (`loadComponent`, fora do bundle inicial).
- [x] **CA-F04.3** Dado qualquer uma das 5 rotas, quando a tela é renderizada, então a barra superior mostra "Registrar gasto" (botão primário) e "Registrar receita".
- [x] **CA-F04.4** Dado a navegação lateral, quando é renderizada, então tem os 5 itens de §3.1 na ordem da tabela, e só o da rota atual tem `aria-current="page"`.
- [x] **CA-F04.5** Dado cada rota, quando ela está ativa, então o título da aba do navegador é `"<Página> · Planilha Financeira"`.
- [x] **CA-F04.6** Dado uma rota desconhecida (ex.: `/xyz`), quando é acessada, então a rota ativa passa a ser `/resumo` (Q2).
- [~] **CA-F04.7** Dado uma janela de 360 px de largura, quando qualquer rota é exibida, então não há rolagem horizontal, a navegação abre pelo ☰, e "+ Gasto"/"+ Receita" estão visíveis com `aria-label` completo; com ≥ 960 px a navegação fica fixa e o ☰ some (RNF-07, Q1). *(T-010: comportamento por largura verificado por teste, com os limites; "sem rolagem horizontal" em 360 px depende da conferência visual no navegador — pendente.)*
- [x] **CA-F04.8** Dado um `<canvas>` com a `GraficoDirective`, quando o componente termina de renderizar, então **um** gráfico é criado com o `tipo`, os `dados` e as `opcoes` recebidos.
- [x] **CA-F04.9** Dado um gráfico criado, quando `dados` ou `opcoes` mudam, então a **mesma** instância é atualizada (`update()`), sem recriar; quando `tipo` muda, a instância anterior é destruída e outra é criada.
- [x] **CA-F04.10** Dado um gráfico criado, quando o componente é destruído, então `destroy()` é chamado; e se o componente for destruído antes da primeira renderização, nenhum gráfico é criado.
- [x] **CA-F04.11** Dado `grafico.config.ts`, quando carregado, então estão registrados os controllers de rosca, barra e linha, `Tooltip` e `Legend`, e **não** estão registrados controllers não usados (ex.: `radar`, `pie`, `polarArea`).
- [x] **CA-F04.12** Dado o valor 1234.56, quando formatado pelo `formatarReais` usado em tooltips e eixos, então o texto é `R$ 1.234,56` (RNF-03).
- [~] **CA-F04.30** Dado um gráfico criado, quando o sistema troca entre claro e escuro, então as cores de texto e de grade passam às do tema novo, lidas das variáveis Material, na **mesma** instância; e o ouvinte da troca é removido quando a diretiva é destruída (Q6). *(T-010: mesma instância, releitura e remoção do ouvinte verificadas por teste com dublês; a resolução real das cores `light-dark()` pelo navegador depende da conferência visual — pendente, e só fica observável quando uma página usar gráfico, em T-023.)*

**Refinados — core e componentes (T-011)**

- [x] **CA-F04.13** Dado uma resposta de erro no formato de `03` §6.2, quando passa pelo interceptor, então quem chamou recebe um `ErroApi` com `status`, `codigo`, `mensagem` e `detalhes` iguais aos do corpo.
- [x] **CA-F04.14** Dado uma resposta 503, quando passa pelo interceptor, então o `ConexaoStore` vai para `'falha'` com a mensagem, e nenhum snackbar é aberto.
- [x] **CA-F04.15** Dado uma resposta 422, quando passa pelo interceptor, então nenhum snackbar é aberto e o erro chega a quem chamou com os `detalhes`.
- [x] **CA-F04.16** Dado uma resposta 404, 409 ou 500, quando passa pelo interceptor, então um snackbar mostra a `mensagem` do backend.
- [x] **CA-F04.17** Dado que o backend não responde (erro de rede ou 502/504 sem o envelope), quando uma chamada falha, então quem chamou recebe um `ErroApi` com `codigo` `BACKEND_INDISPONIVEL`, o `ConexaoStore` vai para `'falha'` com a mensagem de §3.3.4, e nenhum snackbar é aberto (Q3).
- [x] **CA-F04.18** Dado a URL `/lancamentos?mes=2026-13` (ou `?mes=abc`), quando a tela abre, então o mês selecionado é o corrente e a URL passa a ter o mês corrente, sem nova entrada no histórico.
- [x] **CA-F04.19** Dado o seletor em "dezembro de 2026", quando o usuário clica "Próximo mês", então passa a "janeiro de 2027" e a URL tem `?mes=2027-01`; "Mês anterior" a partir de "janeiro de 2027" volta a "dezembro de 2026".
- [x] **CA-F04.20** Dado um mês, quando exibido pelo seletor, então aparece por extenso em pt-BR: `2026-09` → "setembro de 2026" (RNF-03).
- [x] **CA-F04.31** Dado o seletor em "setembro de 2026", quando o usuário clica no nome do mês e escolhe março de 2025 no datepicker, então o datepicker fecha sem mostrar dias, o seletor passa a "março de 2025" e a URL tem `?mes=2025-03` (REQ-04, Q7).
- [x] **CA-F04.21** Dado o `confirmacao-dialog` aberto, quando o usuário confirma, então fecha com `true`; quando cancela, aperta Esc ou clica fora, fecha com `false`; e ao abrir o foco está em "Cancelar".
- [x] **CA-F04.22** Dado `DadosStore.incrementar()`, quando chamado, então `versao` aumenta 1.

**Refinados — abertura e reconexão (T-012)**

- [x] **CA-F04.23** Dado o app abrindo, quando o inicializador roda, então é feito exatamente **um** `GET /api/health`, e o inicializador termina **sem esperar** a resposta (Q4).
- [x] **CA-F04.24** Dado health `ok`, quando a resposta chega, então nenhum banner aparece.
- [x] **CA-F04.25** Dado health `degradado`, quando a resposta chega, então o banner mostra `planilha.erro.mensagem` e o botão "Tentar novamente", e as rotas continuam navegáveis.
- [x] **CA-F04.26** Dado o banner visível, quando o usuário clica "Tentar novamente", então sai **um** novo `GET /api/health`, o botão fica desabilitado ("Tentando…") até a resposta, e cliques durante a espera não geram outra requisição.
- [x] **CA-F04.27** Dado "Tentar novamente" com resposta `ok`, quando a resposta chega, então o banner some, o snackbar "Conexão com a planilha restabelecida." aparece e `DadosStore.versao` aumenta 1 (Q5).
- [x] **CA-F04.28** Dado "Tentar novamente" com nova falha, quando a resposta chega, então o banner continua, com a mensagem nova.
- [x] **CA-F04.29** Dado o backend desligado, quando o app abre, então as telas renderizam normalmente e o banner com a mensagem de `BACKEND_INDISPONIVEL` aparece — o app **não** fica em branco nem travado (`03` §7.2).

---

## 5. Casos de borda

| # | Caso | Comportamento esperado | Regra |
|---|---|---|---|
| 1 | URL `/` | Redireciona para `/resumo`. | `03` §8.1 |
| 2 | URL `/xyz` | Redireciona para `/resumo`. | Q2 |
| 3 | `/resumo?mes=2026-13` | Mês corrente; URL corrigida com `replaceUrl`. | REQ-04 |
| 4 | `/resumo?mes=` (vazio) | Mês corrente; URL corrigida. | REQ-04 |
| 5 | `/resumo?mes=1999-01` | Aceito: janeiro de 1999. | REQ-04 |
| 6 | Seletor em `2026-12` → Próximo | `2027-01`, "janeiro de 2027". | REQ-04 |
| 7 | Seletor em `2027-01` → Anterior | `2026-12`. | REQ-04 |
| 8 | Em `/resumo?mes=2026-05`, clicar "Lançamentos" no menu | Abre `/lancamentos?mes=2026-05`. | CA-04.2 |
| 9 | Em `/lancamentos?mes=2026-05`, clicar "Categorias" e depois "Resumo" | Volta a `/resumo?mes=2026-05` (o store guarda o mês). | CA-04.2 |
| 10 | App aberto em 31/12 às 23:59 e usado depois da meia-noite | O mês selecionado não muda sozinho; "mês corrente" só é recalculado ao abrir sem `?mes=`. | REQ-04 |
| 11 | Janela com 360 px | Sem título na barra; ☰ + "+ Gasto" + "+ Receita"; sem rolagem horizontal. | RNF-07, Q1 |
| 11a | Janela com exatamente 600 px / 960 px | 600 px já mostra o título e os rótulos completos; 960 px já fixa a navegação (limites inclusivos). | Q1 |
| 12 | Health demora 10 s (Google lento) | App já navegável desde o início; o banner só aparece se a resposta vier com falha. | `03` §7.2, Q4 |
| 13 | Backend desligado, `ng serve` ligado | O proxy responde **502** em `text/plain`, sem o envelope (conferido em T-012; 504 tratado igual) → `BACKEND_INDISPONIVEL` → banner. | CA-F04.17 |
| 14 | Dois 503 quase simultâneos | Um só banner, com a mensagem do último. | §3.6.6 |
| 15 | Duplo clique em "Tentar novamente" | Uma só requisição. | CA-F04.26 |
| 16 | Health volta `ok`, mas logo depois um endpoint dá 503 | O banner volta com a nova mensagem. | §3.3 |
| 17 | Gráfico com `dados` sem nenhum valor | O gráfico é criado vazio; mostrar "sem dados" é da página (`estado-vazio`). | `03` §8.2.1 |
| 18 | Sair da tela antes do primeiro render do gráfico | Nenhum `Chart` é criado; nada vaza. | CA-F04.10 |
| 19 | Sistema troca de claro para escuro com o app aberto | Gráficos visíveis releem as cores do tema e atualizam na mesma instância. | F-01 Q2, Q6 |
| 20 | Resposta 500 com corpo HTML (fora do envelope) | Snackbar com "Erro interno. Consulte o log do servidor." — só 0/502/504 contam como backend fora do ar. | `03` §6.2, Q3 |
| 21 | Datepicker aberto e o usuário aperta Esc | Fecha sem trocar o mês. | Q7 |
| 22 | "Tentar novamente" bem-sucedido estando em `/categorias` | Banner some; a página reage a `versao` (em F-04 o placeholder não recarrega nada — o efeito aparece a partir de F-05). | Q5 |

---

## 6. Contrato e dados

**API** — F-04 consome **só** o health e o formato de erro; não cria nem altera endpoint.

| Método | Caminho | Entrada | Saída |
|---|---|---|---|
| GET | `/api/health` | — | `200 {status, planilha: {ok, titulo, erro?}}` — sempre 200 |

Esquema (`03` §6.3), espelhado em `core/models/` sem mapeamento (ADR-09):

```ts
interface RespostaHealth {
  status: 'ok' | 'degradado';
  planilha: { ok: boolean; titulo: string | null; erro: { codigo: string; mensagem: string } | null };
}
```

Formato de erro das demais respostas ≥ 400 (`03` §6.2), convertido em `ErroApi` (§3.3):

```jsonc
{ "erro": { "codigo": "VALIDACAO", "mensagem": "...", "detalhes": [{ "campo": "valor", "mensagem": "..." }] } }
```

Tipos dos enums (`03` §5.5), só como uniões de string — **sem** rótulos no frontend, que vêm do backend (`GET /api/formas-pagamento`, T-015) para não duplicar a fonte (decisão §10):

```ts
type TipoLancamento = 'GASTO' | 'RECEITA';
type FormaPagamento = 'PIX' | 'CREDITO' | 'DEBITO' | 'DINHEIRO' | 'BOLETO' | 'TRANSFERENCIA';
type StatusRecorrencia = 'ATIVA' | 'PAUSADA' | 'ENCERRADA';
```

**Planilha** — nenhuma aba ou coluna é lida ou escrita diretamente (o frontend nunca fala com o Google).

---

## 7. Interface

- **Shell:** barra superior + navegação lateral + banner + `<router-outlet>` (§3.1, §3.5.6).
- **Rotas:** `/resumo`, `/lancamentos`, `/historico`, `/categorias`, `/recorrencias` como placeholders; `/` → `/resumo`.
- **Componentes:** `App`, 5 páginas placeholder, `GraficoDirective`, `SeletorMes`, `ConfirmacaoDialog`, `EstadoVazio`, `Carregando`, `BannerConexao`.
- **Estados:** verificando conexão (sem indicador, Q4) · ok · falha (banner) · tentando de novo ("Tentando…").
- **Mensagens ao usuário (pt-BR):**
  - Banner: a `mensagem` do backend, sem reescrita; botão "Tentar novamente" / "Tentando…".
  - Backend fora do ar (banner): "O servidor do aplicativo não está respondendo. Verifique se o backend está rodando e tente novamente."
  - Reconexão bem-sucedida (snackbar, 4 s): "Conexão com a planilha restabelecida."
  - Barra em < 600 px: "+ Gasto", "+ Receita".
  - Snackbar: a `mensagem` do backend + "Fechar".
  - Placeholder: "Esta tela ainda está em construção."
  - `aria-label`: "Abrir menu", "Mês anterior", "Próximo mês", "Escolher mês", "Registrar gasto", "Registrar receita".

---

## 8. Plano de testes

Unitários com Vitest (`npm test`), `provideHttpClientTesting` + `HttpTestingController` para HTTP e `provideRouter` + `RouterTestingHarness` para rotas (`02` §8). Verificações visuais (360 px, tema) são manuais.

| Teste | Nível | Cobre |
|---|---|---|
| `app.routes.spec.ts` › `redireciona_raiz_para_resumo__CA_F04_1` | unitário FE | CA-F04.1 |
| `app.routes.spec.ts` › `abre_as_5_paginas_sob_demanda__CA_F04_2` | unitário FE | CA-F04.2 |
| `app.routes.spec.ts` › `titulo_da_aba_por_rota__CA_F04_5` | unitário FE | CA-F04.5 |
| `app.routes.spec.ts` › `rota_desconhecida__CA_F04_6` | unitário FE | CA-F04.6 |
| `app.spec.ts` › `registrar_gasto_visivel_em_todas_as_rotas__CA_01_1` | unitário FE | CA-01.1 (parcial), CA-F04.3 |
| `app.spec.ts` › `navegacao_com_5_itens_e_rota_ativa__CA_F04_4` | unitário FE | CA-F04.4 |
| `app.spec.ts` › `navegacao_recolhe_em_janela_estreita__CA_F04_7` | unitário FE | CA-F04.7 (parte automatizável, com `BreakpointObserver` simulado) |
| `shared/grafico/grafico.directive.spec.ts` › `cria_um_grafico_apos_render__CA_F04_8` | unitário FE | CA-F04.8 |
| `…` › `atualiza_a_mesma_instancia_e_recria_ao_trocar_tipo__CA_F04_9` | unitário FE | CA-F04.9 |
| `…` › `destroi_ao_sair_e_nao_cria_se_destruido_antes__CA_F04_10` | unitário FE | CA-F04.10 |
| `…` › `acompanha_troca_de_tema__CA_F04_30` (com `matchMedia` simulado) | unitário FE | CA-F04.30 |
| `shared/grafico/grafico.config.spec.ts` › `registra_so_o_necessario__CA_F04_11` | unitário FE | CA-F04.11 |
| `…` › `formata_reais_ptBR__CA_F04_12` | unitário FE | CA-F04.12 |
| `core/interceptors/erro.interceptor.spec.ts` › `converte_envelope_em_ErroApi__CA_F04_13` | unitário FE | CA-F04.13 |
| `…` › `503_vai_para_o_banner_sem_snackbar__CA_F04_14` | unitário FE | CA-F04.14 |
| `…` › `422_vai_para_o_formulario_sem_snackbar__CA_F04_15` | unitário FE | CA-F04.15 |
| `…` › `404_409_500_abrem_snackbar__CA_F04_16` | unitário FE | CA-F04.16 |
| `…` › `backend_fora_do_ar__CA_F04_17` | unitário FE | CA-F04.17, borda 13 |
| `core/state/mes-selecionado.store.spec.ts` › `mes_corrente_por_padrao__CA_04_1` | unitário FE | CA-04.1 |
| `…` › `mes_invalido_na_url_vira_corrente__CA_F04_18` | unitário FE | CA-F04.18, bordas 3–5 |
| `…` › `mes_mantido_entre_resumo_e_lancamentos__CA_04_2` | unitário FE | CA-04.2, bordas 8–9 |
| `core/utils/mes.spec.ts` › `proximo_e_anterior_cruzam_o_ano__CA_F04_19` | unitário FE | CA-F04.19, bordas 6–7 |
| `…` › `mes_por_extenso_ptBR__CA_F04_20` | unitário FE | CA-F04.20 |
| `shared/components/seletor-mes/seletor-mes.spec.ts` › `botoes_trocam_o_mes_e_a_url__CA_F04_19` | unitário FE | CA-F04.19, CA-F04.20 |
| `…` › `datepicker_escolhe_mes_e_fecha__CA_F04_31` | unitário FE | CA-F04.31, borda 21 |
| `shared/components/confirmacao-dialog/confirmacao.dialog.spec.ts` › `confirma_cancela_e_foca_cancelar__CA_F04_21` | unitário FE | CA-F04.21 |
| `core/state/dados.store.spec.ts` › `incrementa_versao__CA_F04_22` | unitário FE | CA-F04.22 |
| `shared/components/estado-vazio/…spec.ts`, `carregando/…spec.ts` | unitário FE | §3.5.4–5 |
| `core/state/conexao.store.spec.ts` › `abertura_faz_um_health__CA_F04_23` | unitário FE | CA-F04.23 |
| `…` › `health_ok_sem_banner__CA_F04_24` | unitário FE | CA-F04.24 |
| `…` › `health_degradado_mostra_banner__CA_16_1` | unitário FE | CA-16.1, CA-F04.25 |
| `…` › `tentar_novamente_uma_requisicao_por_vez__CA_F04_26` | unitário FE | CA-F04.26, borda 15 |
| `…` › `tentar_novamente_com_sucesso__CA_16_2` | unitário FE | CA-16.2, CA-F04.27 |
| `…` › `tentar_novamente_com_nova_falha__CA_F04_28` | unitário FE | CA-F04.28 |
| `…` › `backend_desligado_nao_trava_o_app__CA_F04_29` | unitário FE | CA-F04.29 |
| Janelas de 360, 600 e 960 px em cada rota, nos temas claro e escuro; trocar o tema do sistema com um gráfico de teste aberto | manual FE | CA-F04.7, CA-F04.30, bordas 11, 11a e 19 |
| `npm start` com backend desligado e depois ligado; clicar "Tentar novamente" | manual FE | CA-F04.29, CA-16.2 ponta a ponta |
| `npm run build`: um chunk lazy por página | manual FE | CA-F04.2 |

---

## 9. Divisão em tarefas

| Tarefa | Escopo nesta feature | Arquivos principais |
|---|---|---|
| **T-010** (FE) | Shell (barra superior, navegação lateral, layout responsivo de Q1), rotas lazy com títulos e redirecionamento de rota desconhecida, 5 placeholders, `GraficoDirective` + `grafico.config.ts` + `FABRICA_GRAFICO`, cores do tema e troca claro/escuro (Q6). Substitui a página de boas-vindas do CLI. | `frontend/src/app/{app.ts,app.html,app.scss,app.routes.ts,app.spec.ts,app.routes.spec.ts}`, `frontend/src/app/features/{resumo,lancamentos,historico,categorias,recorrencias}/<nome>.page.ts`, `frontend/src/app/shared/grafico/{grafico.directive.ts,grafico.config.ts,*.spec.ts}` |
| **T-011** (FE) | `core/models` (`ErroApi`, `RespostaHealth`, enums), `core/api/health.api.ts`, `erro.interceptor.ts`, `ConexaoStore`, `MesSelecionadoStore`, `DadosStore`, `utils/mes.ts`, componentes `seletor-mes` (com datepicker de mês, Q7), `confirmacao-dialog`, `estado-vazio`, `carregando`, `banner-conexao` já exibido no shell a partir do `ConexaoStore`, só com a mensagem (CA-F04.14 e .17 dependem dele); código local `BACKEND_INDISPONIVEL` (Q3); seletor nos placeholders de Resumo e Lançamentos; `?mes=` nos links do menu. | `frontend/src/app/core/{models,api,interceptors,state,utils}/…`, `frontend/src/app/shared/components/{seletor-mes,confirmacao-dialog,estado-vazio,carregando,banner-conexao}/…`, `app.config.ts` (interceptor, `provideNativeDateAdapter`, `MAT_DATE_LOCALE`) |
| **T-012** (FE) | `provideAppInitializer` com o health, sem esperar a resposta (Q4); `ConexaoStore.verificar()`; botão "Tentar novamente" no banner, com snackbar e recarga (Q5). | `frontend/src/app/app.config.ts`, `core/state/conexao.store.ts`, `shared/components/banner-conexao/…`, specs |

Ordem obrigatória: T-010 → T-011 → T-012 (`05` §4; T-012 também depende de T-005, já concluída).

---

## 10. Decisões tomadas nesta feature

| Decisão | Motivo | Virou ADR? |
|---|---|---|
| Criação do `Chart` atrás de um token de injeção (`FABRICA_GRAFICO`), com `new Chart(...)` como padrão. | O jsdom do Vitest não tem `<canvas>` funcional; o dublê por injeção testa a diretiva sem dependência nova (`canvas`/`jest-canvas-mock`) e sem depender de `vi.mock` sobre um módulo empacotado pelo builder do Angular. | Não |
| Enums no frontend só como uniões de string; rótulos vêm do backend. | Uma única fonte para "Cartão de crédito" etc. (`backend/app/domain/enums.py`, exposta por `GET /api/formas-pagamento`). | Não |
| Troca de mês com `replaceUrl`. | O botão Voltar leva à tela anterior, não ao mês anterior; o mês continua compartilhável pela URL. | Não |
| Páginas em `features/<nome>/<nome>.page.ts`, classe `<Nome>Page`. | Segue o sufixo de papel com ponto de ADR-13 (`*.dialog.ts`, `*.store.ts`); `03` §3 não fixava o nome. Entra em `03` §3 ao implementar T-010. | Não |
| Foco inicial em "Cancelar" no `confirmacao-dialog`. | Evita exclusão acidental com Enter. | Não |
| 422 não abre snackbar. | `03` §8.4 entrega a validação ao formulário; snackbar duplicaria a mensagem. | Não |
| Botões de registro visíveis e **sem ação** até T-016. | É o escopo de T-010 em `05`; não se inventa comportamento provisório. | Não |
| Cores do tema lidas por uma "sonda": um elemento invisível recebe `color: var(--mat-sys-…)` e a cor computada é lida; a leitura fica atrás do token `CORES_DO_TEMA` (T-010). | Com `color-scheme: light dark`, o Material 22 define as variáveis como `light-dark(claro, escuro)`, texto que o Chart.js não entende; a cor computada já vem resolvida para o tema atual. O jsdom não resolve variáveis CSS, daí o token. | Não |
| Ícones com a fonte **Material Symbols** como padrão do `MatIconRegistry` (`app.config.ts`, T-010). | O `index.html` gerado pelo `ng add` carrega Material Symbols, mas o `<mat-icon>` procura "Material Icons" por padrão e mostraria o nome do ícone em texto. | Não |
| Opções da página mescladas sobre os padrões com `merge` de `chart.js/helpers` (T-010). | Mescla profunda já existente no Chart.js: a página muda só o que quer (ex.: legenda) e mantém tooltip e eixos em reais. Não é dependência nova. | Não |
| Layout: navegação fixa em ≥ 960 px e sobreposta abaixo disso; em < 600 px sem título e com "+ Gasto"/"+ Receita" (Q1). | Mantém a ação principal sempre visível em 360 px sem quebrar a barra; os rótulos completos continuam acessíveis por `aria-label`. | Não |
| Rota desconhecida → `/resumo` (Q2). | App pessoal sem links externos. | Não |
| Código local `BACKEND_INDISPONIVEL` no mesmo banner (Q3). | Com o backend desligado, não há resposta da API que traga código; um banner único evita dois lugares de aviso. `03` → 1.8 (§8.4). | Não |
| Inicializador não espera o health (Q4). | Sem internet, a tentativa única do backend pode levar segundos; a tela nunca fica em branco. | Não |
| Reconexão: banner some + snackbar + `DadosStore.incrementar()`; só o health tira o banner (Q5). | Confirmação visível e dados atualizados; regra de saída do banner única e previsível. | Não |
| Gráficos leem as variáveis do tema Material e reagem à troca de `prefers-color-scheme` (Q6). | Legíveis nos dois temas (F-01 Q2) sem cor fixa duplicada no código. | Não |
| Snackbar carregado sob demanda por `core/avisos/avisos.ts` (T-011). | Injetar o `MatSnackBar` no interceptor levava o overlay do CDK (~70 kB) ao pacote inicial, que passou de 500 kB (limite de aviso do `angular.json`); sob demanda ele fica em 463 kB. T-012 usa o mesmo serviço para "Conexão restabelecida". | Não |
| Item ativo do menu compara só o caminho (`routerLinkActiveOptions` com query ignorada) (T-011). | Com a comparação padrão, `/resumo?mes=…` no link não ficaria ativo com a URL `/resumo` (app recém-aberto) e o `aria-current` sumiria (CA-F04.4). | Não |
| Datepicker ancorado num `<input>` invisível sob o botão do mês (T-011). | O `mat-datepicker` exige um input associado para abrir e para marcar o mês atual; invisível, fora do Tab e com `aria-hidden`, ele só posiciona o calendário. | Não |
| `confirmar(dialog, dados)` devolve `Observable<boolean>` (T-011). | Esc e clique fora fecham o diálogo do Material sem valor; a função converte isso em `false` (CA-F04.21). | Não |
| Escolha de mês pelo `mat-datepicker` em visão multi-year → mês (Q7). |
| `verificar()` também põe no banner um erro do próprio health que não seja de conexão (T-012). | O interceptor já cuida do backend fora do ar; um 500 do health (que não deveria acontecer) viraria só um aviso passageiro e a falha na abertura passaria despercebida. | Não | Componente oficial, acessível e em pt-BR; o adaptador de datas já seria necessário em F-06. | Não |

---

## 11. Questões em aberto

**Respondidas em 2026-09-30 — nenhuma em aberto.** Em todas, o usuário escolheu a opção recomendada.

- [x] **Q1** → navegação fixa em ≥ 960 px e sobreposta pelo ☰ abaixo disso; em < 600 px a barra perde o título e os botões viram "+ Gasto"/"+ Receita", com `aria-label` completo (§3.1.7).
- [x] **Q2** → rota desconhecida redireciona para `/resumo`.
- [x] **Q3** → código local `BACKEND_INDISPONIVEL` (status 0, ou 502/504 sem envelope), no **mesmo banner** com "Tentar novamente" (§3.3.4). `03` → 1.8 (§8.4).
- [x] **Q4** → o inicializador não espera o health; sem indicador de "verificando".
- [x] **Q5** → reconexão: banner some, snackbar "Conexão com a planilha restabelecida.", `DadosStore.incrementar()`. Só o health tira o banner.
- [x] **Q6** → gráficos leem `--mat-sys-on-surface`/`--mat-sys-outline-variant` e atualizam na troca de `prefers-color-scheme` (§3.2.7).
- [x] **Q7** → `mat-datepicker` em visão multi-year → mês, fechando ao escolher o mês; `provideNativeDateAdapter()` + `MAT_DATE_LOCALE` entram em T-011 (§3.5.2).

---

## Revisões

| Data | Alteração |
|---|---|
| 2026-09-30 | Criação (`/especificar-feature F-04`). Status `Rascunho` — 7 questões em aberto. |
| 2026-09-30 | Q1–Q7 respondidas → status **Aprovada**. Comportamentos incorporados em §3; CA-F04.6, .7, .17, .23, .27 e .29 fechados; CA-F04.30 (tema) e .31 (datepicker) acrescentados; bordas 11a, 21 e 22. `03` → 1.8. |
| 2026-09-30 | T-010 concluída: CA-01.1 (parcial), CA-F04.1 a .6 e .8 a .12 verificados por teste; CA-F04.7 e .30 com a parte automatizável verificada e a conferência visual pendente. Três decisões de implementação em §10. `03` → 1.11. |
| 2026-09-30 | §9 ajustado ao planejar T-011: o banner passa a ser exibido já em T-011 (só a mensagem), porque CA-F04.14/.17 dependem dele; T-012 fica com `verificar()`, o botão "Tentar novamente" e a verificação na abertura. |
| 2026-09-30 | T-011 concluída: CA-04.1, CA-04.2, CA-F04.13 a .22 e .31 verificados por teste. Quatro decisões de implementação em §10 (snackbar sob demanda, item ativo sem query, input do datepicker, `confirmar`). `03` → 1.12. |
| 2026-09-30 | T-012 concluída → **feature Concluída**. CA-16.1, CA-16.2 e CA-F04.23 a .29 verificados por teste; contrato conferido de ponta a ponta com `ng serve` + uvicorn (config falsa): health `degradado`, envelope de erro e **502** do proxy com o backend desligado (bordas 13 e §3.3 corrigidas de 504 para 502). Pendentes só as conferências visuais de CA-F04.7 e .30. `03` → 1.13. |
| 2026-09-30 | **Revisão (T-014, F-05):** a navegação lateral deixou de usar `mat-nav-list` e virou `<nav>` com links simples (mesmos itens, ícones, `aria-current` e comportamento). Motivo: a lista do Material importa `@angular/forms`, e com o primeiro formulário reativo (diálogo de categoria) o módulo inteiro passou a ir para o pacote inicial (529 kB > 500 kB); sem ela, 456 kB. Aprovado pelo usuário. Testes do shell ajustados aos novos seletores. |
