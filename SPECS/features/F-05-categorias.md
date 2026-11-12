# F-05 — Categorias

| Campo | Valor |
|---|---|
| Feature | F-05 |
| Marco | M1 |
| Status | Concluída |
| Requisitos | REQ-11 (CA-11.1 a CA-11.4) |
| Regras | RN-12; RN-15 (já semeada em F-03); base de RN-04 para F-06 |
| Depende de | F-03 (**Concluída**), F-04 (**Concluída**) |
| Tarefas | T-013, T-014 |
| Atualizado em | 2026-09-30 |

> **IDs de critério:** herdados de `01` mantêm o ID original (**CA-11.1** …). Os refinados usam **`CA-F05.y`**.

---

## 1. Objetivo

Deixar o usuário organizar as próprias categorias: criar, renomear, trocar a cor, desativar e excluir — sem nomes repetidos e sem perder o histórico dos lançamentos que já usam uma categoria.

---

## 2. Escopo

**Inclui**
- `categoria_service` (backend): listar, criar (com geração de slug), atualizar (nome, cor, ativa), excluir com bloqueio de uso (RN-12).
- Router `/api/categorias` — GET/POST/PUT/DELETE (`03` §6.1) — e os códigos 409 `CATEGORIA_DUPLICADA` e `CATEGORIA_EM_USO` (`03` §6.2).
- Composição em `api/deps.py`: **uma** `CacheAbas` compartilhada e os repositórios de planilha (sugestão registrada em T-009).
- Página `/categorias` (frontend), diálogo de criar/editar, `CategoriasApi` e `CategoriasStore` (`03` §8.2).

**Não inclui** (e onde será tratado)
- Seed das 15 categorias padrão — já feito pelo bootstrap (**F-03**, RN-15).
- Validar categoria ativa e do mesmo tipo num lançamento (RN-04, códigos `CATEGORIA_INATIVA` e `CATEGORIA_TIPO_INCOMPATIVEL`) — **F-06** / T-015.
- Exibir o nome atual da categoria em cada lançamento (o "efeito" de CA-11.2 na tela) — **F-07** / T-017–T-018. Aqui se garante a causa: o lançamento guarda só o `categoria_id`.
- Recorrência ativa ligada a uma categoria desativada: se a geração continua ou pula o mês — decisão de **F-13** (anotada em §11 como pendência cruzada, não bloqueia F-05).
- Orçamento por categoria — fora de escopo da v1 (`01` §6).

---

## 3. Comportamento detalhado

### 3.1 Regras do nome e da unicidade (RN-12)

1. O nome é normalizado antes de gravar (Q1): espaços nas pontas removidos e sequências de espaços no meio reduzidas a um só ("Pet   Shop" → "Pet Shop"). Depois disso, precisa ter **1 a 40 caracteres**; fora disso → 422 `VALIDACAO` no campo `nome`.
2. **Chave de comparação** para unicidade: nome normalizado, **sem acentos** (decomposição Unicode, descartando as marcas) e **sem diferenciar maiúsculas** (`casefold`). Assim `Saúde`, `saude` e `SAUDE` são o mesmo nome.
3. Unicidade **por tipo**: pode existir "Outros" em GASTO e "Outros" em RECEITA.
4. A comparação considera **todas** as categorias do tipo, ativas e inativas (uma inativa ainda ocupa o nome).
5. Ao renomear, a própria categoria é desconsiderada: "mercado" → "Mercado" é permitido.
6. Violação → 409 `CATEGORIA_DUPLICADA`, mensagem: `Já existe uma categoria de gasto chamada "Mercado".` (ou "de receita").

### 3.2 Slug (`id`) — `03` §5.2

1. Gerado **uma vez**, na criação, a partir do nome: minúsculas, sem acento, qualquer sequência de caracteres fora de `[a-z0-9]` vira um `-`, sem `-` nas pontas. "Contas da casa" → `contas-da-casa`.
2. **Imutável**: renomear não muda o `id` (é o que liga os lançamentos à categoria — CA-11.2).
3. Colisão com um `id` existente (de qualquer tipo): acrescenta `-2`, `-3`, … até ficar livre. "Outros" em RECEITA, havendo `outros` em GASTO → `outros-2`.
4. Nome sem nenhum caractere aproveitável (ex.: "!!!") → base `categoria`.
5. O `id` de uma categoria **excluída** pode ser reutilizado — a exclusão só acontece quando nada a referencia.

### 3.3 Tipo

O tipo (GASTO/RECEITA) é escolhido na criação e **não muda** depois: o `PUT` não tem `tipo` (`03` §6.1). Mudar o tipo tornaria incompatíveis os lançamentos já vinculados (RN-04).

### 3.4 Cor

1. Formato `#RRGGBB`, gravado em maiúsculas (`#e57373` → `#E57373`); outro formato → 422 `VALIDACAO`.
2. **Na tela, paleta fixa de 24 cores (Q2):** as 15 das categorias padrão (F-03 §3.4) e mais 9, pelo mesmo critério (distinguíveis entre si e legíveis nos temas claro e escuro):

   | Origem | Cores |
   |---|---|
   | Padrão (15) | `#E57373` `#FF8A65` `#7986CB` `#4FC3F7` `#4DD0E1` `#F06292` `#7E57C2` `#FFB74D` `#A1887F` `#BA68C8` `#90A4AE` `#66BB6A` `#9CCC65` `#26A69A` `#AED581` |
   | Extras (9) | `#64B5F6` `#FFD54F` `#DCE775` `#4DB6AC` `#9575CD` `#F48FB1` `#FF7043` `#8D6E63` `#78909C` |

   Ao **criar**, vem pré-selecionada a primeira cor da paleta, na ordem da tabela, que nenhuma categoria daquele tipo usa; se todas estiverem em uso, a primeira. Ao **editar** uma categoria cuja cor não está na paleta (editada à mão na planilha), essa cor aparece como uma opção extra, selecionada.
3. A **API** aceita qualquer `#RRGGBB` — a paleta é da interface, não regra de negócio.

### 3.5 Ativar / desativar (CA-11.4)

1. `PUT` com `ativa: false` desativa; `true` reativa. Nada mais muda.
2. Categoria inativa **não aparece** para novos lançamentos (`GET /api/categorias` sem `incluir_inativas` a omite — é o que os formulários de F-06 usam).
3. Continua em relatórios, listagens e na página `/categorias` (com `incluir_inativas=true`), marcada como "Inativa".
4. Desativar ou excluir a **última** categoria ativa de um tipo é **permitido** (Q5). O formulário de F-06 mostrará "Nenhuma categoria de gasto ativa. Crie ou reative uma em Categorias." (ou "de receita").

### 3.6 Excluir (RN-12, CA-11.3)

1. Permitido **só** se nenhum lançamento e nenhuma recorrência (em qualquer status, inclusive pausada ou encerrada) tiver aquele `categoria_id`.
2. Em uso → 409 `CATEGORIA_EM_USO`, mensagem: `A categoria "Mercado" está em uso em lançamentos ou recorrências e não pode ser excluída. Desative-a para que não apareça mais em novos lançamentos.`
3. **A tela sabe antes (Q4, opção B):** a listagem traz `em_uso` por categoria. Numa categoria em uso, "Excluir" abre direto o diálogo "Esta categoria está em uso em lançamentos ou recorrências e não pode ser excluída. Deseja desativá-la?" [Cancelar] [Desativar]; confirmando, a tela faz o `PUT` com `ativa: false`. Nas demais, a confirmação normal de exclusão. O 409 continua no backend como proteção (ex.: outra aba criou um lançamento no meio tempo) e, se acontecer, aparece como aviso do interceptor.
4. `em_uso` é calculado pelo backend a cada listagem: `true` se algum lançamento ou recorrência válidos tiverem aquele `categoria_id` — a mesma regra do bloqueio (item 1). As leituras de `Lancamentos` e `Recorrencias` passam pelo cache (`02` §5.5).
5. Linhas **inválidas** da planilha (ignoradas pela leitura, CA-16.3) não contam como uso — o app não as enxerga.
6. Excluir **todas** as categorias faz o bootstrap semear as 15 padrão de novo no próximo início (F-03, borda 21). A tela avisa isso na confirmação de exclusão da última categoria restante.

### 3.7 Listagem

1. `GET /api/categorias?tipo=&incluir_inativas=`: `tipo` opcional (`GASTO`/`RECEITA`; outro valor → 422); `incluir_inativas` padrão `false`.
2. **Ordem (Q3):** dentro de cada tipo, ativas primeiro e inativas no fim; em cada grupo, alfabética pelo nome sem diferenciar acento e maiúsculas (mesma chave da unicidade, §3.1.2). Sem filtro de tipo, GASTO vem antes de RECEITA. A página e os formulários de F-06 usam a ordem da API, sem reordenar.

### 3.8 Página `/categorias` (T-014)

1. Duas seções empilhadas, **Gastos** e **Receitas**, cada uma com o botão "Nova categoria" (tipo já definido pela seção).
2. Cada item: bolinha com a cor, nome, selo "Inativa" quando for o caso, e as ações **Editar** (nome e cor), **Desativar/Reativar** e **Excluir**.
3. Criar e editar pelo mesmo diálogo (`categoria-form.dialog`): campo nome (com contador até 40) e a paleta de §3.4 (cada cor é um botão com `aria-label` do código da cor e `aria-pressed` na escolhida); o tipo aparece como texto fixo. Erro 409/422 mantém o diálogo aberto com os dados e marca o campo (`detalhes[].campo`; para 409, o campo `nome`).
4. Excluir segue §3.6.3: categoria em uso → diálogo que oferece desativar; sem uso → confirmação (`confirmacao-dialog` de F-04) mostrando o nome.
5. Estados: carregando (`carregando`), vazio por seção (`estado-vazio`: "Nenhuma categoria de gasto."), erro (banner/aviso de F-04).
6. Após qualquer escrita bem-sucedida: aviso curto ("Categoria criada.", "Categoria atualizada.", "Categoria excluída."), recarga do `CategoriasStore` e `DadosStore.incrementar()` (`03` §7.1) — nomes e cores mudados aparecem nas outras telas.
7. Utilizável em 360 px (RNF-07): ações do item num menu (⋮) quando não couberem.

### 3.9 `CategoriasStore` (`03` §8.2)

1. Carrega `GET /api/categorias?incluir_inativas=true` **uma vez**, na primeira vez que alguém a usa; recarrega após escrita e quando `DadosStore.versao` muda.
2. Expõe `todas`, `porTipo(tipo)` (para a página) e `ativasPorTipo(tipo)` (para os formulários de F-06).
3. Não calcula nada além de filtrar e ordenar o que veio da API.

---

## 4. Critérios de aceite

**Herdados de `01`**

- [x] **CA-11.1** Dado um nome já existente no mesmo tipo (ignorando maiúsculas/acentos), quando o usuário tenta criar/renomear, então o sistema recusa com mensagem clara.
- [x] **CA-11.2** Dado uma categoria renomeada, então todos os lançamentos dela exibem o novo nome, inclusive os antigos. *(F-05 garante que renomear não altera `id` nem toca a aba `Lancamentos` — verificado em T-013; a exibição foi verificada em F-07 / T-018.)*
- [x] **CA-11.3** Dado uma categoria com lançamentos ou recorrências, quando o usuário tenta excluir, então o sistema recusa e sugere desativar. *(T-013: recusa 409 com a sugestão na mensagem e `em_uso` na listagem; T-014: "Excluir" em categoria em uso oferece desativar sem enviar `DELETE`.)*
- [~] **CA-11.4** Dado uma categoria desativada, então ela não aparece para novos lançamentos, mas continua nos relatórios e na listagem. *(T-013: listagem padrão sem inativas; T-014: página mostra as inativas com selo e `CategoriasStore.ativasPorTipo` as exclui — os formulários de F-06 o usam; relatórios e listagem de lançamentos em F-07/F-09.)*

**Refinados — backend (T-013)**

- [x] **CA-F05.1** Dado "Mercado" em GASTO, quando se cria "mercado", "MERCADO" ou "Mércado" em GASTO, então 409 `CATEGORIA_DUPLICADA` com a mensagem de §3.1.6, e nada é gravado.
- [x] **CA-F05.2** Dado "Outros" em GASTO, quando se cria "Outros" em RECEITA, então 201, com `id` `outros-2`.
- [x] **CA-F05.3** Dado uma categoria, quando é renomeada para outra grafia do próprio nome ("mercado" → "Mercado"), então 200.
- [x] **CA-F05.4** Dado a criação de "Contas da Casa (fixas)", então o `id` é `contas-da-casa-fixas`; e dado um nome sem letras nem dígitos, então a base do `id` é `categoria`.
- [x] **CA-F05.5** Dado uma categoria renomeada, quando se compara a planilha antes e depois, então o `id` é o mesmo e a aba `Lancamentos` não recebeu nenhuma escrita (CA-11.2).
- [x] **CA-F05.6** Dado uma categoria usada por um lançamento, ou por uma recorrência (mesmo pausada ou encerrada), quando se tenta excluir, então 409 `CATEGORIA_EM_USO` com a mensagem de §3.6.2, e a categoria continua lá.
- [x] **CA-F05.7** Dado uma categoria sem uso, quando excluída, então 204 e ela some da aba `Categorias`.
- [x] **CA-F05.8** Dado categorias ativas e inativas, quando `GET /api/categorias` é chamado sem `incluir_inativas`, então só as ativas vêm; com `incluir_inativas=true`, todas; com `tipo=GASTO`, só as de gasto (CA-11.4).
- [x] **CA-F05.9** Dado `PUT` com `ativa: false` e depois `true`, então a categoria some e volta da listagem padrão, sem mudar nome, cor nem `id`.
- [x] **CA-F05.10** Dado `id` inexistente em `PUT` ou `DELETE`, então 404 `NAO_ENCONTRADO`.
- [x] **CA-F05.11** Dado cor fora de `#RRGGBB`, nome vazio (ou só espaços) ou `tipo` fora do enum, então 422 `VALIDACAO` com o campo em `detalhes`; e dado cor `#e57373`, então é gravada `#E57373`.
- [x] **CA-F05.12** Dado a planilha inacessível, quando qualquer endpoint de categorias é chamado, então 503 com o código da causa (`03` §4.5).
- [x] **CA-F05.13** Dado a resposta de qualquer endpoint, então a categoria sai no formato de §6 (`snake_case`, `tipo` em maiúsculas, `ativa` e `em_uso` booleanos).
- [x] **CA-F05.21** Dado categorias com e sem lançamentos ou recorrências (em qualquer status), quando `GET /api/categorias` é chamado, então `em_uso` é `true` exatamente nas que têm uso (Q4).
- [x] **CA-F05.22** Dado "saúde", "Alimentação" e "Mercado" ativas e "Assinaturas" inativa em GASTO, quando listadas, então a ordem é Alimentação, Mercado, saúde, Assinaturas; e sem filtro, GASTO antes de RECEITA (Q3).
- [x] **CA-F05.23** Dado o nome `"  Pet   Shop  "`, então é gravado `Pet Shop`; e dado um nome com 41 caracteres após a normalização, então 422 no campo `nome` (Q1).

**Refinados — frontend (T-014)**

- [x] **CA-F05.14** Dado a página `/categorias`, quando abre, então mostra as seções Gastos e Receitas com as categorias de cada tipo, cor, nome e selo "Inativa" nas inativas.
- [x] **CA-F05.15** Dado "Nova categoria" na seção Receitas, quando o usuário salva um nome válido, então a categoria aparece na seção Receitas, um aviso confirma e o diálogo fecha.
- [x] **CA-F05.16** Dado um nome duplicado no diálogo, quando o usuário salva, então o diálogo continua aberto com os dados e o campo nome mostra a mensagem do backend (CA-11.1).
- [x] **CA-F05.17** Dado "Desativar" numa categoria, então ela passa a mostrar "Inativa" e a opção vira "Reativar"; e `CategoriasStore.ativasPorTipo` deixa de incluí-la (CA-11.4).
- [x] **CA-F05.18** Dado "Excluir" numa categoria com `em_uso`, então nenhum `DELETE` é enviado: abre o diálogo que oferece desativar e, confirmado, a categoria fica "Inativa" (CA-11.3). Numa sem uso, a confirmação mostra o nome e, confirmada, a categoria some.
- [x] **CA-F05.19** Dado qualquer escrita bem-sucedida, então `CategoriasStore` recarrega e `DadosStore.versao` aumenta 1.
- [~] **CA-F05.20** Dado a janela de 360 px, então a página não rola na horizontal e todas as ações de cada item são alcançáveis (RNF-07). *(T-014: ações sempre num menu ⋮ e textos com quebra; conferência visual pendente, junto com a de F-04.)*
- [x] **CA-F05.24** Dado "Nova categoria" em GASTO com as 11 cores padrão de gasto em uso, então o diálogo mostra as 24 cores da paleta e pré-seleciona a primeira não usada por nenhuma categoria de gasto; e ao editar uma categoria com cor fora da paleta, essa cor aparece selecionada como opção extra (Q2).

---

## 5. Casos de borda

| # | Caso | Comportamento esperado | Regra |
|---|---|---|---|
| 1 | Criar "mercado" com "Mercado" existente (GASTO) | 409 `CATEGORIA_DUPLICADA`. | RN-12 |
| 2 | Criar "Saude" com "Saúde" existente | 409 — acentos não contam. | RN-12 |
| 3 | Criar "Mercado" em RECEITA com "Mercado" em GASTO | 201; `id` `mercado-2`. | RN-12 |
| 4 | Criar "Pet" com uma "Pet" **inativa** no mesmo tipo | 409 — inativa ainda ocupa o nome. | RN-12 |
| 5 | Renomear "Mercado" → "MERCADO" | 200. | RN-12 |
| 6 | Renomear "Mercado" → "Lazer" (existente no mesmo tipo) | 409, nada muda. | RN-12 |
| 7 | Nome `"  Pet   Shop  "` | Gravado como `Pet Shop`. | Q1 |
| 7a | Nome com 40 caracteres / 41 caracteres | Aceito / 422 no campo `nome`. | Q1 |
| 8 | Nome `"!!!"` | `id` base `categoria` (`categoria-2` se ocupado). | §3.2.4 |
| 9 | Criar categoria com o nome de uma que foi excluída | Permitido; o `id` antigo pode ser reutilizado. | §3.2.5 |
| 10 | Excluir categoria usada só por recorrência **encerrada** | 409 `CATEGORIA_EM_USO`. | RN-12 |
| 11 | Excluir categoria usada só por lançamento de anos atrás | 409. | RN-12 |
| 12 | Excluir categoria referenciada só por uma linha **inválida** da planilha | Permitido (o app não enxerga a linha). | §3.6.5 |
| 13 | Excluir a última categoria existente | Permitido; a confirmação avisa que as 15 padrão voltam no próximo início. | F-03 borda 21 |
| 14 | Cor `#e57373` | Gravada `#E57373`. | §3.4 |
| 15 | Cor `red`, `#FFF`, `E57373` | 422. | §3.4 |
| 16 | `PUT` com `tipo` no corpo | Campo ignorado; o tipo não muda. | §3.3 |
| 17 | `GET ?tipo=gasto` (minúsculo) ou `?tipo=OUTRO` | 422. | `02` §7 |
| 18 | Desativar ou excluir a última ativa do tipo | Permitido; F-06 mostra a orientação para criar ou reativar. | Q5 |
| 22 | Categoria em uso cujo último lançamento é excluído (em outra tela) | Na próxima listagem `em_uso` vira `false` e "Excluir" volta a excluir. | Q4 |
| 23 | Categoria com cor `#123456` (editada à mão, fora da paleta) | Aparece na lista com essa cor; no diálogo de edição, como opção extra selecionada. | Q2 |
| 19 | Duas abas do navegador criando o mesmo nome ao mesmo tempo | Pode passar duas vezes (checagem e escrita não são atômicas). Aceito: app de um usuário; a planilha continua válida, e a duplicata pode ser renomeada. | RNF-01 |
| 20 | Usuário edita a aba `Categorias` à mão criando dois nomes iguais | A listagem mostra os dois; a unicidade só é cobrada nas escritas do app. | RN-14 |
| 21 | Planilha inacessível ao abrir `/categorias` | 503 → banner de F-04; a página mostra o estado de erro, sem lista. | CA-F05.12 |

---

## 6. Contrato e dados

**API** (`03` §6.1, sem alteração de rota)

| Método | Caminho | Entrada | Saída |
|---|---|---|---|
| GET | `/api/categorias` | `?tipo=GASTO\|RECEITA` (opcional) `&incluir_inativas=true\|false` (padrão `false`) | `200 [Categoria]` |
| POST | `/api/categorias` | `{nome, tipo, cor}` | `201 Categoria` · `409 CATEGORIA_DUPLICADA` · `422` |
| PUT | `/api/categorias/{id}` | `{nome, cor, ativa}` | `200 Categoria` · `404` · `409 CATEGORIA_DUPLICADA` · `422` |
| DELETE | `/api/categorias/{id}` | — | `204` · `404` · `409 CATEGORIA_EM_USO` |

Esquema `Categoria` (acrescentado em `03` §6.3 — `03` → 1.14):

```jsonc
{ "id": "contas-da-casa", "nome": "Contas da casa", "tipo": "GASTO",
  "cor": "#4FC3F7", "ativa": true, "criado_em": "2026-09-29T10:15:00",
  "em_uso": true }   // calculado a cada listagem (§3.6.4); não é coluna da planilha
```

**Erros** (`03` §6.2 — códigos já previstos): 409 `CATEGORIA_DUPLICADA`, 409 `CATEGORIA_EM_USO`, 404 `NAO_ENCONTRADO`, 422 `VALIDACAO`, 503 da planilha. `api/erros.py` ganha os dois códigos 409 no mapa (hoje só há um comentário reservando).

**Planilha** — aba `Categorias` (`03` §5.2), lida e escrita pelo `CategoriaRepositoryPlanilha` de F-03. Para o bloqueio de exclusão e para `em_uso`, **leitura** das abas `Lancamentos` e `Recorrencias` (`categoria_id`), pelo cache. Nenhuma coluna nova; `versao_schema` não muda.

---

## 7. Interface

- **Rota:** `/categorias` (página já existe como placeholder em F-04).
- **Componentes:** `CategoriasPage`, `categoria-form.dialog` (criar/editar), `CategoriasApi` (`core/api/`), `CategoriasStore` (`core/state/`), modelo `Categoria` (`core/models/`). Reusa `confirmacao-dialog`, `estado-vazio`, `carregando` e `Avisos` de F-04.
- **Estados:** carregando · vazio por seção · erro (banner) · sucesso.
- **Mensagens (pt-BR):**
  - Avisos: "Categoria criada.", "Categoria atualizada.", "Categoria desativada.", "Categoria reativada.", "Categoria excluída."
  - Confirmação de exclusão: título "Excluir categoria?", texto `A categoria "<nome>" será excluída.` (+ aviso de re-seed se for a última — §3.6.6), botão "Excluir".
  - Categoria em uso: título "Categoria em uso", texto "Esta categoria está em uso em lançamentos ou recorrências e não pode ser excluída. Deseja desativá-la?", botão "Desativar".
  - Contador do nome: "<n>/40".
  - Vazio: "Nenhuma categoria de gasto." / "Nenhuma categoria de receita."
  - Erros: os do backend (§3.1.6, §3.6.2), sem reescrita.

---

## 8. Plano de testes

Backend: serviço com repositórios **em memória** (`02` §8); API com `TestClient` + `dependency_overrides`. Frontend: Vitest com `HttpTestingController`.

| Teste | Nível | Cobre |
|---|---|---|
| `tests/unit/test_categoria_service.py::test_nome_duplicado_ignora_caixa_e_acento__RN_12` (parametrizado) | unitário BE | CA-11.1, CA-F05.1, bordas 1–2 |
| `…::test_mesmo_nome_em_outro_tipo_e_permitido__RN_12` | unitário BE | CA-F05.2, borda 3 |
| `…::test_inativa_ocupa_o_nome__RN_12` | unitário BE | borda 4 |
| `…::test_renomear_para_outra_grafia_do_proprio_nome__RN_12` | unitário BE | CA-F05.3, bordas 5–6 |
| `…::test_slug_na_criacao_e_colisao__F05_3_2` (parametrizado) | unitário BE | CA-F05.4, bordas 3, 8, 9 |
| `…::test_renomear_nao_muda_id_nem_lancamentos__CA_11_2` | unitário BE | CA-11.2, CA-F05.5 |
| `…::test_excluir_em_uso_por_lancamento_ou_recorrencia__RN_12` (parametrizado por status da recorrência) | unitário BE | CA-11.3, CA-F05.6, bordas 10–11 |
| `…::test_excluir_sem_uso__RN_12` | unitário BE | CA-F05.7 |
| `…::test_ativar_desativar_preserva_o_resto__CA_11_4` | unitário BE | CA-F05.9 |
| `…::test_nome_normalizado_e_limite__CA_F05_23` | unitário BE | CA-F05.23, bordas 7, 7a |
| `…::test_em_uso_por_lancamento_ou_recorrencia__CA_F05_21` | unitário BE | CA-F05.21, borda 22 |
| `…::test_ordem_ativas_alfabetica_inativas_no_fim__CA_F05_22` | unitário BE | CA-F05.22 |
| `tests/api/test_categorias.py::test_listar_filtra_tipo_e_inativas__CA_11_4` | API BE | CA-11.4, CA-F05.8 |
| `…::test_criar_duplicada_409__CA_11_1` | API BE | CA-11.1, CA-F05.1 |
| `…::test_excluir_em_uso_409__CA_11_3` | API BE | CA-11.3, CA-F05.6 |
| `…::test_id_inexistente_404__CA_F05_10` | API BE | CA-F05.10 |
| `…::test_validacao_422__CA_F05_11` (parametrizado: cor, nome, tipo, `?tipo=gasto`) | API BE | CA-F05.11, bordas 14, 15, 17 |
| `…::test_put_ignora_tipo__F05_3_3` | API BE | borda 16 |
| `…::test_planilha_inacessivel_503__CA_F05_12` | API BE | CA-F05.12 |
| `…::test_formato_da_resposta__CA_F05_13` | API BE | CA-F05.13 |
| `…::test_rotas_do_contrato` (OpenAPI lista exatamente as 4 rotas de §6 + health) | API BE | `03` §6.1 |
| `frontend/…/core/api/categorias.api.spec.ts` | unitário FE | §6 |
| `…/core/state/categorias.store.spec.ts` › `carrega_uma_vez_e_recarrega_apos_escrita__CA_F05_19`, `ativas_por_tipo__CA_11_4` | unitário FE | CA-F05.17, .19 |
| `…/features/categorias/categorias.page.spec.ts` › `lista_por_tipo_com_selo_inativa__CA_F05_14`, `cria_na_secao_certa__CA_F05_15`, `desativar_e_reativar__CA_F05_17`, `excluir__CA_F05_18` | unitário FE | CA-F05.14, .15, .17, .18 |
| `…/features/categorias/categoria-form.dialog.spec.ts` › `duplicada_mantem_dialogo_e_marca_nome__CA_F05_16`, `paleta_e_pre_selecao__CA_F05_24`, `cor_fora_da_paleta_na_edicao__CA_F05_24` | unitário FE | CA-F05.16, .24, borda 23 |
| Página em 360 px, temas claro e escuro | manual FE | CA-F05.20 |

---

## 9. Divisão em tarefas

| Tarefa | Escopo nesta feature | Arquivos principais |
|---|---|---|
| **T-013** (BE) | `categoria_service` (normalização, chave de unicidade, slug, ordem, `em_uso`, CRUD, bloqueio de uso), erros `CategoriaDuplicada`/`CategoriaEmUso`, schemas da API, router `/api/categorias`, composição em `deps.py` (cache único + repositórios). | `backend/app/services/categoria_service.py`, `backend/app/domain/erros.py`, `backend/app/api/{schemas.py,deps.py,erros.py,routers/categorias.py}`, `backend/app/main.py`, `backend/tests/unit/test_categoria_service.py`, `backend/tests/api/test_categorias.py` |
| **T-014** (FE) | Modelo, `CategoriasApi`, `CategoriasStore`, paleta de cores, página `/categorias` e `categoria-form.dialog`. | `frontend/src/app/core/{models/categoria.ts,api/categorias.api.ts,state/categorias.store.ts}`, `frontend/src/app/features/categorias/{categorias.page.ts,categoria-form.dialog.ts,paleta.ts}` + specs |

Ordem: T-013 → T-014 (`05` §4; T-014 também depende de T-011, já concluída).

---

## 10. Decisões tomadas nesta feature

| Decisão | Motivo | Virou ADR? |
|---|---|---|
| Unicidade compara nome sem acento e com `casefold`, contra **todas** as categorias do tipo (inclusive inativas). | RN-12 fala em "único por tipo", sem exceção para inativas; reativar uma inativa não pode criar duplicata. | Não |
| `tipo` imutável após a criação. | O `PUT` de `03` §6.1 não o inclui; mudar o tipo quebraria RN-04 nos lançamentos já vinculados. | Não |
| Excluir considera recorrências em **qualquer** status. | RN-12 diz "recorrências vinculadas", sem distinguir status; uma encerrada ainda guarda o `categoria_id`. | Não |
| Linha inválida da planilha não conta como uso. | O repositório não a enxerga (CA-16.3); tratá-la exigiria ler a aba crua só para isso. | Não |
| Composição (cache único + repositórios de planilha) entra em T-013. | É o primeiro endpoint de negócio (sugestão de T-009). | Não |
| Repositórios e cache criados **uma vez**, no lifespan, e entregues por `api/deps.py` (T-013). | Criar por requisição rebuscaria a referência de cada aba (uma chamada de metadados por aba a cada requisição) e desperdiçaria o cache. `03` → 1.15. | Não |
| Limite de 40 caracteres só no schema de **entrada** da API; o modelo de domínio aceita qualquer tamanho (T-013). | Um nome maior digitado à mão na planilha não pode virar "linha inválida" e sumir do app. | Não |
| O teste de guarda de rotas (`tests/api/test_app.py`) passa a listar exatamente as rotas implementadas (T-013). | Antes exigia só `/api/health`; cada tarefa que criar endpoint atualiza a lista junto com `03` §6.1. | Não |
| Nome: 1–40 caracteres, pontas aparadas e espaços internos reduzidos (Q1). | Nomes curtos cabem em legendas de gráfico e em 360 px; espaço duplicado costuma ser erro de digitação e atrapalharia a unicidade. | Não |
| Paleta fixa de 24 cores na interface; API aceita qualquer `#RRGGBB` (Q2). | Garante contraste nos dois temas (F-01 Q2) e cores distinguíveis nos gráficos (CA-13.1); a planilha continua podendo ser editada à mão. | Não |
| Ordem: ativas antes, alfabética sem acento/caixa; GASTO antes de RECEITA (Q3). | Previsível e igual em todas as telas; inativas no fim não atrapalham quem escolhe. | Não |
| `em_uso` na listagem; "Excluir" em categoria em uso oferece desativar sem chamar o `DELETE` (Q4-B). | O usuário recebe a sugestão de CA-11.3 antes de errar, sem precisar desligar o aviso global do interceptor; o 409 fica como proteção. `03` → 1.14. | Não |
| Última categoria ativa de um tipo pode ser desativada/excluída (Q5). | Bloquear obrigaria a criar outra antes de reorganizar; F-06 orienta quando não houver nenhuma ativa. | Não |
| Ações de cada categoria sempre num menu ⋮, em qualquer largura (T-014). | Um padrão só, que garante os 360 px (RNF-07) sem layout alternativo. | Não |
| "Excluir" de uma categoria **em uso e já inativa** aparece desabilitado como "Excluir (em uso)" (T-014). | Oferecer "Desativar" não faria sentido; o usuário vê por que não pode excluir. | Não |
| O diálogo de categoria salva por conta própria (T-014). | Só assim ele continua aberto com os dados e marca o campo quando o backend recusa (409/422). | Não |
| `CategoriasStore` guarda a `versao` carregada e só recarrega quando ela muda (T-014). | O efeito que observa `DadosStore.versao` roda pela 1ª vez depois de a página já ter pedido a carga; sem a guarda, haveria duas requisições iguais. | Não |
| Navegação lateral do shell sem `mat-nav-list` (T-014, revisão de F-04). | A lista do Material levava `@angular/forms` inteiro ao pacote inicial; sem ela, 456 kB (limite de aviso 500 kB). Decisão do usuário. | Não |

---

## 11. Questões em aberto

**Respondidas em 2026-09-30 — nenhuma em aberto.** Em todas, o usuário escolheu a opção recomendada.

- [x] **Q1** → 1 a 40 caracteres após aparar as pontas; espaços repetidos no meio viram um só (§3.1.1).
- [x] **Q2** → paleta fixa de 24 cores na interface, pré-seleção da primeira livre no tipo; API aceita qualquer `#RRGGBB` (§3.4).
- [x] **Q3** → ativas antes, alfabética sem acento/caixa, inativas no fim; GASTO antes de RECEITA (§3.7.2).
- [x] **Q4** → opção **B**: `em_uso` na listagem; "Excluir" em categoria em uso oferece desativar (§3.6.3). `03` → 1.14.
- [x] **Q5** → permitido desativar/excluir a última ativa de um tipo; F-06 orienta (§3.5.4).

**Pendência cruzada (não bloqueia F-05):** recorrência ativa ligada a uma categoria desativada — gerar o lançamento mesmo assim ou pular? RN-04 exige categoria ativa "para novos lançamentos". Decidir ao especificar **F-13**. → **Decidida em F-13 Q1 (2026-10-01): gera normalmente**; desativar só esconde a categoria dos lançamentos novos.

---

## Revisões

| Data | Alteração |
|---|---|
| 2026-09-30 | Criação (`/especificar-feature F-05`). Status `Rascunho` — 5 questões em aberto. |
| 2026-09-30 | Q1–Q5 respondidas → status **Aprovada**. Paleta de 24 cores definida; `em_uso` no contrato; CA-F05.18 fechado; CA-F05.21 a .24 e bordas 7a, 22 e 23 acrescentados. `03` → 1.14. |
| 2026-09-30 | T-013 concluída: CA-11.1 e CA-F05.1 a .13, .21 a .23 verificados por teste; CA-11.2, .3 e .4 com a parte do backend verificada (o resto é T-014/F-07). Três decisões em §10. `03` → 1.15. |
| 2026-09-30 | T-014 concluída → **feature Concluída**. CA-11.3 e CA-F05.14 a .19 e .24 verificados por teste; CA-11.2/.4 com a parte de F-05 feita (o resto é F-07/F-09); CA-F05.20 com conferência visual pendente. Cinco decisões em §10, incluindo a troca do `mat-nav-list` do shell (revisão registrada em F-04). `02` → 1.9, `03` → 1.16. |
| 2026-09-30 | **Revisão (T-016, F-06 Q3):** o diálogo de categoria passa o marcador `TRATAMENTO_LOCAL` em criar/atualizar; um 409 (nome duplicado) aparece só no campo, sem o aviso repetido do interceptor. A página (desativar/reativar/excluir), que não mostra erro em campo, continua com o aviso. Teste `duplicada_so_no_campo__CA_F06_16`. |
| 2026-10-01 | Pendência cruzada de §11 decidida em F-13 Q1: recorrência ativa com categoria desativada continua gerando. Sem mudança de comportamento em F-05. |
| 2026-11-12 | **Revisão (F-16, RN-24, CA-11.5):** "A classificar" (`a-classificar`, `a-classificar-receita`) são **reservadas**: renomear e trocar a cor continuam permitidos; excluir e desativar → 409 `CATEGORIA_RESERVADA`; JSON ganha `reservada`; a página mostra só "Editar" para elas. Trabalho em **T-036** (backend) e **T-041** (tela). |
