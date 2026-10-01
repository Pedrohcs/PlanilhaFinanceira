# F-14 — Polimento e resiliência

| Campo | Valor |
|---|---|
| Feature | F-14 |
| Marco | M4 |
| Status | Aprovada |
| Requisitos | REQ-16 (CA-16.2, CA-16.3) |
| Regras | RN-14; RNF-03, RNF-04, RNF-06, RNF-07 |
| Depende de | F-08, F-10, F-11, F-12, F-13 (todas **Concluída**) |
| Tarefas | T-031, T-032 |
| Atualizado em | 2026-10-01 |

> **IDs de critério:** herdados de `01` mantêm o ID original (**CA-16.3** …). Os refinados usam **`CA-F14.y`**.
>
> Marcas **(Qn)** apontam a decisão de §11 que fixou aquele trecho.

---

## 1. Objetivo

Deixar o aplicativo consistente e confiável no uso do dia a dia: toda tela com os mesmos estados (carregando, vazio, erro), utilizável em janela estreita, em português e acessível; e, quando a planilha é editada à mão, o usuário consegue recarregar os dados na hora e fica sabendo quando alguma linha foi ignorada por estar inválida.

---

## 2. Escopo

**Inclui**
- **T-031 (FE) — revisão de todas as telas:** `/resumo`, `/lancamentos`, `/historico`, `/categorias`, `/recorrencias`, o shell e os diálogos (lançamento, categoria, recorrência, confirmação): estados carregando/vazio/erro, responsividade ≥ 360 px (RNF-07), mensagens em pt-BR (RNF-03), acessibilidade básica (rótulos, foco no diálogo). Corrige o que a revisão encontrar.
- **T-031 — duas sugestões anotadas nas tarefas anteriores (Q5):** fontes servidas localmente e erro do servidor no campo que some ao interagir.
- **T-032 (BE+FE) — "Recarregar dados":** `POST /api/sistema/recarregar` (`03` §6.1, RN-14) e o botão na interface **(Q1)**.
- **T-032 — aviso de linhas ignoradas** (CA-16.3) nas telas que recebem `linhas_ignoradas` **(Q2, Q3)**.
- **T-032 — mensagens de validação do Pydantic em pt-BR** (hoje chegam em inglês em `detalhes`, ex.: "Input should be less than or equal to 31").
- **T-032 — desempenho com 5.000 lançamentos** (RNF-04): repositório em memória/planilha falsa (já há testes por tela) e um teste `@integracao` contra a planilha de teste **(Q6)**.

**Não inclui** (e onde será tratado)
- Scripts de inicialização e o roteiro E2E com todos os CA — **F-15** (T-033, T-035).
- Suíte de integração completa (bootstrap, CRUD, parcelamento, sincronização) — **F-15** (T-034). Aqui só o teste de desempenho.
- Mostrar **quais** linhas foram ignoradas — CA-16.3 pede **quantas**; o número da linha continua no log `WARNING` do backend (`03` §5.6).
- Mudanças de comportamento das features (regras, contratos de negócio) — fora de escopo; o que a revisão achar que exija isso vira sugestão no Log.
- Sugestões anotadas **não escolhidas** em Q5: README sobre a aba "Página1" (T-008) e `conftest` forçando a credencial falsa (T-009) — continuam como sugestões no Log de `05`.

---

## 3. Comportamento detalhado

### 3.1 Revisão das telas (T-031)

Para cada tela/diálogo, a revisão confere os itens abaixo e corrige o que faltar. O resultado (tabela tela × item, com "ok" ou o que foi corrigido) fica em §10 desta spec.

1. **Estados** (padrão de F-04/F-07):
   - **carregando** só na primeira carga (`app-carregando`); nas seguintes, o conteúdo anterior esmaecido;
   - **vazio** com mensagem própria da tela (`app-estado-vazio`) e, quando houver ação óbvia, o botão dela;
   - **erro** "Não foi possível carregar …" sem números velhos; a causa vai para o banner/aviso (interceptor);
   - resposta antiga descartada (troca rápida de mês/período/filtro).
2. **Responsividade (RNF-07):** em 360 px e em 1280 px, nenhuma rolagem horizontal da página; textos longos (descrição de 100 caracteres, nome de categoria de 40) quebram; diálogos cabem (`maxWidth: calc(100vw - 32px)`); botões da barra no formato curto abaixo de 600 px (F-04 Q1).
3. **pt-BR (RNF-03):** todo texto visível em português; moeda `R$ 1.234,56`, datas `dd/mm/aaaa`, meses por extenso; nenhum texto de biblioteca em inglês visível (paginador, datepicker, snackbar "Fechar", rótulos de leitor de tela do Material).
4. **Acessibilidade básica:**
   - todo campo com `mat-label`; botão só de ícone com `aria-label`;
   - diálogo abre com foco no primeiro campo (ou em "Cancelar" na confirmação) e, ao fechar, o foco volta ao botão que o abriu;
   - estado e tipo não só por cor (selos com texto, valor com sinal);
   - gráficos com `role="img"` e `aria-label` (F-10/F-11);
   - títulos de página (`h1`) e de seção (`h2`) em ordem.
5. **RNF-06:** nos três formulários (lançamento, categoria, recorrência), erro de API mantém o diálogo aberto com tudo o que foi digitado (já é assim; a revisão confere com 503 e backend fora).
6. **Pacote inicial** abaixo do orçamento de 500 kB (`angular.json`); a revisão registra o tamanho final.

### 3.2 Sugestões anotadas (T-031, **Q5**)

1. **Fontes locais:** Roboto e Material Symbols servidas pelo próprio app (pacotes npm `@fontsource/roboto` e `material-symbols`, com **ADR** em `02` §9 e entrada em `02` §1), sem `fonts.googleapis.com` no `index.html`. Sem internet, os ícones deixam de aparecer como texto ("more_vert") e o app continua legível (RNF-01, REQ-16 "sem internet").
2. **Erro do servidor no campo** (sugestão de T-030): some na primeira interação com o campo (abrir o select, digitar ou escolher o mesmo valor), nos três diálogos.

### 3.3 "Recarregar dados" (T-032, RN-14)

1. **Backend:** `POST /api/sistema/recarregar` → `cache.invalidar_tudo()` → `204`, **sem** chamada ao Google (só esvazia o cache; a próxima leitura de cada aba vai à planilha). Responde 204 mesmo com a planilha inacessível (não há o que falhar).
2. **Frontend (Q1):** botão de ícone `refresh` na **barra superior**, em todas as telas e larguras, `aria-label` e dica "Recarregar dados da planilha".
   - Ao clicar: desabilita durante o pedido; no 204, `DadosStore.versao++` (as telas e o `CategoriasStore` recarregam) e aviso "Dados recarregados da planilha.".
   - Backend fora do ar → banner (interceptor), sem aviso de sucesso.
   - Se o banner de conexão estiver aberto, o botão continua disponível (o banner tem o próprio "Tentar novamente").
3. Editar a planilha à mão e clicar em "Recarregar dados" mostra a mudança na hora (sem esperar o TTL de 30 s do cache).

### 3.4 Aviso de linhas ignoradas (T-032, CA-16.3)

1. **Onde (Q2, Q3):** nas telas que recebem `linhas_ignoradas` da API — **lançamentos** (`ListaLancamentos`), **resumo** (`ResumoMensal`) e **histórico** (`ResumoHistorico`) — sempre que o número for > 0.
2. **Como:** uma faixa discreta (componente compartilhado `shared/components/aviso-linhas-ignoradas`), abaixo do cabeçalho da página, com ícone de alerta e o texto:
   - "1 linha da planilha foi ignorada por estar inválida." / "3 linhas da planilha foram ignoradas por estarem inválidas.";
   - mais "Corrija-a na planilha e use **Recarregar dados**." (plural: "Corrija-as…").
   - `role="status"` (lido sem roubar o foco). Some quando o número volta a 0 (recarga).
3. O número vem pronto da API; o frontend não conta nada.
4. Linhas inválidas das abas `Categorias` e `Recorrencias` continuam só no log `WARNING` (contrato de `GET /api/categorias` e `GET /api/recorrencias` sem mudança) **(Q3)**.

### 3.5 Mensagens de validação em pt-BR (T-032)

1. O handler de `RequestValidationError` (`api/erros.py`) traduz os tipos de erro do Pydantic que a API pode gerar para mensagens curtas em pt-BR, por tipo (`type` do erro), mantendo o campo:

   | Tipo do Pydantic | Mensagem |
   |---|---|
   | `missing` | "Campo obrigatório." |
   | `greater_than` / `greater_than_equal` | "Deve ser maior que {gt}." / "Deve ser no mínimo {ge}." |
   | `less_than_equal` | "Deve ser no máximo {le}." |
   | `string_too_short` / `string_too_long` | "Texto obrigatório." / "Use no máximo {max_length} caracteres." |
   | `string_pattern_mismatch` | "Formato inválido." |
   | `decimal_max_places` | "Use no máximo 2 casas decimais." |
   | `int_parsing`, `decimal_parsing`, `float_parsing`, `int_type`, … | "Número inválido." |
   | `date_parsing`, `date_from_datetime_parsing`, `date_type` | "Data inválida." |
   | `enum`, `literal_error` | "Valor não permitido." |
   | outro | "Valor inválido." |
2. A mensagem geral continua "Dados inválidos.". Mensagens que o domínio já escreve em pt-BR (`ErroValidacao.no_campo`) não mudam.

### 3.6 Desempenho (T-032, RNF-04)

1. **Planilha falsa (sempre):** já existem testes de 5.000 linhas com uma leitura por aba e < 3 s para listagem, resumo e histórico (F-07, F-09, F-11). T-032 acrescenta o **registro** de um lançamento com 5.000 linhas na aba (uma leitura de `Categorias`, uma escrita, < 3 s).
2. **Planilha de teste (`@integracao`, manual — Q6):** `tests/integracao/test_desempenho.py` grava 5.000 lançamentos numa única chamada na planilha de `SPREADSHEET_ID_TESTE`, mede `GET /api/resumo/mensal`, `GET /api/resumo/historico` (12 meses) e `POST /api/lancamentos` (cada um < 3 s, cache frio) e **remove** as linhas criadas ao final, mesmo se o teste falhar. Pulado sem a variável (`02` §8).

---

## 4. Critérios de aceite

**Herdados de `01`**

- [ ] **CA-16.2** Dado uma falha temporária, então o usuário pode tentar novamente sem reiniciar o aplicativo. *(F-04 já cobre o "Tentar novamente"; F-14 acrescenta "Recarregar dados" para edições manuais e confere RNF-06 nos formulários.)*
- [ ] **CA-16.3** Dado uma linha editada manualmente na planilha com dado inválido, então o sistema continua funcionando, ignora a linha nos cálculos e informa quantas linhas foram ignoradas.

**Refinados — revisão (T-031)**

- [ ] **CA-F14.1** Dado cada uma das 5 páginas, então há estado de carregando (1ª carga), vazio (mensagem própria), erro ("Não foi possível carregar …", sem dado velho) e recarga esmaecida; e resposta antiga é descartada.
- [ ] **CA-F14.2** Dado a janela de 360 px e a de 1280 px, nos temas claro e escuro, então nenhuma página nem diálogo tem rolagem horizontal, e textos longos quebram (conferência visual — Q4).
- [ ] **CA-F14.3** Dado qualquer tela, então nenhum texto visível está em inglês e moeda, datas e meses seguem RNF-03.
- [ ] **CA-F14.4** Dado qualquer diálogo, então ele abre com o foco no primeiro campo (confirmação: em "Cancelar"), fecha com Esc e devolve o foco ao botão que o abriu; todo campo tem rótulo e todo botão só de ícone tem `aria-label`.
- [ ] **CA-F14.5** Dado um 503 ou o backend fora do ar ao salvar em qualquer dos três formulários, então o diálogo continua aberto com o que foi digitado (RNF-06).
- [ ] **CA-F14.6** Dado o build, então o pacote inicial fica abaixo de 500 kB e o tamanho é registrado.
- [ ] **CA-F14.7** (Q5) Dado o app aberto sem internet, então os ícones e a fonte aparecem (servidos localmente), e o `index.html` não referencia `fonts.googleapis.com`.
- [ ] **CA-F14.8** (Q5) Dado um erro do servidor marcado num campo, quando o usuário interage com esse campo (inclusive escolhendo o mesmo valor), então a mensagem do servidor some e o formulário pode ser enviado de novo.
- **CA-F14.9** *(removido — a sugestão do `conftest` não entrou em Q5).*

**Refinados — recarregar, linhas ignoradas, pt-BR, desempenho (T-032)**

- [ ] **CA-F14.10** Dado `POST /api/sistema/recarregar`, então `204`, o cache de todas as abas é invalidado e nenhuma chamada ao Google é feita; a leitura seguinte de cada aba vai à planilha (RN-14).
- [ ] **CA-F14.11** Dado a planilha inacessível, então `POST /api/sistema/recarregar` ainda responde 204.
- [ ] **CA-F14.12** Dado o botão "Recarregar dados" na barra (Q1), quando clicado, então ele fica desabilitado durante o pedido, e no 204 as telas recarregam (`versao++`) e aparece "Dados recarregados da planilha."; com o backend fora, o banner aparece e não há aviso de sucesso.
- [ ] **CA-F14.13** Dado `linhas_ignoradas` = 1 / 3 na resposta de lançamentos, resumo ou histórico, então a faixa mostra o texto no singular / plural de §3.4.2 com `role="status"`; dado 0, nenhuma faixa (CA-16.3).
- [ ] **CA-F14.14** Dado um corpo com `dia_do_mes` = 32, `valor` com 3 casas, `descricao` vazia, `mes_inicio` "julho" ou campo obrigatório faltando, então `detalhes[].mensagem` vem em pt-BR (§3.5).
- [ ] **CA-F14.15** Dado 5.000 lançamentos na planilha falsa, então registrar um lançamento faz uma leitura de `Categorias`, uma escrita e leva < 3 s (RNF-04).
- [ ] **CA-F14.16** (Q6) Dado `SPREADSHEET_ID_TESTE`, quando `pytest -m integracao` roda o teste de desempenho, então resumo, histórico e registro levam < 3 s cada com 5.000 lançamentos, e as linhas criadas são removidas ao final.

---

## 5. Casos de borda

| # | Caso | Comportamento esperado | Regra |
|---|---|---|---|
| 1 | Valor editado à mão para "abc" numa linha de setembro | A linha é ignorada nas somas; faixa "1 linha … foi ignorada" em lançamentos, resumo e histórico. | CA-16.3 |
| 2 | Usuário corrige a linha na planilha e clica em "Recarregar dados" | A faixa some e o valor entra nos totais, sem esperar 30 s. | RN-14 |
| 3 | Linha inválida em outro mês que não o exibido | O número conta do mesmo jeito (é a aba inteira que é lida). | CA-16.3 |
| 4 | Linha inválida em `Categorias` | Só no log; a lista de categorias não mostra aviso (Q3). | RN-14 |
| 5 | "Recarregar dados" com a planilha fora | 204; as telas recarregam e caem no erro de sempre (banner com a causa). | REQ-16 |
| 6 | Duplo clique em "Recarregar dados" | Um pedido só (botão desabilitado). | — |
| 7 | Descrição com 100 caracteres sem espaço em 360 px | Quebra dentro da célula/cartão; sem rolagem horizontal. | RNF-07 |
| 8 | Nome de categoria com 40 caracteres no select em 360 px | Cabe ou quebra; o painel não ultrapassa a tela. | RNF-07 |
| 9 | App aberto sem internet (backend local no ar, Google fora) | Banner com "Google Sheets indisponível…"; ícones e fonte visíveis (Q5). | REQ-16 |
| 10 | Esc no diálogo de lançamento com dados digitados | Fecha sem salvar (comportamento do Material, sem confirmação). | — |
| 11 | 422 do Pydantic num campo que o formulário não conhece | Aviso com a mensagem geral em pt-BR (os diálogos já tratam). | RNF-03 |
| 12 | Erro do servidor em "Categoria" e o usuário escolhe a mesma | A mensagem some e dá para salvar de novo (Q5). | RNF-06 |
| 13 | Teste de desempenho interrompido no meio | As linhas criadas são removidas no `finally` (Q6). | — |

---

## 6. Contrato e dados

**API** (`03` §6.1 — endpoint já previsto, implementado aqui)

| Método | Caminho | Entrada | Saída |
|---|---|---|---|
| POST | `/api/sistema/recarregar` | — | `204` (invalida o cache de todas as abas; sem chamada ao Google) |

Sem mudança nos demais contratos: `linhas_ignoradas` já vem em `ListaLancamentos`, `ResumoMensal` e `ResumoHistorico` (`03` §6.3). As mensagens de `detalhes` do 422 passam a ser em pt-BR (§3.5); `codigo` e `campo` não mudam.

**Planilha** — nenhuma aba ou coluna nova. O teste de desempenho (Q6) escreve e depois remove linhas da aba `Lancamentos` **da planilha de teste**, nunca da planilha real.

---

## 7. Interface

- **Shell:** botão `refresh` na barra superior (Q1), antes dos botões de registro; `aria-label` "Recarregar dados da planilha"; `matTooltip` não (evita módulo novo) — o `title` nativo serve de dica.
- **Componente novo:** `shared/components/aviso-linhas-ignoradas` (`input` `quantidade`), usado por lançamentos, resumo e histórico.
- **Estados:** como em §3.1 para todas as telas.
- **Mensagens (pt-BR):** "Recarregar dados da planilha"; "Dados recarregados da planilha."; "1 linha da planilha foi ignorada por estar inválida. Corrija-a na planilha e use Recarregar dados."; "<n> linhas da planilha foram ignoradas por estarem inválidas. Corrija-as na planilha e use Recarregar dados."; mensagens de §3.5.

---

## 8. Plano de testes

| Teste | Nível | Cobre |
|---|---|---|
| `frontend/…/features/*/*.page.spec.ts` › `estados_carregando_vazio_erro__CA_F14_1` (as que faltarem) | unitário FE | CA-F14.1 |
| `…/features/*/…dialog.spec.ts` › `foco_inicial_e_rotulos__CA_F14_4` (lançamento, categoria, recorrência) | unitário FE | CA-F14.4 |
| `…` › `503_mantem_dados__RNF_06` (os três formulários) | unitário FE | CA-F14.5, borda 11 |
| `…` › `erro_do_servidor_some_ao_interagir__CA_F14_8` | unitário FE | CA-F14.8, borda 12 |
| `frontend/src/index.html` sem `fonts.googleapis.com` (spec de configuração) + build | unitário FE + build | CA-F14.7 |
| `npm run build` (tamanho registrado) | build | CA-F14.6 |
| Conferência visual em 360 px e 1280 px, claro e escuro, nas 5 páginas e 4 diálogos (Q4) | manual | CA-F14.2, CA-F14.3, bordas 7–9 |
| `backend/tests/api/test_sistema.py::test_recarregar_204_invalida_cache__CA_F14_10` (planilha falsa: nova leitura depois) | API BE | CA-F14.10, borda 2 |
| `…::test_recarregar_sem_planilha_204__CA_F14_11` | API BE | CA-F14.11, borda 5 |
| `backend/tests/api/test_erros.py::test_mensagens_pydantic_em_ptbr__CA_F14_14` (parametrizado) | API BE | CA-F14.14 |
| `backend/tests/api/test_lancamentos.py::test_registrar_com_5000_linhas__RNF_04` | API BE | CA-F14.15 |
| `backend/tests/integracao/test_desempenho.py::test_desempenho_5000__RNF_04` (`@integracao`) | integração | CA-F14.16, borda 13 |
| `tests/api/test_app.py` (guarda de rotas) | API BE | `POST /api/sistema/recarregar` |
| `frontend/…/core/api/sistema.api.spec.ts` | unitário FE | §6 |
| `…/app.spec.ts` › `recarregar_dados__CA_F14_12` (desabilita, aviso, `versao++`, backend fora) | unitário FE | CA-F14.12, bordas 5–6 |
| `…/shared/components/aviso-linhas-ignoradas/…spec.ts` › `singular_plural_e_zero__CA_16_3` | unitário FE | CA-16.3, CA-F14.13 |
| `…/features/{lancamentos,resumo,historico}/*.page.spec.ts` › `mostra_linhas_ignoradas__CA_16_3` | unitário FE | CA-16.3, borda 1 |

---

## 9. Divisão em tarefas

| Tarefa | Escopo nesta feature | Arquivos principais |
|---|---|---|
| **T-031** (FE) | Revisão de §3.1 com correções e conferência visual com a planilha de teste (Q4); fontes locais com ADR e erro do servidor que some ao interagir (Q5); tabela do resultado em §10. | `frontend/src/index.html`, `frontend/src/styles.scss`, `frontend/package.json`, `frontend/src/app/features/**`, `frontend/src/app/shared/components/**`, `frontend/src/app/app.{ts,html}`, `SPECS/02-definicoes-tecnicas.md` (ADR) |
| **T-032** (BE+FE) | `POST /api/sistema/recarregar` + botão na barra; aviso de linhas ignoradas nas 3 telas; mensagens do Pydantic em pt-BR; testes de desempenho (planilha falsa + `@integracao`). | `backend/app/api/routers/sistema.py`, `backend/app/api/{deps.py,erros.py}`, `backend/app/main.py`, `backend/tests/api/{test_sistema.py,test_erros.py,test_lancamentos.py,test_app.py}`, `backend/tests/integracao/test_desempenho.py`, `frontend/src/app/core/api/sistema.api.ts`, `frontend/src/app/app.{ts,html}`, `frontend/src/app/shared/components/aviso-linhas-ignoradas/`, `frontend/src/app/features/{lancamentos,resumo,historico}/*` |

Ordem: T-031 → T-032 (`04`/`05`: T-032 depende de T-031).

---

## 10. Decisões tomadas nesta feature

| Decisão | Motivo | Virou ADR? |
|---|---|---|
| "Recarregar dados" só invalida o cache; não reconecta nem chama o Google. | RN-14 pede refletir edições manuais; reconectar é o "Tentar novamente" do banner (F-04). | Não |
| Aviso de linhas ignoradas como faixa com `role="status"`, não snackbar. | Fica visível enquanto o problema existe e é lido sem roubar o foco; some sozinho na recarga. | Não |
| Mensagens do Pydantic traduzidas por tipo de erro no handler, sem biblioteca de i18n. | São poucos tipos possíveis na API; nenhuma dependência nova. | Não |
| Teste de desempenho real só como `@integracao` (manual), contra a planilha de teste, com limpeza no `finally`. | Nunca toca a planilha real; `pytest` comum continua sem rede (`02` §8). | Não |
| "Recarregar dados" na barra superior, em todas as telas (Q1). | Edições manuais podem afetar qualquer tela; um lugar só, sempre à vista. | Não |
| Faixa nas telas de lançamentos, resumo e histórico (Q2); Categorias e Recorrências só no log (Q3). | Os contratos das listas de categorias e recorrências não mudam; as três telas com totais são as que podem mostrar número errado. | Não |
| Conferência visual conduzida pelo Claude no navegador automatizado, com o backend apontando para a planilha de teste (Q4). | Dá para criar dados de exemplo sem tocar a planilha real; o resultado fica registrado em §10. | Não |
| Entram só as sugestões de fontes locais e do erro do servidor no campo (Q5). | Escolha do usuário; README e `conftest` seguem como sugestões. | Fontes: sim (T-031) |
| Teste de desempenho real `@integracao` na planilha de teste, com limpeza (Q6). | Mede RNF-04 de verdade sem rodar no `pytest` comum. | Não |
| Resultado da revisão de T-031 registrado aqui (tela × item). | Deixa claro o que foi conferido e o que foi corrigido, para o roteiro E2E de F-15. | Não |

---

## 11. Questões em aberto

**Respondidas em 2026-10-01 — nenhuma em aberto.**

- [x] **Q1** → botão ↻ "Recarregar dados" na **barra superior**, em todas as telas (§3.3.2).
- [x] **Q2** → **faixa** no topo de lançamentos, resumo e histórico enquanto houver linhas ignoradas (§3.4).
- [x] **Q3** → linhas inválidas de Categorias e Recorrências **só no log**; contratos sem mudança (§3.4.4).
- [x] **Q4** → conferência visual **conduzida pelo Claude** no navegador automatizado, com o backend na **planilha de teste** (§3.1.2, CA-F14.2).
- [x] **Q5** → entram **fontes locais** (com ADR) e **erro do servidor que some ao interagir**; README da aba "Página1" e `conftest` **não** entram (§3.2; CA-F14.9 removido).
- [x] **Q6** → **sim**: teste `@integracao` com 5.000 linhas na planilha de teste, com limpeza (§3.6.2).

---

## Revisões

| Data | Alteração |
|---|---|
| 2026-10-01 | Criação (`/especificar-feature F-14`). Status `Rascunho` — 6 questões em aberto. |
| 2026-10-01 | Q1–Q6 respondidas → status **Aprovada**. Q1–Q4 e Q6 na opção recomendada; Q5 só com fontes locais e erro do servidor (CA-F14.9 removido; T-031 continua só FE). Cinco decisões em §10. |
