# F-13 — Recorrências

| Campo | Valor |
|---|---|
| Feature | F-13 |
| Marco | M3 |
| Status | Concluída |
| Requisitos | REQ-09 (CA-09.1, CA-09.2), REQ-10 (CA-10.1 a CA-10.4) |
| Regras | RN-01, RN-04, RN-05, RN-06, RN-09, RN-10, RN-11, RN-12, RN-14; premissas P-04, P-05 (confirmadas em 2026-10-01) |
| Depende de | F-06 (**Concluída**); T-030 também usa F-04 (T-012, **Concluída**) e o diálogo/utilitários de F-06 (T-016, **Concluída**) |
| Tarefas | T-028, T-029, T-030 |
| Atualizado em | 2026-10-01 |

> **IDs de critério:** herdados de `01` mantêm o ID original (**CA-09.1** …). Os refinados usam **`CA-F13.y`**.
>
> Marcas **(Qn)** apontam a decisão de §11 que fixou aquele trecho.

---

## 1. Objetivo

Cadastrar uma vez as contas e receitas que se repetem todo mês (aluguel, assinaturas, salário) e deixar o aplicativo gerar os lançamentos sozinho ao abrir, sem duplicar, sem recriar o que o usuário excluiu e sem inventar meses futuros.

---

## 2. Escopo

**Inclui**
- `recorrencia_service`: listar, criar, editar e mudar status (pausar, reativar, encerrar), com `proximo_mes` calculado (T-028).
- `recorrencia_service.sincronizar`: geração idempotente pela marca d'água `ultimo_mes_gerado` (algoritmo de `03` §4.4), numa única escrita de lançamentos (T-029).
- Endpoints de `03` §6.1: `GET`/`POST /api/recorrencias`, `PUT /api/recorrencias/{id}`, `PATCH /api/recorrencias/{id}/status`, `POST /api/recorrencias/sincronizar`.
- Página `/recorrencias` (hoje provisória, F-04): lista com estado e próximo mês, criar, editar, pausar, reativar, encerrar (T-030).
- Sincronização na abertura do app, depois de um `health` ok, com aviso "n lançamentos recorrentes gerados" (`03` §7.2, T-030).
- A pendência cruzada de F-05: recorrência ativa com categoria desativada **(Q1)**.

**Não inclui** (e onde será tratado)
- Excluir uma recorrência — REQ-09 não pede (cadastra, edita, pausa, reativa, **encerra**). Encerrar é a forma de parar de vez.
- Alterar ou apagar lançamentos já gerados ao editar/pausar/encerrar — RN-11 e CA-09.2 proíbem; eles se editam e excluem como qualquer lançamento (F-08).
- Geração em segundo plano ou agendada — P-05: só ao abrir o app (e nas ações de §3.3.6, Q5).
- Valor variável por mês (luz, água) — P-04: valor fixo; o usuário ajusta o lançamento gerado (F-08).
- Aviso de linhas ignoradas da aba `Recorrencias` na tela — **F-14**.
- Botão "Recarregar dados" — **F-14** (T-032).

---

## 3. Comportamento detalhado

### 3.1 Regras da recorrência (T-028)

1. **Campos** (`RecorrenciaEntrada`, `03` §6.3): `tipo`, `descricao` (RN-06: 1–100), `valor` (RN-01: > 0, 2 casas), `categoria_id`, `forma_pagamento` (obrigatória para gasto, opcional para receita — RN-05), `dia_do_mes` (1–31, RN-09), `mes_inicio` (`YYYY-MM`, obrigatório), `mes_fim` (`YYYY-MM` ou `null` = sem fim). Não há observação (a aba `Recorrencias` não tem a coluna; os lançamentos gerados saem com observação vazia).
2. **Validações**, na ordem: formato/limites pelo Pydantic (422 no campo) → `mes_fim` ≥ `mes_inicio`, senão 422 no campo `mes_fim`: "O mês de fim deve ser igual ou posterior ao mês de início." → categoria e forma pela **mesma** `validar_categoria_e_forma` de F-06/F-12 (inexistente → 422 em `categoria_id`; tipo incompatível → 409 `CATEGORIA_TIPO_INCOMPATIVEL`; inativa → 409 `CATEGORIA_INATIVA`; gasto sem forma → 422 em `forma_pagamento`).
3. **Criar** (`POST`): `id = uuid4().hex`, `status = ATIVA`, `ultimo_mes_gerado = null`, `criado_em = atualizado_em = agora()`. **Uma** escrita na aba. `mes_inicio` no passado é aceito, sem limite: os meses de `mes_inicio` até o corrente serão gerados (CA-10.1) **(Q6)**.
4. **Editar** (`PUT`, CA-09.2): 404 "Recorrência não encontrada." antes das regras; todos os campos de §3.1.1 podem mudar, inclusive o tipo (como em F-08); a categoria **atual** pode estar inativa (F-08 Q1). Preserva `id`, `status`, `ultimo_mes_gerado` e `criado_em`; `atualizado_em = agora()`. **Nenhum** lançamento já gerado muda: só os gerados depois usam os dados novos. Recorrência `ENCERRADA` não é editável → 422 no campo `status`: "Recorrência encerrada não pode ser editada." **(Q3)**.
5. **Mudar status** (`PATCH .../status` com `{status}`) — transições válidas **(Q3)**:

   | De → Para | Efeito |
   |---|---|
   | `ATIVA` → `PAUSADA` | Para de gerar. Nada mais muda (RN-11). |
   | `PAUSADA` → `ATIVA` | Reativa **sem retroativos** (RN-11): `ultimo_mes_gerado = max(ultimo_mes_gerado, mes_anterior(mes_corrente))` (`03` §4.4). |
   | `ATIVA`/`PAUSADA` → `ENCERRADA` | Para de gerar, **definitivamente**. Lançamentos gerados ficam. |
   | mesmo status, ou qualquer saída de `ENCERRADA` | 422 no campo `status`: "Não é possível mudar de <atual> para <novo>." |

   404 se o `id` não existe. `atualizado_em = agora()`. Uma escrita.
6. **Listar** (`GET`): todas as recorrências válidas da aba, ordenadas por status (`ATIVA`, `PAUSADA`, `ENCERRADA`) e, dentro dele, pela descrição sem acento/caixa (chave de F-05). Linhas inválidas são ignoradas (RN-14, `03` §5.6).
7. **`proximo_mes`** (CA-09.1), calculado a cada resposta, nunca gravado:
   - `ATIVA`: `p = max(mes_inicio, proximo_mes(ultimo_mes_gerado))` (só `mes_inicio` se nunca gerou); `null` se `mes_fim` existe e `p > mes_fim`. Pode ser um mês futuro ("vai gerar em novembro").
   - `PAUSADA` e `ENCERRADA`: `null`.
8. Ativa com `mes_fim` já passado e tudo gerado: o status **continua `ATIVA`** (a sincronização não muda status) e `proximo_mes` = `null`; a tela mostra "Vigência terminou em <mês>" **(Q4)**.

### 3.2 Sincronização — `recorrencia_service.sincronizar` (T-029)

1. **Uma sincronização por vez** no processo (trava): duas abas do navegador abrindo juntas não geram em dobro. **Editar e mudar status esperam** a sincronização em curso (mesma trava): senão a sincronização gravaria por cima da edição a cópia antiga da recorrência, só com a marca d'água nova (T-029).
2. Lê `Recorrencias`, `Lancamentos` e `Categorias` (uma leitura de cada, pelo cache). `mes_corrente` do relógio local (injetável nos testes, como em F-11).
3. Para cada recorrência **`ATIVA`** (`03` §4.4):
   - `primeiro = max(mes_inicio, proximo_mes(ultimo_mes_gerado))` (sem marca d'água → `mes_inicio`);
   - `ultimo = min(mes_corrente, mes_fim or mes_corrente)` — **nunca** um mês futuro (CA-10.4, RN-09);
   - para cada mês de `primeiro` a `ultimo`: um lançamento com `data = ajustar_dia(mes, dia_do_mes)` (dia 31 em fevereiro → 28/29 — RN-09), `tipo`, `descricao`, `valor`, `categoria_id`, `forma_pagamento` da recorrência **no momento da geração** (CA-09.2), observação vazia, `recorrencia_id = id`, `criado_em = atualizado_em = agora()`;
   - no mês corrente o lançamento é gerado **mesmo que o dia ainda não tenha chegado** (data futura dentro do mês) **(Q2)**;
   - se gerou algo (ou pulou pela defesa do item 5), `ultimo_mes_gerado = ultimo` e `atualizado_em = agora()`.
4. **Categoria inativa ou apagada à mão:** gera normalmente (o lançamento aparece com o nome da categoria inativa, ou "Categoria não encontrada" — F-07). RN-04 vale para lançamentos registrados pelo usuário; desativar a categoria não para a recorrência — para isso existe pausar/encerrar **(Q1)**.
5. **Defesa contra falha parcial:** um mês que já tem lançamento com o mesmo `recorrencia_id` é **pulado** (não gera de novo), mas conta para avançar a marca d'água. Cobre o caso de a escrita dos lançamentos dar certo e a das marcas d'água falhar (item 6). Não muda CA-10.3: um lançamento excluído está num mês ≤ marca d'água, que já não é gerado.
6. **Escritas:** todos os lançamentos gerados numa **única** chamada (`inserir` em lote, `02` §5.5); **depois**, uma atualização por recorrência que avançou (`atualizar`). Sem nada a gerar → **nenhuma** escrita (CA-10.2). Recorrência apagada à mão entre a leitura e a atualização: os lançamentos já gravados ficam e as demais recorrências seguem (não é erro) (T-029).
7. **Resposta:** `{lancamentos_gerados: n, detalhes: [{recorrencia_id, meses: [YYYY-MM]}]}` — só as recorrências que geraram algo, meses em ordem.
8. Planilha inacessível → 503 com a causa (F-02); nada é gravado pela metade além do previsto no item 5.

### 3.3 Página `/recorrencias` (T-030)

1. Título "Recorrências" e o botão **"Nova recorrência"**.
2. **Lista** (CA-09.1), na ordem da API. Em ≥ 600 px, tabela: Descrição · Categoria (bolinha da cor + nome; inativa com "(inativa)"; apagada → "Categoria não encontrada") · Valor (`− R$ 39,90` para gasto, `+ R$ 5.000,00` em verde para receita, como F-07) · Dia ("dia 10") · Vigência ("desde julho de 2026", ou "de julho de 2026 a dezembro de 2026") · Estado (selo "Ativa" / "Pausada" / "Encerrada") · Próximo mês ("setembro de 2026"; "—" se `null`; "Vigência terminou em agosto de 2026" para ativa sem próximo **(Q4)**) · ⋮. Abaixo de 600 px, cartões com os mesmos dados. Nomes e cores de categoria vêm do `CategoriasStore` (já carregado pelo app), não da API de recorrências.
3. **Menu ⋮** por estado: `ATIVA` → Editar, Pausar, Encerrar; `PAUSADA` → Editar, Reativar, Encerrar; `ENCERRADA` → nenhuma ação (menu ausente) **(Q3)**.
   - Pausar e Reativar: sem confirmação; aviso "Recorrência pausada." / "Recorrência reativada. Meses do período pausado não são gerados." (RN-11).
   - Encerrar: confirmação "Encerrar recorrência?" — `"<descrição>" deixa de gerar lançamentos. Os lançamentos já gerados continuam. Não é possível reativar depois.` — botão "Encerrar"; aviso "Recorrência encerrada.".
4. **Diálogo** `recorrencia-form.dialog` ("Nova recorrência" / "Editar recorrência"): Tipo (Gasto/Receita, alternância; trocar limpa a categoria do outro tipo, como F-08), Descrição, Valor (pt-BR, `utils/valor.ts`), Categoria (só ativas do tipo; na edição a atual inativa aparece "(inativa)"), Forma de pagamento (obrigatória no gasto; "Não informar" na receita), Dia do mês (1–31, com a dica "Nos meses sem esse dia, usa o último dia do mês."), Mês de início (datepicker ano → mês; padrão: mês corrente), Mês de fim (opcional; "Sem fim" por padrão, com botão para limpar). Formulário reativo tipado; erros da API no campo (`TRATAMENTO_LOCAL`, F-06 Q3); em erro o diálogo fica aberto com os dados (CA-01.4).
   - Com `mes_inicio` anterior ao mês corrente, o diálogo avisa: "Os lançamentos de julho de 2026 a setembro de 2026 serão gerados ao salvar." (um mês só: "O lançamento de julho de 2026 será gerado ao salvar.") (a contagem de meses é aritmética de calendário, não de dinheiro) **(Q5, Q6)**.
5. Estados: carregando · vazio ("Nenhuma recorrência cadastrada." + botão "Nova recorrência") · erro ("Não foi possível carregar as recorrências.") · recarga com esmaecido; resposta antiga descartada (F-07).
6. **Depois de salvar, reativar** (ações que podem gerar meses), a página chama `POST /api/recorrencias/sincronizar` na hora, recarrega a lista e, se `n > 0`, mostra o mesmo aviso da abertura e incrementa `DadosStore.versao` **(Q5)**.

### 3.4 Sincronização na abertura (T-030, `03` §7.2, P-05)

1. O inicializador de F-04 continua sem esperar respostas (F-04 Q4). Quando o `GET /api/health` volta **ok**, o app chama `POST /api/recorrencias/sincronizar` **uma vez**.
2. `lancamentos_gerados > 0` → aviso "3 lançamentos recorrentes gerados." (singular: "1 lançamento recorrente gerado.") e `DadosStore.versao++` (as telas abertas recarregam). `0` → nada.
3. Falha da sincronização: 503/backend fora → banner (interceptor de F-04); outros erros → aviso do interceptor. O app continua usável.
4. "Tentar novamente" do banner que **restabelece** a conexão também dispara a sincronização (o app pode ter aberto sem planilha).

---

## 4. Critérios de aceite

**Herdados de `01`**

- [x] **CA-09.1** Dado a tela de recorrências, então todas aparecem com seu estado (ativa/pausada/encerrada) e o próximo mês a gerar. *(T-028: a API devolve status e `proximo_mes` — CA-F13.7; T-030: a tela mostra — CA-F13.20.)*
- [x] **CA-09.2** Dado uma recorrência editada, então só os lançamentos gerados **depois** da edição usam os novos dados. *(T-028: a edição não toca lançamentos e preserva a marca d'água — CA-F13.3; T-029: a geração seguinte usa os dados novos — CA-F13.15.)*
- [x] **CA-10.1** Dado uma recorrência ativa desde julho, e o app aberto pela primeira vez em setembro, então são gerados os lançamentos de julho, agosto e setembro. *(T-029: verificado na API — CA-F13.9 a .12; T-030: a abertura do app chama a sincronização uma vez — CA-F13.25.)*
- [x] **CA-10.2** Dado que o app é aberto várias vezes no mesmo mês, então nenhum lançamento é duplicado. *(T-029: verificado na API — CA-F13.9 a .12; T-030: a abertura do app chama a sincronização uma vez — CA-F13.25.)*
- [x] **CA-10.3** Dado que o usuário excluiu um lançamento gerado, quando o app é reaberto, então ele **não** é gerado de novo. *(T-029: verificado na API — CA-F13.9 a .12; T-030: a abertura do app chama a sincronização uma vez — CA-F13.25.)*
- [x] **CA-10.4** Nunca são gerados lançamentos para meses futuros. *(T-029: CA-F13.12; a abertura do app só chama a mesma sincronização.)*

**Refinados — CRUD e status (T-028)**

- [x] **CA-F13.1** Dado uma `RecorrenciaEntrada` válida, quando `POST /api/recorrencias`, então 201 com `status` `ATIVA`, `ultimo_mes_gerado` `null`, `proximo_mes` = `mes_inicio`, e **uma** linha nova na aba `Recorrencias` (colunas de `03` §5.3).
- [x] **CA-F13.2** Dado descrição vazia/101 caracteres, valor ≤ 0 ou com 3 casas, `dia_do_mes` 0 ou 32, mês fora de `YYYY-MM`, `mes_fim` < `mes_inicio`, gasto sem forma ou categoria inexistente, então 422 `VALIDACAO` no campo certo; categoria de outro tipo ou inativa → 409 com o código de F-06.
- [x] **CA-F13.3** Dado uma recorrência com lançamentos gerados, quando `PUT` muda valor, descrição, categoria e dia, então 200 com os dados novos, `status`/`ultimo_mes_gerado`/`criado_em` preservados, e nenhum lançamento já gerado muda (CA-09.2).
- [x] **CA-F13.4** Dado `PUT` com a categoria atual inativa, então 200 (F-08 Q1); trocar para outra inativa → 409 `CATEGORIA_INATIVA`.
- [x] **CA-F13.5** Dado as transições de §3.1.5, então as válidas dão 200 com o status novo e as inválidas (mesmo status, sair de `ENCERRADA`) dão 422 no campo `status`; `id` inexistente → 404 em `PUT` e `PATCH`.
- [x] **CA-F13.6** Dado uma recorrência pausada em junho com `ultimo_mes_gerado` = `2026-05`, quando reativada em setembro de 2026, então `ultimo_mes_gerado` = `2026-08` e `proximo_mes` = `2026-09` (RN-11: junho a agosto não são gerados).
- [x] **CA-F13.7** Dado recorrências nos três status, então `GET` as traz na ordem de §3.1.6, com `proximo_mes` de §3.1.7 (ativa nunca gerada, ativa em dia, ativa com `mes_fim` passado → `null`, pausada e encerrada → `null`).
- [x] **CA-F13.8** Dado `PUT` numa recorrência encerrada, então 422 no campo `status` (Q3).

**Refinados — sincronização (T-029)**

- [x] **CA-F13.9** Dado uma recorrência ativa desde `2026-07`, dia 10, nunca gerada, e hoje = 01/10/2026, quando `POST /api/recorrencias/sincronizar`, então 4 lançamentos (10/07, 10/08, 10/09 e 10/10 — o de outubro por Q2), todos com `recorrencia_id`, gravados numa **única** chamada de inserção, `ultimo_mes_gerado` = `2026-10` e a resposta lista os 4 meses (CA-10.1).
- [x] **CA-F13.10** Dado a sincronização repetida no mesmo mês, então `lancamentos_gerados` = 0 e **nenhuma** escrita na planilha (CA-10.2).
- [x] **CA-F13.11** Dado um lançamento gerado excluído (F-08), quando sincroniza de novo, então ele não volta (CA-10.3, RN-10).
- [x] **CA-F13.12** Dado `mes_inicio` no futuro, ou `mes_fim` no passado já todo gerado, então nada é gerado; nunca há lançamento com data em mês posterior ao corrente (CA-10.4).
- [x] **CA-F13.13** Dado `dia_do_mes` = 31 e o período jan–abr/2027, então as datas são 31/01, 28/02, 31/03 e 30/04 (RN-09); em 2028, 29/02.
- [x] **CA-F13.14** Dado recorrências pausadas e encerradas com meses pendentes, então nada é gerado para elas (RN-11).
- [x] **CA-F13.15** Dado uma recorrência editada depois de gerar julho e agosto, quando setembro é gerado, então setembro usa os dados novos e julho/agosto continuam como estavam (CA-09.2).
- [x] **CA-F13.16** Dado uma recorrência ativa com categoria desativada (ou apagada à mão), então o lançamento é gerado normalmente (Q1).
- [x] **CA-F13.17** Dado um lançamento da recorrência já existente em agosto e marca d'água em julho (falha parcial anterior), quando sincroniza, então agosto **não** é gerado de novo e a marca d'água avança.
- [x] **CA-F13.18** Dado duas sincronizações simultâneas, então os lançamentos saem uma vez só (trava).
- [x] **CA-F13.19** Dado a planilha inacessível, então 503 com a causa; dado uma linha inválida em `Recorrencias`, então ela é ignorada sem derrubar a sincronização.

**Refinados — frontend (T-030)**

- [x] **CA-F13.20** Dado a resposta da API, então a lista mostra descrição, categoria (cor e nome atuais do `CategoriasStore`), valor com sinal, dia, vigência por extenso, selo de estado e próximo mês, na ordem da API (CA-09.1); tabela ≥ 600 px, cartões abaixo.
- [x] **CA-F13.21** Dado o menu ⋮, então as ações dependem do estado (§3.3.3); Encerrar pede confirmação; Pausar/Reativar/Encerrar chamam o `PATCH`, avisam e recarregam a lista.
- [x] **CA-F13.22** Dado o diálogo novo, então os campos de §3.3.4 têm os padrões (tipo Gasto, mês corrente, sem fim), a categoria lista só ativas do tipo, a forma é obrigatória no gasto, e o valor aceita formato pt-BR; dado o diálogo de edição, então vem preenchido e a categoria atual inativa aparece.
- [x] **CA-F13.23** Dado 422/409 da API, então o erro aparece no campo e o diálogo fica aberto com os dados; dado 503, o diálogo fica aberto e o banner aparece.
- [x] **CA-F13.24** Dado `mes_inicio` anterior ao corrente no diálogo, então aparece o aviso de meses a gerar; ao salvar, a sincronização é chamada e, com `n > 0`, aparece o aviso e `versao` é incrementada (Q5, Q6).
- [x] **CA-F13.25** Dado a abertura do app com `health` ok, então `POST /api/recorrencias/sincronizar` é chamado uma vez; `n > 0` → aviso no singular/plural e `versao++`; `0` → nada; `health` com falha → não chama; "Tentar novamente" que restabelece → chama.
- [~] **CA-F13.26** Dado lista vazia, carga com erro, ou janela de 360 px, então estado vazio, mensagem de erro e layout sem rolagem horizontal (RNF-07; visual).

---

## 5. Casos de borda

| # | Caso | Comportamento esperado | Regra |
|---|---|---|---|
| 1 | Dia 31 em fevereiro de 2027 / 2028 | 28/02/2027 / 29/02/2028. | RN-09 |
| 2 | Dia 31 em abril | 30/04. | RN-09 |
| 3 | Ativa desde julho, app aberto pela 1ª vez em setembro | Julho, agosto e setembro gerados. | CA-10.1 |
| 4 | App aberto 5 vezes em setembro | Só a 1ª gera; as outras: 0 e nenhuma escrita. | CA-10.2 |
| 5 | Lançamento gerado em agosto excluído | Não volta. | CA-10.3, RN-10 |
| 6 | `mes_inicio` = mês que vem | Nada gerado agora; `proximo_mes` = mês que vem. | CA-10.4 |
| 7 | `mes_fim` = agosto, hoje setembro, marca d'água em junho | Gera julho e agosto; `proximo_mes` vira `null`; status continua `ATIVA` (Q4). | RN-09 |
| 8 | Hoje 01/10, dia do mês 10 | O lançamento de 10/10 é gerado hoje (data futura dentro do mês) (Q2). | RN-09 |
| 9 | Pausada em junho, reativada em setembro | Junho a agosto nunca gerados; setembro sim, na próxima sincronização. | RN-11 |
| 10 | Pausada e reativada no mesmo mês, antes de gerar o mês | Marca d'água = mês anterior: o mês corrente ainda é gerado. | RN-11, `03` §4.4 |
| 11 | Pausada antes de gerar qualquer mês, `mes_inicio` no passado | Ao reativar, os meses passados não são gerados. | RN-11 |
| 12 | Encerrada | Não gera; não edita; não reativa (Q3). | RN-11, Q3 |
| 13 | Valor editado de R$ 39,90 para R$ 44,90 em setembro | Julho/agosto continuam R$ 39,90; outubro sai R$ 44,90. | CA-09.2 |
| 14 | Editar `mes_inicio` para antes de meses já gerados | Nada é gerado para trás da marca d'água. | RN-10 |
| 15 | Categoria desativada depois de criar a recorrência | Continua gerando (Q1); na tela, "(inativa)". | Q1, CA-11.4 |
| 16 | Categoria apagada à mão na planilha | Gera; lista e listagem mostram "Categoria não encontrada". | RN-14, Q1 |
| 17 | Lançamento gerado com a data mudada à mão para outro mês | Não afeta a geração (a marca d'água manda); a defesa do §3.2.5 olha `recorrencia_id` + mês da data. | RN-10, RN-14 |
| 18 | Escrita dos lançamentos ok e das marcas d'água com erro | Na próxima sincronização os meses já gerados são pulados (§3.2.5). | CA-10.2 |
| 19 | Duas abas abrindo o app ao mesmo tempo | Uma sincronização espera a outra; nada duplicado. | CA-10.2 |
| 20 | Linha inválida na aba `Recorrencias` (dia 40) | Ignorada na lista e na sincronização. | RN-14 |
| 21 | Receita sem forma de pagamento | Aceita; lançamentos gerados sem forma. | RN-05 |
| 22 | Recorrência com `mes_inicio` em 2020 | Aceita (Q6); a 1ª sincronização gera todos os meses até o corrente numa única inserção. | Q6 |
| 23 | App aberto sem planilha; "Tentar novamente" restabelece | A sincronização roda nessa hora. | §3.4.4 |

---

## 6. Contrato e dados

**API** (`03` §6.1 — sem mudança de rotas)

| Método | Caminho | Entrada | Saída |
|---|---|---|---|
| GET | `/api/recorrencias` | — | `200 [Recorrencia]` · `503` |
| POST | `/api/recorrencias` | `RecorrenciaEntrada` | `201 Recorrencia` · `422` · `409` · `503` |
| PUT | `/api/recorrencias/{id}` | `RecorrenciaEntrada` | `200 Recorrencia` · `404` · `422` · `409` · `503` |
| PATCH | `/api/recorrencias/{id}/status` | `{ "status": "PAUSADA" }` | `200 Recorrencia` · `404` · `422` · `503` |
| POST | `/api/recorrencias/sincronizar` | — | `200 {lancamentos_gerados, detalhes}` · `503` |

```jsonc
// RecorrenciaEntrada (03 §6.3)
{ "tipo": "GASTO", "descricao": "Streaming", "valor": 39.90, "categoria_id": "assinaturas",
  "forma_pagamento": "CREDITO", "dia_do_mes": 10, "mes_inicio": "2026-07", "mes_fim": null }

// Recorrencia = RecorrenciaEntrada + (03 §6.3)
{ "id": "c02d...", "status": "ATIVA", "ultimo_mes_gerado": "2026-09", "proximo_mes": "2026-10",
  "criado_em": "2026-07-01T09:00:00", "atualizado_em": "2026-09-01T09:00:00" }

// POST /api/recorrencias/sincronizar
{ "lancamentos_gerados": 4,
  "detalhes": [ { "recorrencia_id": "c02d...", "meses": ["2026-07", "2026-08", "2026-09", "2026-10"] } ] }
```

**Precisões sobre `03`** (aprovadas; T-028/T-029 as aplicam):
- §6.2: 404 com a mensagem "Recorrência não encontrada."; transição de status inválida e edição de encerrada → 422 `VALIDACAO` no campo `status` (sem código novo).
- §6.3: regra de `proximo_mes` (§3.1.7) e ordem da listagem (§3.1.6).
- §4.4: no algoritmo, "pular mês que já tem lançamento da recorrência" (§3.2.5), "sem nada a gerar, nenhuma escrita" e a trava de uma sincronização por vez.

**Planilha** — aba `Recorrencias` (`03` §5.3, A–M), lida e escrita; aba `Lancamentos` (`03` §5.1), escrita em lote pela sincronização (`recorrencia_id` na coluna L); aba `Categorias`, só leitura. **Nenhuma coluna nova.**

---

## 7. Interface

- **Rota:** `/recorrencias` (F-04).
- **Componentes:** `RecorrenciasPage` (substitui a provisória), `recorrencia-form.dialog` (aberto sob demanda), `RecorrenciasApi`, modelo `Recorrencia` em `core/models/`, sincronização na abertura junto de `provideVerificacaoDeConexao`/`ConexaoStore` (F-04), `confirmacao-dialog`, `estado-vazio`, `carregando`, `CategoriasStore`, `FormasPagamentoStore`, `utils/valor.ts`, `utils/mes.ts`.
- **Estados:** carregando · vazio · erro · recarregando · sucesso.
- **Mensagens (pt-BR):** "Recorrências"; "Nova recorrência"; "Editar recorrência"; "Ativa"/"Pausada"/"Encerrada"; "dia 10"; "desde julho de 2026"; "de julho de 2026 a dezembro de 2026"; "Vigência terminou em agosto de 2026"; "Pausar"; "Reativar"; "Encerrar"; "Encerrar recorrência?"; "Recorrência pausada."; "Recorrência reativada. Meses do período pausado não são gerados."; "Recorrência encerrada."; "Nos meses sem esse dia, usa o último dia do mês."; "Os lançamentos de <mês> a <mês> serão gerados ao salvar." / "O lançamento de <mês> será gerado ao salvar."; "Sem fim"; "Nenhuma recorrência cadastrada."; "Não foi possível carregar as recorrências."; "1 lançamento recorrente gerado." / "<n> lançamentos recorrentes gerados.". Backend: "Recorrência não encontrada."; "O mês de fim deve ser igual ou posterior ao mês de início."; "Recorrência encerrada não pode ser editada."; "Não é possível mudar de <Ativa> para <Ativa>.".
- **Acessibilidade:** tabela com `<th scope="col">`; selo de estado com texto (não só cor); menu ⋮ com `aria-label` "Ações de <descrição>"; foco no 1º campo ao abrir o diálogo (F-06).

---

## 8. Plano de testes

| Teste | Nível | Cobre |
|---|---|---|
| `tests/unit/test_recorrencia_service.py::test_criar__CA_F13_1` | unitário BE | CA-F13.1 |
| `…::test_validacoes__CA_F13_2` (parametrizado) · `test_criar_receita_sem_forma_e_inicio_no_passado__RN_05` · `test_mes_fim_igual_ao_inicio_e_aceito` | unitário BE | CA-F13.2, RN-04, RN-05, bordas 21–22 |
| `…::test_editar_nao_muda_gerados__CA_09_2` | unitário BE | CA-09.2, CA-F13.3, borda 13 |
| `…::test_editar_categoria_atual_inativa__CA_F13_4` | unitário BE | CA-F13.4 |
| `…::test_transicoes_de_status__CA_F13_5` (parametrizado) · `test_mudar_status_inexistente_404` · `test_pausar_e_encerrar_nao_mexem_na_marca_dagua__RN_11` | unitário BE | CA-F13.5, borda 12 |
| `…::test_reativar_sem_retroativos__RN_11` (parametrizado: bordas 9–11) | unitário BE | CA-F13.6, RN-11 |
| `…::test_listar_ordem_e_proximo_mes__CA_09_1` | unitário BE | CA-09.1, CA-F13.7, bordas 6–7 |
| `…::test_editar_encerrada__CA_F13_8` | unitário BE | CA-F13.8 |
| `tests/unit/test_sincronizacao.py::test_gera_desde_o_inicio__CA_10_1` | unitário BE | CA-10.1, CA-F13.9, bordas 3, 8 |
| `…::test_idempotente__CA_10_2` | unitário BE | CA-10.2, CA-F13.10, borda 4 |
| `…::test_excluido_nao_volta__CA_10_3__RN_10` | unitário BE | CA-10.3, CA-F13.11, borda 5 |
| `…::test_nunca_mes_futuro__CA_10_4` | unitário BE | CA-10.4, CA-F13.12, bordas 6–7 |
| `…::test_dia_31__RN_09` (parametrizado: 2027, 2028, abril) | unitário BE | CA-F13.13, bordas 1–2 |
| `…::test_pausada_e_encerrada_nao_geram__RN_11` | unitário BE | CA-F13.14 |
| `…::test_edicao_vale_para_proximos__CA_09_2` | unitário BE | CA-F13.15, borda 13 |
| `…::test_categoria_inativa_ou_apagada_gera__CA_F13_16` | unitário BE | CA-F13.16, bordas 15–16 |
| `…::test_pula_mes_ja_gerado__CA_F13_17` | unitário BE | CA-F13.17, bordas 17–18 |
| `…::test_trava_sincronizacoes_simultaneas__CA_F13_18` · `test_edicao_espera_a_sincronizacao__CA_F13_18` (threads; ambos falham sem a trava, conferido) | unitário BE | CA-F13.18, borda 19, §3.2.1 |
| `…::test_receita_sem_forma__RN_05` · `test_so_mes_ja_gerado_avanca_a_marca_sem_inserir` · `test_recorrencia_apagada_durante_sincronizacao` | unitário BE | borda 21, §3.2.5–6 |
| `tests/api/test_recorrencias.py::test_post_201_formato_e_linha__CA_F13_1` (planilha falsa) | API BE | contrato §6, CA-F13.1 |
| `…::test_422_409__CA_F13_2` (parametrizado: RN-01, RN-06, RN-09 no Pydantic) · `test_put_edita_e_404__CA_09_2` · `test_get_ordem_e_linha_invalida_ignorada__CA_09_1` · `test_get_503` | API BE | CA-F13.2, CA-F13.3, CA-F13.7, borda 20 |
| `…::test_patch_status__CA_F13_5` | API BE | CA-F13.5 |
| `…::test_sincronizar_uma_insercao_e_sem_escrita_na_repeticao__CA_10_2` (planilha falsa) | API BE | CA-F13.9, CA-F13.10 |
| `…::test_sincronizar_linha_invalida_ignorada__CA_F13_19` · `test_sincronizar_503__CA_F13_19` | API BE | CA-F13.19, borda 20 |
| `tests/api/test_app.py` (guarda de rotas) | API BE | 5 rotas novas |
| `frontend/…/core/api/recorrencias.api.spec.ts` | unitário FE | §6 |
| `…/features/recorrencias/recorrencias.page.spec.ts` › `lista_com_estado_e_proximo_mes__CA_09_1` | unitário FE | CA-09.1, CA-F13.20 |
| `…` › `acoes_por_estado__CA_F13_21` | unitário FE | CA-F13.21 |
| `…` › `vazio_erro_e_recarga__CA_F13_26` | unitário FE | CA-F13.26 |
| `…/features/recorrencias/recorrencia-form.dialog.spec.ts` › `novo_e_edicao__CA_F13_22` | unitário FE | CA-F13.22 |
| `…` › `erros_no_campo__CA_F13_23` | unitário FE | CA-F13.23 |
| `…` › `aviso_retroativo_e_vigencia__CA_F13_24` | unitário FE | CA-F13.24 (aviso; a sincronização ao salvar está no spec da página) |
| `…/core/state/conexao.store.spec.ts` › `sincroniza_na_abertura__CA_F13_25` (1 e 3) · `abertura_sem_nada_a_gerar_fica_em_silencio__CA_F13_25` · `abertura_com_planilha_fora_nao_sincroniza__CA_F13_25` · `falha_da_sincronizacao_nao_quebra_a_abertura__F13` · `tentar_novamente_que_reconecta_sincroniza__F13_borda_23` | unitário FE | CA-F13.25, CA-10.1..10.3 (disparo), borda 23 |
| `…/features/recorrencias/recorrencias.page.spec.ts` › `cartoes_abaixo_de_600px__CA_F13_20` · `pausar_reativar_e_encerrar__CA_F13_21` · `status_recusado_avisa_e_recarrega__F13` · `salvar_sincroniza_e_avisa_uma_vez__CA_F13_24` | unitário FE | CA-F13.20, .21, .24 |
| Conferência visual em 360 px e 1280 px, claro e escuro | manual | CA-F13.26 |

---

## 9. Divisão em tarefas

| Tarefa | Escopo nesta feature | Arquivos principais |
|---|---|---|
| **T-028** (BE) | `recorrencia_service` (listar com ordem e `proximo_mes`, criar, editar, mudar status com reativação sem retroativos); schemas `RecorrenciaEntrada`/`RecorrenciaSaida`/`StatusEntrada`; router `/api/recorrencias` (GET/POST/PUT/PATCH); dependência; guarda de rotas; precisões em `03` §6.2/§6.3. O modelo, a aba e os repositórios já existem (F-03). | `backend/app/services/recorrencia_service.py`, `backend/app/api/routers/recorrencias.py`, `backend/app/api/{schemas.py,deps.py}`, `backend/app/main.py`, `backend/tests/unit/test_recorrencia_service.py`, `backend/tests/api/{test_recorrencias.py,test_app.py}` |
| **T-029** (BE) | `recorrencia_service.sincronizar` (algoritmo de `03` §4.4 + defesa do §3.2.5 + trava), `POST /api/recorrencias/sincronizar`; precisões em `03` §4.4. | `backend/app/services/recorrencia_service.py`, `backend/app/api/routers/recorrencias.py`, `backend/app/api/schemas.py`, `backend/tests/unit/test_sincronizacao.py`, `backend/tests/api/test_recorrencias.py` |
| **T-030** (FE) | `RecorrenciasApi`, modelo, página `/recorrencias` (lista, menu por estado, confirmação de encerrar), `recorrencia-form.dialog`, sincronização na abertura e no "Tentar novamente", e após salvar/reativar (Q5). | `frontend/src/app/core/api/recorrencias.api.ts`, `frontend/src/app/core/models/recorrencia.ts`, `frontend/src/app/core/state/conexao.store.ts` (ou `core/state/sincronizacao.ts`), `frontend/src/app/features/recorrencias/{recorrencias.page.*,recorrencia-form.dialog.*}` + specs |

Ordem: T-028 → T-029 → T-030 (T-030 também depende de T-016 e T-012, concluídas).

---

## 10. Decisões tomadas nesta feature

| Decisão | Motivo | Virou ADR? |
|---|---|---|
| Validação de categoria e forma pela mesma `validar_categoria_e_forma` de F-06/F-12. | Mesmas mensagens e códigos em todo o app. | Não |
| Edição: todos os campos, inclusive o tipo; categoria atual inativa permitida; preserva status, marca d'água e `criado_em`. | Mesmo comportamento de F-08 (Q1); a marca d'água é o que garante CA-09.2 e RN-10. | Não |
| Transição inválida e edição de encerrada → 422 no campo `status`, sem código de erro novo. | `03` §6.2 já cobre "regra violada num campo" com 422. | Não |
| `proximo_mes` calculado na resposta, nunca gravado; `null` para pausada e encerrada. | Deriva de colunas existentes; nenhuma coluna nova na planilha. | Não |
| Sincronização pula mês que já tem lançamento da recorrência, mas avança a marca d'água. | As escritas de lançamentos e de marcas d'água são chamadas separadas; sem isso, uma falha entre elas duplicaria na próxima abertura. | Não |
| Uma sincronização por vez no processo (trava). | Duas abas abrindo juntas não podem gerar em dobro (CA-10.2). | Não |
| Sem nada a gerar, nenhuma escrita. | Abrir o app várias vezes não gasta cota da API do Google (`02` §5.5). | Não |
| Nome e cor da categoria na lista vêm do `CategoriasStore`, não da API de recorrências. | O contrato de `03` §6.3 não traz nome/cor na `Recorrencia`; o store já está carregado. | Não |
| Tipo como lista de seleção (Gasto/Receita), como na edição de lançamento (T-030). | Sem módulo novo do Material; mesmo controle do diálogo de F-08. | Não |
| Meses de início e fim como botões com o datepicker ano → mês (como o seletor de período de F-11); "Sem fim" com botão para limpar (T-030). | Um campo de data mostraria "01/07/2026" num campo de mês. | Não |
| Aviso retroativo só enquanto nada foi gerado (criação, ou ativa nunca gerada), com os meses por extenso e o ano em cada um (T-030). | Depois de gerar, mudar o início não gera para trás (RN-10): o aviso estaria errado. | Não |
| Um aviso por ação, juntando os textos ("Recorrência criada. 3 lançamentos recorrentes gerados."); no "Tentar novamente", junto do "Conexão… restabelecida." e com uma só recarga (T-030). | Dois avisos seguidos fariam um apagar o outro; duas recargas seriam pedidos à toa. | Não |
| `SincronizacaoRecorrencias` em `core/state/sincronizacao.ts` só chama e conta; quem chama monta o aviso e decide a recarga (T-030). | Usado pelo `ConexaoStore` (abertura, reconexão) e pela página (salvar, reativar). | Não |
| Validadores de valor e de texto movidos para `core/utils/validadores.ts`, usados pelos dois diálogos (T-030). | Mesmas regras e mensagens em lançamento e recorrência, sem cópia. Sem mudança de comportamento em F-06. | Não |
| `RecorrenciaService` recebe também o repositório de lançamentos (T-029). | A sincronização insere lançamentos e consulta os já gerados (defesa de §3.2.5). | Não |
| A trava é um `threading.Lock` do módulo de serviço, não da requisição (T-029). | O serviço é criado a cada requisição; a trava tem de valer para o processo inteiro. | Não |
| `StatusRecorrencia.rotulo` ("Ativa", "Pausada", "Encerrada") no domínio, como os outros enums (T-028). | Mensagem de transição inválida em pt-BR sem tabela de rótulos no serviço. | Não |
| Empate de status e descrição na listagem → `criado_em` (T-028). | Ordem estável entre recargas. | Não |
| Reativação usa o mês do mesmo relógio injetável de `criado_em`/`atualizado_em` (T-028). | Um só relógio nos testes; RN-11 testado com data fixa. | Não |
| Sem excluir recorrência. | REQ-09 pede encerrar, não excluir; a categoria usada por recorrência encerrada continua "em uso" (F-05). | Não |
| Categoria desativada ou apagada não para a geração (Q1). | Desativar só esconde a categoria dos lançamentos novos (CA-11.4); parar a recorrência é pausar/encerrar. Fecha a pendência cruzada de F-05. | Não |
| Mês corrente gerado mesmo antes do dia (Q2). | É o algoritmo de `03` §4.4 (por mês, não por dia); a conta já entra no saldo do mês. | Não |
| Encerrada é definitiva: não gera, não edita, não reativa (Q3). | RN-11 só prevê reativar pausada; encerrar é a forma de parar de vez (sem excluir). | Não |
| Fim da vigência não muda o status (Q4). | A sincronização só avança a marca d'água; a tela explica "Vigência terminou em …". | Não |
| Sincronização logo após salvar ou reativar na tela (Q5). | O usuário vê na hora os lançamentos devidos; P-05 continua valendo para a abertura. | Não |
| `mes_inicio` no passado sem limite, com aviso no diálogo (Q6). | CA-10.1 exige o retroativo; o aviso evita surpresa com muitos lançamentos. | Não |

---

## 11. Questões em aberto

**Respondidas em 2026-10-01 — nenhuma em aberto.** Em todas, o usuário escolheu a opção recomendada.

- [x] **Q1** → **gera normalmente** com categoria desativada ou apagada (§3.2.4).
- [x] **Q2** → o mês corrente é gerado **já**, mesmo com o dia ainda por vir (§3.2.3).
- [x] **Q3** → encerrar é **definitivo**: não gera, não edita, não reativa (§3.1.4–5, §3.3.3).
- [x] **Q4** → fim da vigência **não muda o status**; a tela mostra "Vigência terminou em …" (§3.1.8).
- [x] **Q5** → sincroniza **logo após salvar ou reativar** na tela (§3.3.6).
- [x] **Q6** → `mes_inicio` no passado **sem limite**, com aviso no diálogo (§3.1.3, §3.3.4).
- [x] **Q7** → **P-04 e P-05 confirmadas** (`01` → 1.2).

Texto original das questões, para registro:

- **Q1 — Categoria desativada (pendência de F-05).** Recorrência ativa ligada a uma categoria desativada ou apagada à mão: (a) **Recomendado:** gera normalmente — desativar a categoria só a esconde dos lançamentos novos (CA-11.4); para parar a recorrência existem pausar/encerrar; (b) pula o mês e avança a marca d'água (o lançamento daquele mês se perde); (c) não gera nem avança até a categoria voltar a ficar ativa (os meses acumulam e saem juntos depois).
- **Q2 — Mês corrente antes do dia.** Hoje 01/10, recorrência no dia 10: (a) **Recomendado:** gera já o lançamento de 10/10 (data futura dentro do mês; é o que o algoritmo de `03` §4.4 faz e mostra a conta do mês no saldo); (b) só gera quando o dia chegar (o lançamento aparece na primeira abertura a partir de 10/10).
- **Q3 — Encerrar.** (a) **Recomendado:** encerrada é definitiva — não gera, não se edita e não volta a ficar ativa (RN-11 só fala em reativar **pausada**); (b) encerrada pode ser reativada como uma pausada.
- **Q4 — Fim da vigência.** Recorrência ativa cujo `mes_fim` já passou e foi todo gerado: (a) **Recomendado:** continua `ATIVA`, sem próximo mês, e a tela mostra "Vigência terminou em agosto de 2026"; (b) a sincronização a marca como `ENCERRADA` automaticamente.
- **Q5 — Quando gerar depois de criar/editar/reativar.** (a) **Recomendado:** a tela chama a sincronização logo após salvar ou reativar, e os lançamentos devidos aparecem na hora; (b) só na próxima abertura do app (P-05 ao pé da letra).
- **Q6 — Mês de início no passado.** (a) **Recomendado:** aceito sem limite, com aviso no diálogo de quantos meses serão gerados (CA-10.1 exige o retroativo); (b) até 12 meses atrás; (c) não aceitar meses passados (só a partir do corrente).
- **Q7 — Premissas P-04 e P-05** (hoje "A confirmar" em `01`): recorrência com **valor fixo** (contas variáveis geradas com valor estimado e ajustadas à mão) e geração **ao abrir o app** (não em segundo plano). Confirmar as duas, ou ajustar?

---

## Revisões

| Data | Alteração |
|---|---|
| 2026-10-01 | Criação (`/especificar-feature F-13`). Status `Rascunho` — 7 questões em aberto. Resolve (pendente de Q1) a pendência cruzada de F-05. |
| 2026-10-01 | Q1–Q7 respondidas (todas na opção recomendada) → status **Aprovada**. Seis decisões em §10. P-04 e P-05 confirmadas (`01` → 1.2). Precisões em `03` §4.4/§6.2/§6.3 ficam para T-028/T-029. |
| 2026-10-01 | T-028 concluída: CA-F13.1 a .8 verificados por teste; parte da API de CA-09.1 e CA-09.2. `03` → 1.31 (§3, §6.2, §6.3). Três decisões em §10. |
| 2026-10-01 | T-029 (plano, aprovado pelo usuário): §3.2.1 editar/mudar status esperam a sincronização; §3.2.3 `atualizado_em` ao avançar a marca d'água; §3.2.6 recorrência apagada à mão durante a sincronização não é erro. |
| 2026-10-01 | T-029 concluída: CA-F13.9 a .19, CA-09.2 e CA-10.4 verificados por teste; parte da API de CA-10.1 a 10.3 (falta o disparo na abertura, T-030). `03` → 1.32 (§3, §4.4). Duas decisões em §10. |
| 2026-10-01 | T-030 concluída → feature **Concluída**. CA-09.1, CA-10.1 a 10.3 e CA-F13.20 a .25 verificados por teste; CA-F13.26 depende da conferência visual em 360 px. Seis decisões em §10. `03` → 1.33. |
