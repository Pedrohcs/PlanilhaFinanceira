# F-06 — Registrar lançamento

| Campo | Valor |
|---|---|
| Feature | F-06 |
| Marco | M1 |
| Status | Aprovada |
| Requisitos | REQ-01 (CA-01.1 a CA-01.5), REQ-02 (CA-02.1, CA-02.2) |
| Regras | RN-01, RN-02, RN-03, RN-04, RN-05, RN-06 |
| Depende de | F-05 (**Concluída**) |
| Tarefas | T-015, T-016 |
| Atualizado em | 2026-09-30 |

> **IDs de critério:** herdados de `01` mantêm o ID original (**CA-01.1** …). Os refinados usam **`CA-F06.y`**.

---

## 1. Objetivo

Registrar um gasto ou uma receita em poucos segundos, de qualquer tela, com a planilha recebendo uma linha correta e o app refletindo a mudança na hora — sem perder o que foi digitado se algo falhar.

---

## 2. Escopo

**Inclui**
- `lancamento_service.criar` (RN-01..06) e `POST /api/lancamentos` → `201 Lancamento` (`03` §6.1, §6.3).
- `GET /api/formas-pagamento` → `200 [{codigo, nome}]`.
- Os dois códigos 409 que faltavam: `CATEGORIA_INATIVA` e `CATEGORIA_TIPO_INCOMPATIVEL` (`03` §6.2).
- `lancamento-form.dialog` no modo **novo** (gasto ou receita), aberto pelos botões do shell — carregado sob demanda, para não pesar no pacote inicial (sugestão de T-014).
- `LancamentosApi.criar`, `FormasPagamentoStore`, interpretação do valor digitado em pt-BR.
- Marcador `TRATAMENTO_LOCAL` para o interceptor não repetir, como aviso, um 409 que o formulário já mostra no campo (Q3) — aplicado também ao diálogo de categoria de F-05.

**Não inclui** (e onde será tratado)
- Listar, filtrar e totalizar lançamentos — **F-07** (a exibição do novo lançamento na listagem e no resumo, efeito de CA-01.5, é verificada em F-07/F-09; aqui se garante a causa: `DadosStore.versao` aumenta).
- Editar e excluir — **F-08** (o mesmo diálogo ganha o modo edição em T-020).
- Compra parcelada (checkbox "Compra parcelada") — **F-12** / T-027.
- Lançamentos gerados por recorrência — **F-13**.

---

## 3. Comportamento detalhado

### 3.1 Abertura (CA-01.1)

1. "Registrar gasto" e "Registrar receita" (shell, F-04) abrem o diálogo com o **tipo fixo** pelo botão; não há troca de tipo dentro dele.
2. Título: "Registrar gasto" / "Registrar receita".
3. **Data** vem preenchida com **hoje** (relógio local, RN-02); todos os outros campos vazios — inclusive a forma de pagamento, que o usuário escolhe sempre (Q4).
4. O foco inicial fica no campo **valor**.
5. O código do diálogo é importado **sob demanda** no primeiro clique (o pacote inicial não cresce).

### 3.2 Campos e validação no cliente

| Campo | Regra | Mensagem |
|---|---|---|
| Data | obrigatória; qualquer data válida, passada ou futura (RN-02); `dd/mm/aaaa` com datepicker | "Informe uma data válida." |
| Valor | obrigatório; > 0; no máximo 2 casas (RN-01); digitação em pt-BR, regras em §3.2.1 (Q2) | "Informe um valor maior que zero." / "Use no máximo 2 casas decimais." / "Valor inválido. Ex.: 1.234,56" |
| Descrição | obrigatória; 1 a 100 caracteres depois de aparar as pontas (RN-06); contador "n/100" | "Informe a descrição." / "Use no máximo 100 caracteres." |
| Categoria | obrigatória; só **ativas** do tipo (RN-04, CA-02.1), na ordem da API; mostra a cor | "Escolha uma categoria." |
| Forma de pagamento | **gasto**: obrigatória; **receita**: opcional, com opção "Não informar" (RN-05, CA-02.2) | "Escolha a forma de pagamento." |
| Observação | opcional; até 500 caracteres; vazia vira `null` (RN-06); contador "n/500" | "Use no máximo 500 caracteres." |

Formulário **inválido** → campos marcados e **nada é enviado** (CA-01.3).

#### 3.2.1 Interpretação do valor (Q2)

Campo de texto livre (`inputmode="decimal"`), interpretado assim, na ordem:

1. `R$` e espaços (inclusive o espaço fixo) são ignorados. Sinal de menos → inválido.
2. **Com vírgula** (no máximo uma): a vírgula é o separador decimal. Antes dela, dígitos puros (`1234`) ou agrupados de 3 em 3 por pontos (`1.234`, `12.345.678`); depois dela, 1 ou 2 dígitos. `1.234,56` → 1234.56; `42,5` → 42.50.
3. **Sem vírgula:**
   - pontos só agrupando de 3 em 3 → milhar: `1.234` → 1234.00, `1.234.567` → 1234567.00;
   - um único ponto seguido de 1 ou 2 dígitos → decimal: `42.50` → 42.50, `1.5` → 1.50;
   - só dígitos → inteiro: `42` → 42.00.
4. Mais de 2 casas depois do separador decimal (`0,001`, `1.2345` que não seja milhar) → "Use no máximo 2 casas decimais."; qualquer outra forma (`abc`, `1,2,3`, `12.34.5`) → "Valor inválido. Ex.: 1.234,56".
5. Ao sair do campo, um valor válido é reescrito formatado em pt-BR com 2 casas e milhar (`42,5` → `42,50`; `1234.5` → `1.234,50`).
6. O número enviado à API é o valor interpretado (ex.: `42.5`); o frontend não faz conta nenhuma com ele.

Nenhuma categoria ativa do tipo (F-05 Q5) → no lugar do seletor, a mensagem "Nenhuma categoria de gasto ativa. Crie ou reative uma em Categorias." (ou "de receita"), com link para `/categorias`, e "Salvar" desabilitado.

### 3.3 Salvar (CA-01.2)

1. `POST /api/lancamentos` com `LancamentoEntrada`; o botão vira "Salvando…" e fica desabilitado (sem envio duplicado).
2. Sucesso (201): o diálogo fecha, um aviso confirma — "Gasto registrado." / "Receita registrada." — e `DadosStore.incrementar()` faz as telas abertas recarregarem (`03` §7.1, CA-01.5).
3. Só há o botão "Salvar", que fecha o diálogo; não existe "salvar e registrar outro" nesta versão (Q1).

### 3.4 Falhas (CA-01.4, RNF-06)

1. **Qualquer** falha mantém o diálogo aberto com tudo o que foi digitado.
2. 422 `VALIDACAO` → cada `detalhes[].campo` marca o seu campo com a mensagem do backend.
3. 409 `CATEGORIA_INATIVA` / `CATEGORIA_TIPO_INCOMPATIVEL` (a categoria mudou em outra aba) → mensagem no campo categoria, e a lista de categorias é recarregada.
4. 503 / backend fora do ar → banner de F-04; o diálogo continua aberto e "Salvar" pode ser tentado de novo.
5. **Sem aviso duplicado (Q3):** as chamadas do diálogo levam o marcador `TRATAMENTO_LOCAL` (`HttpContext`); nelas, o interceptor **não** abre aviso para 409 — a mensagem aparece só no campo. 422 já não gerava aviso; 503 e backend fora do ar continuam indo para o banner. O mesmo marcador passa a ser usado no diálogo de categoria (F-05), que hoje mostra o 409 duas vezes.

### 3.5 Backend — `lancamento_service.criar` (T-015)

1. Valida a entrada (schema): `valor` como `Dinheiro` (> 0, 2 casas, até 12 dígitos — RN-01); `descricao` aparada, 1–100; `observacao` aparada, ≤ 500, vazia → `null` (RN-06); `data` ISO obrigatória (RN-02); `tipo` e `forma_pagamento` do enum.
2. Regras que dependem de outros dados:
   - `categoria_id` inexistente → 422 `VALIDACAO` no campo `categoria_id`: "Categoria não encontrada." (o recurso do POST é o lançamento, por isso não é 404);
   - categoria **inativa** → 409 `CATEGORIA_INATIVA`: `A categoria "Mercado" está desativada. Escolha uma categoria ativa.` (RN-04);
   - categoria de **outro tipo** → 409 `CATEGORIA_TIPO_INCOMPATIVEL`: `A categoria "Salário" é de receita e não pode ser usada num gasto.` (RN-04);
   - **gasto sem forma** de pagamento → 422 `VALIDACAO` no campo `forma_pagamento`: "Informe a forma de pagamento." (RN-05); receita sem forma é válida (CA-02.2); receita **com** forma é gravada normalmente.
3. Monta o `Lancamento`: `id = uuid4().hex`, `criado_em = atualizado_em = agora()` (hora local, F-03), campos de parcela e recorrência vazios.
4. Grava **uma** linha (`inserir([lancamento])`, `RAW` + `INSERT_ROWS`).
5. Responde `201` com o `Lancamento` de `03` §6.3, incluindo `categoria_nome` e `categoria_cor` lidos da categoria.
6. O mês de referência é o da `data` (RN-03) — nada extra é gravado.

### 3.6 Formas de pagamento

`GET /api/formas-pagamento` devolve as 6 de RN-05, na ordem da regra: Pix, Cartão de crédito, Cartão de débito, Dinheiro, Boleto, Transferência — rótulos de `backend/app/domain/enums.py` (F-04 §10: única fonte). O frontend busca **uma vez** (`FormasPagamentoStore`).

---

## 4. Critérios de aceite

**Herdados de `01`**

- [ ] **CA-01.1** Dado qualquer tela aberta, quando o usuário aciona "Registrar gasto", então um formulário abre com a data de hoje já preenchida.
- [ ] **CA-01.2** Dado um formulário válido, quando o usuário confirma, então o gasto é gravado na planilha, o formulário fecha e uma confirmação é exibida.
- [ ] **CA-01.3** Dado um campo obrigatório vazio ou valor ≤ 0, quando o usuário tenta confirmar, então o sistema indica o campo inválido e não grava nada.
- [ ] **CA-01.4** Dado que a gravação falhou, quando o erro é exibido, então os dados digitados continuam no formulário para nova tentativa.
- [ ] **CA-01.5** Dado um gasto recém-registrado, quando o usuário vê a listagem e o resumo do mês, então o gasto já aparece e os totais já o consideram. *(F-06 garante `DadosStore.versao++`; a verificação na tela é de F-07/F-09.)*
- [ ] **CA-02.1** Dado o formulário de receita, quando o usuário escolhe a categoria, então só categorias ativas do tipo receita são oferecidas.
- [~] **CA-02.2** Dado um formulário de receita válido sem forma de pagamento, quando o usuário confirma, então a receita é gravada. *(T-015: API grava receita sem forma; o formulário é T-016.)*

**Refinados — backend (T-015)**

- [x] **CA-F06.1** Dado um gasto válido, quando `POST /api/lancamentos`, então 201, **uma** linha nova na aba `Lancamentos` com `id` uuid hex, data ISO em texto, valor numérico, enums em maiúsculas, `criado_em = atualizado_em`, parcela/recorrência vazias; e a resposta traz `categoria_nome` e `categoria_cor`.
- [x] **CA-F06.2** Dado `valor` 0, negativo, com 3 casas ou acima de 12 dígitos, então 422 no campo `valor` e nada é gravado (RN-01).
- [x] **CA-F06.3** Dado `data` ausente ou inválida (`2026-02-30`, `30/09/2026`), então 422 no campo `data`; e datas passadas e futuras (`1999-01-01`, `2030-12-31`) são aceitas (RN-02).
- [x] **CA-F06.4** Dado categoria inativa, então 409 `CATEGORIA_INATIVA`; de outro tipo, 409 `CATEGORIA_TIPO_INCOMPATIVEL`; inexistente, 422 no campo `categoria_id` — em todos, nada gravado (RN-04).
- [x] **CA-F06.5** Dado gasto sem `forma_pagamento`, então 422 no campo `forma_pagamento`; e receita sem forma, 201 com `forma_pagamento: null` (RN-05, CA-02.2).
- [x] **CA-F06.6** Dado descrição vazia, só espaços ou com 101 caracteres (após aparar), ou observação com 501, então 422 no campo; e observação `""` é gravada vazia e devolvida `null` (RN-06).
- [x] **CA-F06.7** Dado `GET /api/formas-pagamento`, então 200 com os 6 `{codigo, nome}` na ordem de RN-05.
- [x] **CA-F06.8** Dado a planilha inacessível, quando `POST /api/lancamentos`, então 503 com o código da causa e nada gravado.

**Refinados — frontend (T-016)**

- [ ] **CA-F06.9** Dado "Registrar receita", quando o diálogo abre, então o título é "Registrar receita", a data é hoje, o seletor mostra só categorias **ativas de receita** (com a cor) e a forma de pagamento tem "Não informar".
- [ ] **CA-F06.10** Dado o formulário com valor, descrição, categoria ou (em gasto) forma vazios, quando "Salvar", então esses campos mostram a mensagem de §3.2 e **nenhuma** requisição sai (CA-01.3).
- [ ] **CA-F06.11** Dado um gasto válido, quando "Salvar", então sai `POST` com o corpo de `03` §6.3 (valor como número, data `YYYY-MM-DD`), o botão mostra "Salvando…", e no 201 o diálogo fecha, aparece "Gasto registrado." e `DadosStore.versao` aumenta 1 (CA-01.2, CA-01.5).
- [ ] **CA-F06.12** Dado um 422 com `detalhes`, um 409 de categoria, um 503 ou o backend fora do ar, então o diálogo continua aberto com **todos** os valores digitados e a mensagem aparece no lugar certo (campo, ou banner) (CA-01.4, RNF-06); no 409 de categoria, a lista de categorias é recarregada.
- [ ] **CA-F06.13** Dado nenhuma categoria ativa do tipo, então aparece a orientação de §3.2 com link para Categorias e "Salvar" fica desabilitado (F-05 Q5).
- [ ] **CA-F06.14** Dado o texto digitado no valor, então a interpretação segue §3.2.1: `42,5` → 42.50, `1.234,56` → 1234.56, `1.234` → 1234, `42.50` → 42.50, `R$ 10` → 10; `0,001` → "Use no máximo 2 casas decimais."; `abc` e `1,2,3` → "Valor inválido. Ex.: 1.234,56"; e ao sair do campo `1234.5` aparece como `1.234,50` (Q2).
- [ ] **CA-F06.16** Dado um 409 numa chamada com `TRATAMENTO_LOCAL` (diálogo de lançamento ou de categoria), então a mensagem aparece só no campo, sem aviso do interceptor; e sem o marcador, o 409 continua gerando aviso (Q3).
- [ ] **CA-F06.15** Dado o app recém-aberto, quando o pacote inicial é medido no build, então o código do diálogo **não** está nele (carga sob demanda).

---

## 5. Casos de borda

| # | Caso | Comportamento esperado | Regra |
|---|---|---|---|
| 1 | Valor `0,00` | Inválido: "Informe um valor maior que zero." | RN-01 |
| 2 | Valor `0,001` | Inválido: "Use no máximo 2 casas decimais." (cliente e 422 no backend) | RN-01 |
| 3 | Valor `9.999.999.999,99` / `10.000.000.000,00` | Aceito / 422 (acima de 12 dígitos). | RN-01 |
| 4 | Data `31/12/2030` e `01/01/1999` | Aceitas. | RN-02 |
| 5 | Data `29/02/2025` digitada | Inválida no cliente ("Informe uma data válida."). | RN-02 |
| 6 | Gasto em 31/10 às 23:59, salvo às 00:01 de 01/11 | Grava a data **escolhida** (31/10); o mês de referência é outubro. | RN-03 |
| 7 | Categoria desativada em outra aba entre abrir e salvar | 409 `CATEGORIA_INATIVA` no campo; lista recarregada sem ela. | RN-04 |
| 8 | Receita com forma de pagamento `PIX` | Gravada com a forma. | RN-05 |
| 9 | Descrição `"  Almoço  "` | Gravada `Almoço`. | RN-06 |
| 10 | Descrição `=SOMA(A1:A9)` | Gravada como texto (RAW, ADR-04). | RN-06 |
| 11 | Duplo clique em "Salvar" | Uma só requisição. | CA-01.2 |
| 12 | Backend desligado ao salvar | Banner de F-04; diálogo aberto com os dados. | RNF-06 |
| 13 | Esc / clique fora com dados digitados | Fecha sem salvar (sem pergunta de confirmação). | — |
| 13a | Valor `1.234` | 1234,00 (pontos de 3 em 3 = milhar). | Q2 |
| 13b | Valor `1.5` / `42.50` | 1,50 / 42,50 (ponto único com 1–2 dígitos = decimal). | Q2 |
| 14 | Nenhuma categoria de receita ativa | Orientação + link; "Salvar" desabilitado. | F-05 Q5 |
| 15 | 5.000 lançamentos na planilha | Registrar leva < 3 s: uma leitura de categorias (cache) e **uma** escrita. | RNF-04 |
| 16 | Diálogo aberto em janela de 360 px | Campos em coluna única, sem rolagem horizontal; o diálogo ocupa a largura com margem de 16 px. | RNF-07 |

---

## 6. Contrato e dados

**API** (`03` §6.1, sem rota nova)

| Método | Caminho | Entrada | Saída |
|---|---|---|---|
| POST | `/api/lancamentos` | `LancamentoEntrada` | `201 Lancamento` · `409 CATEGORIA_INATIVA` · `409 CATEGORIA_TIPO_INCOMPATIVEL` · `422` · `503` |
| GET | `/api/formas-pagamento` | — | `200 [{codigo, nome}]` |

Esquemas (`03` §6.3, sem alteração):

```jsonc
// LancamentoEntrada
{ "data": "2026-09-29", "tipo": "GASTO", "descricao": "Almoço", "valor": 42.50,
  "categoria_id": "alimentacao", "forma_pagamento": "PIX", "observacao": null }

// Lancamento = LancamentoEntrada +
{ "id": "9f1c...", "categoria_nome": "Alimentação", "categoria_cor": "#E57373",
  "parcelamento_id": null, "parcela_numero": null, "parcela_total": null,
  "recorrencia_id": null, "criado_em": "...", "atualizado_em": "..." }

// Forma de pagamento
{ "codigo": "CREDITO", "nome": "Cartão de crédito" }
```

**Planilha** — aba `Lancamentos` (`03` §5.1): **uma** linha por registro, colunas A–N, pelo `LancamentoRepositoryPlanilha` de F-03. Leitura da aba `Categorias` (cache) para RN-04 e para o nome/cor da resposta. Nenhuma coluna nova.

**Erros** — 409 `CATEGORIA_INATIVA` e `CATEGORIA_TIPO_INCOMPATIVEL` já previstos em `03` §6.2; entram no mapa de `api/erros.py` e como exceções de domínio.

---

## 7. Interface

- **Onde:** diálogo aberto pelos botões do shell (qualquer rota).
- **Componentes:** `lancamento-form.dialog` (em `features/lancamentos/`, `03` §3), `LancamentosApi` e `FormasPagamentoApi` (`core/api/`), `FormasPagamentoStore` (`core/state/`), modelos `Lancamento`/`LancamentoEntrada`/`FormaPagamentoOpcao` (`core/models/`), utilitário de valor em pt-BR (`core/utils/`). Reusa `CategoriasStore.ativasPorTipo` (F-05), `Avisos` e `DadosStore` (F-04).
- **Estados:** preenchendo · salvando · erro (no campo ou banner) · sem categorias ativas.
- **Mensagens (pt-BR):** títulos "Registrar gasto"/"Registrar receita"; avisos "Gasto registrado."/"Receita registrada."; validações de §3.2; erros do backend de §3.5, sem reescrita; botão "Salvando…"; opção "Não informar".

---

## 8. Plano de testes

| Teste | Nível | Cobre |
|---|---|---|
| `tests/unit/test_lancamento_service.py::test_cria_gasto_valido__CA_01_2` | unitário BE | CA-01.2, CA-F06.1 |
| `…::test_categoria_inativa_ou_de_outro_tipo__RN_04` (parametrizado) | unitário BE | CA-F06.4, borda 7 |
| `…::test_categoria_inexistente_422__RN_04` | unitário BE | CA-F06.4 |
| `…::test_gasto_exige_forma_receita_nao__RN_05` | unitário BE | CA-F06.5, CA-02.2, borda 8 |
| `…::test_descricao_e_observacao_aparadas__RN_06` | unitário BE | CA-F06.6, bordas 9–10 |
| `tests/api/test_lancamentos.py::test_post_201_formato_e_linha_na_planilha__CA_F06_1` (composição real + planilha falsa) | API BE | CA-F06.1 |
| `…::test_valor_invalido_422__RN_01` (parametrizado) | API BE | CA-F06.2, bordas 1–3 |
| `…::test_data_422_e_datas_extremas__RN_02` | API BE | CA-F06.3, borda 4 |
| `…::test_409_de_categoria__RN_04` | API BE | CA-F06.4 |
| `…::test_descricao_observacao_422__RN_06` | API BE | CA-F06.6 |
| `…::test_planilha_inacessivel_503__CA_F06_8` | API BE | CA-F06.8 |
| `tests/api/test_formas_pagamento.py::test_seis_formas_na_ordem__CA_F06_7` | API BE | CA-F06.7 |
| `tests/api/test_app.py` (guarda de rotas com `POST /api/lancamentos` e `GET /api/formas-pagamento`) | API BE | `03` §6.1 |
| `frontend/…/core/utils/valor.spec.ts` › `interpreta_valor_ptBR__CA_F06_14` (parametrizado com todos os exemplos de §3.2.1) e `formata_ao_sair` | unitário FE | CA-F06.14, bordas 1–3, 13a, 13b |
| `…/core/interceptors/erro.interceptor.spec.ts` › `409_com_tratamento_local_sem_aviso__CA_F06_16` | unitário FE | CA-F06.16 |
| `…/features/categorias/categoria-form.dialog.spec.ts` › `duplicada_so_no_campo__CA_F06_16` | unitário FE | CA-F06.16 (correção em F-05) |
| `…/features/lancamentos/lancamento-form.dialog.spec.ts` › `abre_com_hoje_e_categorias_do_tipo__CA_01_1`, `receita_so_ativas_de_receita__CA_02_1` | unitário FE | CA-01.1, CA-02.1, CA-F06.9 |
| `…` › `invalido_nao_envia__CA_01_3` | unitário FE | CA-01.3, CA-F06.10, borda 5 |
| `…` › `salva_fecha_avisa_e_incrementa__CA_01_2` | unitário FE | CA-01.2, CA-01.5, CA-F06.11, borda 11 |
| `…` › `receita_sem_forma__CA_02_2` | unitário FE | CA-02.2 |
| `…` › `falha_mantem_os_dados__CA_01_4` (422, 409, 503, status 0) | unitário FE | CA-01.4, CA-F06.12, bordas 7, 12 |
| `…` › `sem_categoria_ativa__CA_F06_13` | unitário FE | CA-F06.13, borda 14 |
| `app.spec.ts` › `botoes_abrem_o_dialogo_do_tipo__CA_01_1` | unitário FE | CA-01.1 |
| `npm run build`: diálogo fora do pacote inicial | manual FE | CA-F06.15 |
| Diálogo em 360 px | manual FE | borda 16 |

---

## 9. Divisão em tarefas

| Tarefa | Escopo nesta feature | Arquivos principais |
|---|---|---|
| **T-015** (BE) | `lancamento_service.criar`, exceções `CategoriaInativa`/`CategoriaTipoIncompativel`, schemas `LancamentoEntrada`/`LancamentoSaida`/`FormaPagamentoSaida`, routers `lancamentos` (POST) e `formas_pagamento` (GET), `LancamentoServiceDep`, guarda de rotas. | `backend/app/services/lancamento_service.py`, `backend/app/domain/erros.py`, `backend/app/api/{schemas.py,deps.py,erros.py,routers/lancamentos.py,routers/formas_pagamento.py}`, `backend/app/main.py`, `backend/tests/unit/test_lancamento_service.py`, `backend/tests/api/{test_lancamentos.py,test_formas_pagamento.py,test_app.py}` |
| **T-016** (FE) | Modelos, `LancamentosApi.criar`, `FormasPagamentoApi` + store, utilitário de valor, `lancamento-form.dialog` (modo novo), botões do shell com import sob demanda; marcador `TRATAMENTO_LOCAL` no interceptor e no diálogo de categoria (Q3). | `frontend/src/app/core/{models/lancamento.ts,api/lancamentos.api.ts,api/formas-pagamento.api.ts,state/formas-pagamento.store.ts,utils/valor.ts}`, `frontend/src/app/features/lancamentos/lancamento-form.dialog.ts`, `frontend/src/app/app.{ts,html}`, `frontend/src/app/core/interceptors/erro.interceptor.ts`, `frontend/src/app/core/api/categorias.api.ts` + specs |

Ordem: T-015 → T-016 (`05` §4; T-016 também depende de T-014, concluída).

---

## 10. Decisões tomadas nesta feature

| Decisão | Motivo | Virou ADR? |
|---|---|---|
| Tipo fixo pelo botão que abriu o diálogo. | São duas ações distintas no shell (REQ-01, REQ-02); trocar o tipo no meio mudaria a lista de categorias e a obrigatoriedade da forma. | Não |
| `categoria_id` inexistente → 422 no campo, não 404. | O recurso do `POST` é o lançamento; a categoria é um dado de entrada inválido. | Não |
| Descrição e observação aparadas nas pontas; espaços internos preservados; observação vazia → `null`. | RN-06 conta caracteres; aparar evita "descrição" só de espaços. | Não |
| Diálogo carregado sob demanda pelo shell. | O shell está no pacote inicial (456 kB, aviso em 500 kB); formulário, datepicker e select ficam fora dele (sugestão de T-014). | Não |
| Esc / clique fora fecham sem confirmação. | Registrar é rápido; perguntar "descartar?" a cada fechamento atrapalharia mais do que ajuda. | Não |
| Só "Salvar", que fecha o diálogo (Q1). | Mais simples; "salvar e registrar outro" pode entrar no polimento (T-031) se fizer falta. | Não |
| Valor em campo livre pt-BR com as regras de §3.2.1 (Q2). | Digitar "42,50" é o natural no teclado; a regra do ponto (milhar de 3 em 3, decimal com 1–2 dígitos) cobre também quem digita "42.50". | Não |
| Marcador `TRATAMENTO_LOCAL` (`HttpContext`) para o interceptor não repetir um 409 que o formulário já mostra (Q3). | Evita a mesma frase no campo e no aviso; mantém o comportamento global para quem não trata o erro. `03` → 1.17 (§8.4). | Não |
| Forma de pagamento nunca pré-selecionada (Q4). | Evita gravar a forma errada sem perceber; RN-05 exige escolha consciente no gasto. | Não |
| Erro de domínio passa a carregar `detalhes`; `ErroValidacao.no_campo(campo, mensagem)` (T-015). | Categoria inexistente e gasto sem forma são regras do serviço, mas o formulário precisa do campo para marcá-lo (CA-F06.12). Cabe no formato de `03` §6.2; `03` → 1.18. | Não |
| Ordem das checagens da categoria: existe → mesmo tipo → ativa → forma (T-015). | Tipo errado é o erro mais fundamental; uma categoria inativa de outro tipo é reportada como "de outro tipo". | Não |
| `GET /api/formas-pagamento` não depende da planilha (T-015). | A lista é fixa (P-01) e vem do enum; o formulário pode mostrá-la mesmo com a planilha fora. | Não |
| `valor` na entrada usa o tipo `Dinheiro`: JSON `true` e texto como `"42,50"` são recusados (T-015). | A interpretação do formato pt-BR é do frontend (§3.2.1); a API recebe número. | Não |

---

## 11. Questões em aberto

**Respondidas em 2026-09-30 — nenhuma em aberto.** Em todas, o usuário escolheu a opção recomendada.

- [x] **Q1** → só "Salvar", que fecha o diálogo (§3.3.3).
- [x] **Q2** → campo livre em pt-BR, regras de §3.2.1, reformatado ao sair do campo.
- [x] **Q3** → marcador `TRATAMENTO_LOCAL`: sem aviso do interceptor em 409 nas chamadas dos diálogos de lançamento e de categoria (§3.4.5). `03` → 1.17.
- [x] **Q4** → forma de pagamento nunca pré-selecionada (§3.1.3).

---

## Revisões

| Data | Alteração |
|---|---|
| 2026-09-30 | Criação (`/especificar-feature F-06`). Status `Rascunho` — 4 questões em aberto. |
| 2026-09-30 | Q1–Q4 respondidas → status **Aprovada**. Regras do valor em §3.2.1; `TRATAMENTO_LOCAL` no escopo de T-016 (inclui o diálogo de categoria); CA-F06.14 detalhado e CA-F06.16 acrescentado; bordas 13a e 13b. `03` → 1.17. |
| 2026-09-30 | T-015 concluída: CA-F06.1 a .8 verificados por teste (API com planilha falsa e em memória); CA-02.2 com a parte do backend. Quatro decisões em §10. `03` → 1.18. |
