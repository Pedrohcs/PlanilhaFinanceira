# F-08 — Editar e excluir lançamentos

| Campo | Valor |
|---|---|
| Feature | F-08 |
| Marco | M1 |
| Status | Concluída |
| Requisitos | REQ-05 (CA-05.1 a CA-05.3), REQ-06 (CA-06.1, CA-06.2) |
| Regras | RN-01..06 (mesmas do registro), RN-03, RN-08, RN-10, RN-14 |
| Depende de | F-07 (**Concluída**) |
| Tarefas | T-019, T-020 |
| Atualizado em | 2026-09-30 |

> **IDs de critério:** herdados de `01` mantêm o ID original (**CA-05.1** …). Os refinados usam **`CA-F08.y`**.

---

## 1. Objetivo

Corrigir ou remover um lançamento direto da listagem, com a certeza de que só aquela linha da planilha muda — mesmo que o usuário tenha reordenado ou editado a planilha à mão.

---

## 2. Escopo

**Inclui**
- `lancamento_service.editar(id, entrada)` e `excluir(id)`; `PUT /api/lancamentos/{id}` → `200 Lancamento` e `DELETE /api/lancamentos/{id}` → `204` (`03` §6.1), `404 NAO_ENCONTRADO` para `id` inexistente.
- Na listagem (F-07): ações **Editar** e **Excluir** em cada lançamento.
- `lancamento-form.dialog` (F-06) ganha o **modo edição**, pré-preenchido.
- `LancamentosApi.atualizar` e `excluir`.

**Não inclui** (e onde será tratado)
- Excluir o parcelamento inteiro e a opção "Compra parcelada" — **F-12**. Aqui, editar ou excluir uma parcela afeta **só aquela parcela** (RN-08).
- Editar a regra de uma recorrência — **F-13**. Aqui, um lançamento gerado por recorrência se edita e exclui como qualquer outro (RN-10) e **não reaparece** depois de excluído.
- Desfazer uma exclusão — fora de escopo.

---

## 3. Comportamento detalhado

### 3.1 Backend — `editar` (T-019)

1. Entrada: o mesmo `LancamentoEntrada` do registro (`03` §6.3), com as mesmas validações de schema (RN-01, RN-02, RN-06) e de serviço (F-06 §3.5).
2. `id` inexistente (inclusive apagado à mão na planilha) → 404 `NAO_ENCONTRADO`: "Lançamento não encontrado." — verificado **antes** das regras de categoria.
3. **Qualquer campo** pode mudar (REQ-05), **inclusive o tipo** (gasto ↔ receita): a categoria tem de ser do tipo novo e, se for gasto, a forma de pagamento é obrigatória (RN-04, RN-05).
4. **Categoria inativa (Q1):** manter a **mesma** categoria do lançamento é permitido mesmo que ela esteja inativa — RN-04 exige categoria ativa "para novos lançamentos", e este já existia. **Trocar** para outra categoria exige que a nova esteja ativa (senão 409 `CATEGORIA_INATIVA`). Categoria de outro tipo continua recusada (409 `CATEGORIA_TIPO_INCOMPATIVEL`) — inclusive a atual, se o tipo mudou — e inexistente, 422 no campo.
5. Campos **preservados**, que o `PUT` não altera: `id`, `parcelamento_id`, `parcela_numero`, `parcela_total`, `recorrencia_id`, `criado_em`. `atualizado_em = agora()` (hora local, F-03).
6. Grava pelo `atualizar` do repositório de F-03: relê a aba, **localiza pelo `id`** e reescreve só as colunas A–N daquela linha (CA-05.2, CA-F03.19).
7. Resposta: `200 Lancamento` com `categoria_nome`/`categoria_cor` atuais.
8. Mudou a data para outro mês → passa a contar no mês novo (RN-03, CA-05.3) — nada extra: o mês é derivado da data.

### 3.2 Backend — `excluir` (T-019)

1. `id` inexistente → 404 `NAO_ENCONTRADO`, nada muda.
2. Remove **só** a linha daquele `id` (`remover([id])`, F-03: tudo ou nada, de baixo para cima) → `204`.
3. Parcela: remove só aquela parcela; as outras continuam, com seu "k/N" original (RN-08).
4. Lançamento de recorrência: remove; a marca d'água `ultimo_mes_gerado` da recorrência não muda, então ele **não é gerado de novo** (RN-10).

### 3.3 Listagem — ações (T-020)

1. Cada lançamento (tabela e cartões de F-07) ganha as ações **Editar** e **Excluir** num **menu ⋮** (Q2): última coluna da tabela ("Ações", sem título visível) e canto superior direito do cartão. O botão ⋮ tem `aria-label` "Ações de <descrição>" — o mesmo padrão da página de categorias.
2. **Editar** abre o diálogo de F-06 em modo edição (§3.4).
3. **Excluir** pede confirmação (`confirmacao-dialog`, F-04) mostrando **descrição, valor e data** (CA-06.1):
   - título "Excluir lançamento?";
   - mensagem: `"Almoço" — − R$ 42,50 em 30/09/2026 será excluído.`;
   - parcela: acrescenta "Só esta parcela (3/10) será excluída; as demais continuam.";
   - recorrente: acrescenta "A recorrência não gera este lançamento de novo.";
   - botão "Excluir".
   Confirmado → `DELETE`; sucesso → aviso "Lançamento excluído." e `DadosStore.incrementar()` — a lista e os totais se recalculam (CA-06.2).
4. **404** (o lançamento sumiu da planilha no meio tempo) ao editar ou excluir: o interceptor mostra "Lançamento não encontrado."; o diálogo de edição fecha; a lista recarrega (`versao++`).

### 3.4 Diálogo em modo edição (T-020)

1. Título "Editar gasto" / "Editar receita".
2. Campos pré-preenchidos com os dados atuais (CA-05.1): data, valor formatado (`42,50`), descrição, categoria, forma, observação.
3. **Tipo editável** (REQ-05: "qualquer campo"): no modo edição aparece o campo **Tipo** (Gasto/Receita). Trocar o tipo: a lista de categorias passa a ser a do tipo novo e a categoria escolhida é limpa se for de outro tipo; a forma de pagamento segue RN-05 (obrigatória no gasto, "Não informar" na receita).
4. Lista de categorias: ativas do tipo + **a categoria atual do lançamento**, se estiver inativa e for do tipo escolhido, marcada "(inativa)" (Q1). Trocar o tipo tira a categoria atual da lista se ela for de outro tipo.
5. Parcela e recorrência: o diálogo mostra, sem editar, "Parcela 3/10" ou "Gerado por recorrência".
6. Salvar → `PUT` com `TRATAMENTO_LOCAL` (F-06 Q3); erros como no registro (F-06 §3.4): o diálogo fica aberto com os dados.
7. Sucesso → diálogo fecha, aviso e `DadosStore.incrementar()`. **Aviso (Q3):** se a data nova é de outro mês que a antiga, "Lançamento atualizado. Agora ele está em outubro de 2026." (mês por extenso); senão, "Lançamento atualizado.".

---

## 4. Critérios de aceite

**Herdados de `01`**

- [x] **CA-05.1** Dado um lançamento na listagem, quando o usuário escolhe editar, então o formulário abre com os dados atuais.
- [x] **CA-05.2** Dado uma edição válida confirmada, então a linha correspondente na planilha é atualizada (e nenhuma outra).
- [x] **CA-05.3** Dado que a data foi alterada para outro mês, então o lançamento passa a contar no novo mês.
- [x] **CA-06.1** Dado um lançamento, quando o usuário escolhe excluir, então o sistema pede confirmação mostrando descrição e valor.
- [x] **CA-06.2** Dado a confirmação, então a linha é removida da planilha e os totais são recalculados. *(T-019: remoção da linha certa e totais recalculados na API; T-020: a tela recarrega lista e totais.)*

**Refinados — backend (T-019)**

- [x] **CA-F08.1** Dado um lançamento, quando `PUT` com todos os campos mudados (inclusive o tipo, com categoria e forma coerentes), então 200 com os valores novos; `id`, `criado_em`, parcela e recorrência preservados; `atualizado_em` novo.
- [x] **CA-F08.2** Dado que o usuário **reordenou** as linhas da planilha depois da última leitura, quando edita um lançamento, então só a linha daquele `id` muda — todas as outras continuam idênticas (CA-05.2).
- [x] **CA-F08.3** Dado `id` inexistente, então `PUT` e `DELETE` respondem 404 `NAO_ENCONTRADO` ("Lançamento não encontrado.") e nada muda.
- [x] **CA-F08.4** Dado edição inválida (valor 0, gasto sem forma, categoria de outro tipo, categoria inexistente), então 422/409 como no registro e a linha não muda.
- [x] **CA-F08.5** Dado um lançamento cuja categoria ficou inativa, quando editado mantendo a categoria, então 200; e quando a categoria é trocada por **outra** inativa, então 409 `CATEGORIA_INATIVA` (Q1).
- [x] **CA-F08.6** Dado a data mudada de 30/09 para 02/10, então a listagem de setembro não o traz mais e a de outubro traz, e os totais de ambos mudam (CA-05.3).
- [x] **CA-F08.7** Dado `DELETE` de um `id`, então só aquela linha some — inclusive após reordenação manual — e a listagem do mês recalcula os totais (CA-06.2).
- [x] **CA-F08.8** Dado a parcela 3/10 excluída, então as parcelas 1, 2 e 4..10 continuam, com "k/10" (RN-08).
- [x] **CA-F08.9** Dado a planilha inacessível, então `PUT`/`DELETE` → 503 com a causa e nada muda.

**Refinados — frontend (T-020)**

- [x] **CA-F08.10** Dado "Editar" num gasto, então o diálogo abre com título "Editar gasto" e todos os campos preenchidos (valor como `42,50`, data `dd/mm/aaaa`), e o campo Tipo presente (CA-05.1).
- [x] **CA-F08.11** Dado a troca de tipo para Receita no modo edição, então a lista de categorias passa a ser de receita, a categoria de gasto é limpa e a forma ganha "Não informar".
- [x] **CA-F08.12** Dado a edição salva, então sai `PUT /api/lancamentos/{id}` com o corpo completo, o diálogo fecha, aparece o aviso e `DadosStore.versao` aumenta; num erro 422/409, o diálogo fica aberto com os dados.
- [x] **CA-F08.13** Dado "Excluir", então a confirmação mostra descrição, valor com sinal e data (CA-06.1), e os textos extras de parcela ou recorrência quando for o caso; "Cancelar" não envia nada; "Excluir" envia o `DELETE`, avisa "Lançamento excluído." e a lista recarrega (CA-06.2).
- [x] **CA-F08.14** Dado um 404 ao editar ou excluir, então o diálogo de edição fecha e a lista recarrega (a mensagem vem do interceptor).
- [x] **CA-F08.15** Dado a categoria atual inativa, então o diálogo de edição a mostra selecionada e marcada "(inativa)" entre as ativas do tipo, e salvar sem trocá-la envia o `PUT` normalmente (Q1).
- [x] **CA-F08.16** Dado a janela de 360 px (cartões) e a de 1280 px (tabela), então cada lançamento tem o menu ⋮ com Editar e Excluir, com `aria-label` "Ações de <descrição>" (RNF-07, Q2).
- [x] **CA-F08.17** Dado a data editada de 30/09/2026 para 02/10/2026, então o aviso é "Lançamento atualizado. Agora ele está em outubro de 2026."; e sem mudança de mês, "Lançamento atualizado." (Q3).

---

## 5. Casos de borda

| # | Caso | Comportamento esperado | Regra |
|---|---|---|---|
| 1 | Linhas reordenadas à mão entre abrir a lista e salvar a edição | Só a linha do `id` muda. | CA-05.2 |
| 2 | Lançamento apagado à mão antes de salvar a edição | 404; diálogo fecha; lista recarrega. | RN-14 |
| 3 | `id` duplicado na planilha (editado à mão) | `atualizar` reescreve a **primeira** linha do `id`; `excluir` remove **todas** as linhas daquele `id` (F-03 §3.6). | RN-14 |
| 4 | Gasto editado para receita mantendo a categoria "Mercado" | 409 `CATEGORIA_TIPO_INCOMPATIVEL` (no cliente, a categoria já é limpa ao trocar o tipo). | RN-04 |
| 5 | Receita sem forma editada para gasto | Forma passa a ser obrigatória; sem ela, 422. | RN-05 |
| 6 | Data de 30/09 para 02/10 | Sai de setembro, entra em outubro; aviso "Agora ele está em outubro de 2026." | RN-03, Q3 |
| 14 | Categoria atual inativa; tipo trocado de gasto para receita | A categoria atual some da lista (é de gasto) e é limpa; é preciso escolher uma ativa de receita. | RN-04, Q1 |
| 7 | Parcela 3/10 editada (valor) | Só ela muda; continua "3/10". | RN-08 |
| 8 | Parcela 3/10 excluída | As outras 9 continuam com "k/10". | RN-08 |
| 9 | Lançamento de recorrência excluído | Não é gerado de novo (a marca d'água não muda). | RN-10 |
| 10 | Editar sem mudar nada e salvar | 200; só `atualizado_em` muda. | — |
| 11 | Duplo clique em "Excluir" da confirmação | Um só `DELETE` (o diálogo fecha no primeiro). | — |
| 12 | Planilha fora ao excluir | Banner de F-04; nada é removido; a lista continua. | RNF-06 |
| 13 | Descrição com `=SOMA(...)` editada | Continua texto (RAW). | ADR-04 |

---

## 6. Contrato e dados

**API** (`03` §6.1, sem alteração)

| Método | Caminho | Entrada | Saída |
|---|---|---|---|
| PUT | `/api/lancamentos/{id}` | `LancamentoEntrada` | `200 Lancamento` · `404` · `409` · `422` · `503` |
| DELETE | `/api/lancamentos/{id}` | — | `204` · `404` · `503` |

`LancamentoEntrada` e `Lancamento` como em F-06 §6. O `PUT` substitui os campos editáveis; parcela, recorrência, `id` e `criado_em` são preservados pelo backend.

**Planilha** — aba `Lancamentos`: `atualizar` reescreve A–N da linha do `id`; `remover` apaga a linha (um `batch_update`). Leitura de `Categorias` (cache) para RN-04 e nome/cor. Nenhuma coluna nova.

---

## 7. Interface

- **Onde:** página `/lancamentos` (F-07) e o diálogo de F-06.
- **Componentes:** `LancamentosPage` (ações), `lancamento-form.dialog` (modo edição), `abrir-lancamento.ts` (abre em modo edição e trata o resultado), `confirmacao-dialog` (F-04), `LancamentosApi.atualizar/excluir`.
- **Mensagens (pt-BR):** "Editar gasto"/"Editar receita"; "Excluir lançamento?"; `"<descrição>" — <valor> em <data> será excluído.`; "Só esta parcela (k/N) será excluída; as demais continuam."; "A recorrência não gera este lançamento de novo."; "Lançamento atualizado."; "Lançamento excluído."; "Lançamento não encontrado." (backend); "Parcela k/N"; "Gerado por recorrência".

---

## 8. Plano de testes

| Teste | Nível | Cobre |
|---|---|---|
| `tests/unit/test_lancamento_service.py::test_editar_todos_os_campos_preserva_os_demais__CA_05_1` | unitário BE | CA-F08.1, borda 10 |
| `…::test_editar_regras_de_categoria_e_forma__RN_04_RN_05` (parametrizado) | unitário BE | CA-F08.4, bordas 4–5 |
| `…::test_editar_categoria_inativa__Q1` | unitário BE | CA-F08.5 |
| `…::test_editar_e_excluir_inexistente_404__CA_F08_3` | unitário BE | CA-F08.3, borda 2 |
| `…::test_excluir_parcela_so_ela__RN_08` | unitário BE | CA-F08.8, borda 8 |
| `tests/api/test_lancamentos.py::test_put_so_a_linha_do_id_apos_reordenacao__CA_05_2` (planilha falsa) | API BE | CA-05.2, CA-F08.2, borda 1 |
| `…::test_put_muda_de_mes__CA_05_3` | API BE | CA-05.3, CA-F08.6, borda 6 |
| `…::test_delete_so_a_linha_e_totais__CA_06_2` (planilha falsa, com reordenação) | API BE | CA-06.2, CA-F08.7 |
| `…::test_put_delete_404__CA_F08_3` | API BE | CA-F08.3 |
| `…::test_put_validacoes__CA_F08_4` | API BE | CA-F08.4 |
| `…::test_put_delete_503__CA_F08_9` | API BE | CA-F08.9 |
| `…::test_descricao_com_igual_editada__ADR_04` | API BE | borda 13 |
| `frontend/…/core/api/lancamentos.api.spec.ts` › `atualizar_e_excluir` | unitário FE | §6 |
| `…/features/lancamentos/lancamento-form.dialog.spec.ts` › `edicao_pre_preenchida__CA_05_1` | unitário FE | CA-05.1, CA-F08.10 |
| `…` › `troca_de_tipo__CA_F08_11` | unitário FE | CA-F08.11, bordas 4–5 |
| `…` › `salva_edicao_com_put__CA_F08_12` e `erro_mantem_dados_na_edicao__CA_01_4` | unitário FE | CA-F08.12 |
| `…` › `volta_para_gasto_exige_forma__RN_05` | unitário FE | borda 5 |
| `…` › `recorrente_mostra_vinculo__F08` e `registro_nao_mostra_tipo_nem_vinculo` | unitário FE | §3.4 |
| `…` › `404_fecha_o_dialogo__CA_F08_14` | unitário FE | CA-F08.14, borda 2 |
| `…` › `categoria_inativa_na_edicao__CA_F08_15` | unitário FE | CA-F08.15 |
| `…/features/lancamentos/lancamentos.page.spec.ts` › `acoes_em_tabela_e_cartoes__CA_F08_16` | unitário FE | CA-F08.16 |
| `…` › `excluir_confirma_e_recarrega__CA_06_1` (inclui parcela e recorrência; cancelar) | unitário FE | CA-06.1, CA-06.2, CA-F08.13 |
| `…` › `404_ao_excluir_recarrega__CA_F08_14` | unitário FE | CA-F08.14 |
| `…` › `planilha_fora_ao_excluir_mantem_a_lista__borda_12` | unitário FE | borda 12 |
| `…` › `editar_abre_o_dialogo_pre_preenchido__CA_05_1` | unitário FE | CA-05.1 |
| `…/features/lancamentos/abrir-lancamento.spec.ts` › `edicao_avisa_e_incrementa__CA_F08_17` (com e sem mudança de mês) | unitário FE | CA-F08.12, CA-F08.17, borda 6 |

---

## 9. Divisão em tarefas

| Tarefa | Escopo nesta feature | Arquivos principais |
|---|---|---|
| **T-019** (BE) | `lancamento_service.editar/excluir`, routers `PUT`/`DELETE`, guarda de rotas. | `backend/app/services/lancamento_service.py`, `backend/app/api/routers/lancamentos.py`, `backend/tests/unit/test_lancamento_service.py`, `backend/tests/api/{test_lancamentos.py,test_app.py}` |
| **T-020** (FE) | `LancamentosApi.atualizar/excluir`; modo edição do diálogo (tipo editável, categoria inativa atual, parcela/recorrência informativas); ações na listagem; confirmação de exclusão. | `frontend/src/app/core/api/lancamentos.api.ts`, `frontend/src/app/features/lancamentos/{lancamento-form.dialog.ts,abrir-lancamento.ts,lancamentos.page.*}` + specs |

Ordem: T-019 → T-020 (T-020 também depende de T-018, concluída).

---

## 10. Decisões tomadas nesta feature

| Decisão | Motivo | Virou ADR? |
|---|---|---|
| Tipo editável (gasto ↔ receita), com categoria e forma revalidadas. | REQ-05: "qualquer campo". | Não |
| `PUT` preserva `id`, parcela, recorrência e `criado_em`; `atualizado_em` novo. | O vínculo de parcela só serve para "k/N" e excluir o parcelamento (RN-08); o de recorrência, para a marca d'água (RN-10). Não são campos de `LancamentoEntrada`. | Não |
| 404 verificado antes das regras de categoria. | Se o lançamento não existe, qualquer outro erro seria enganoso. | Não |
| Confirmação de exclusão com descrição, valor com sinal **e data**, e texto extra para parcela/recorrência. | CA-06.1 pede descrição e valor; a data desfaz a ambiguidade entre lançamentos parecidos; os extras antecipam dúvidas de RN-08/RN-10. | Não |
| 404 no diálogo de edição fecha o diálogo e recarrega a lista. | Não há o que salvar; manter aberto convidaria a tentar de novo em vão. | Não |
| Na edição, manter a categoria atual inativa é permitido; trocar exige ativa (Q1). | RN-04 restringe "novos lançamentos"; obrigar a trocar a categoria para corrigir, por exemplo, o valor seria reescrever o histórico. | Não |
| Ações no menu ⋮ (Q2). | Mesmo padrão da página de categorias; uma coluna estreita e alcançável em 360 px. | Não |
| Aviso diz o mês novo quando a edição muda o mês (Q3). | Explica por que o lançamento sumiu da lista aberta. | Não |
| O serviço troca a mensagem do `NaoEncontrado` do repositório ("Registro <id> não encontrado.") por "Lançamento não encontrado." (T-019). | O `id` não diz nada ao usuário; vale também quando a linha some entre a leitura e a escrita (borda 2). | Não |
| Validação de categoria e forma compartilhada entre criar e editar (`_validar`), com a exceção da categoria atual inativa só na edição (T-019). | Uma regra só para RN-04/RN-05; a exceção de Q1 fica explícita num parâmetro. | Não |
| A exclusão recarrega a lista no sucesso e no 404; com a planilha ou o backend fora, não recarrega (T-020). | Borda 12: "a lista continua" — recarregar trocaria a lista pela mensagem de erro de carga. | Não |
| `editarLancamento` fica em `abrir-lancamento.ts`, ao lado de `abrirLancamento`; a página (já carregada sob demanda) o importa direto, o shell continua com o import dinâmico (T-020). | Um só lugar abre o diálogo e decide aviso + recarga; o pacote inicial não muda (474 kB). | Não |

---

## 11. Questões em aberto

**Respondidas em 2026-09-30 — nenhuma em aberto.** Em todas, o usuário escolheu a opção recomendada.

- [x] **Q1** → manter a categoria atual inativa é permitido; trocar exige ativa (§3.1.4, §3.4.4).
- [x] **Q2** → ações no menu ⋮, na tabela e nos cartões (§3.3.1).
- [x] **Q3** → aviso com o mês novo quando a edição muda o mês (§3.4.7).

---

## Revisões

| Data | Alteração |
|---|---|
| 2026-09-30 | Criação (`/especificar-feature F-08`). Status `Rascunho` — 3 questões em aberto. |
| 2026-09-30 | Q1–Q3 respondidas → status **Aprovada**. CA-F08.5, .15 e .16 fechados; CA-F08.17 acrescentado; borda 14. |
| 2026-09-30 | T-019 concluída: CA-05.2, CA-05.3 e CA-F08.1 a .9 verificados por teste (inclui planilha reordenada à mão antes do `PUT` e do `DELETE`); CA-06.2 com a parte da API. Duas decisões em §10. |
| 2026-09-30 | T-020 concluída → feature **Concluída**. CA-05.1, CA-06.1, CA-06.2 e CA-F08.10 a .17 verificados por teste; plano de testes com os nomes finais e testes extras (bordas 5 e 12, vínculos). Duas decisões em §10. |
