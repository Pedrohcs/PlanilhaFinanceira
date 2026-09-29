# F-02 — Conexão com Google Sheets

| Campo | Valor |
|---|---|
| Feature | F-02 |
| Marco | M0 |
| Status | Concluída |
| Requisitos | REQ-16, RNF-05, RNF-06 (parcial) |
| Regras | — (nenhuma RN de negócio; as regras aqui são de infraestrutura: `02` §5.4, §5.5, §5.6) |
| Depende de | F-01 (**Concluída**) |
| Tarefas | T-004, T-005, T-006 |
| Atualizado em | 2026-09-29 |

> **IDs de critério:** os critérios herdados do requisito mantêm o ID de `01` (**CA-16.1**, **CA-16.2**). Os refinados desta feature usam **`CA-F02.y`**.

---

## 1. Objetivo

Fazer o backend autenticar com a service account, abrir a planilha do usuário por ID e, quando algo falhar, dizer exatamente o que está errado e o que fazer — sem derrubar o servidor e sem que o usuário precise reiniciar nada depois de corrigir.

---

## 2. Escopo

**Inclui**
- `infra/sheets_client.py`: carga da credencial, autorização, `open_by_key`, retry com backoff e tradução de todo erro do Google para exceção de domínio (`02` §5.6).
- Exceções de domínio de conexão e os handlers HTTP que as convertem no formato de `03` §6.2.
- Lifespan que tenta conectar sem derrubar o servidor, e `GET /api/health` que reporta o estado **e permite nova tentativa** (CA-16.2).
- `README.md` na raiz com a preparação única da planilha e como rodar.

**Não inclui** (e onde será tratado)
- Criação de abas, cabeçalhos e seed de categorias — `bootstrap` é **F-03** / T-008 (REQ-15, CA-15.1, CA-15.2).
- Leitura/escrita de linhas, cache por aba e `linhas_ignoradas` (**CA-16.3**) — **F-03** / T-009.
- `POST /api/sistema/recarregar` — **F-14** / T-032.
- Banner de erro e botão "Tentar novamente" na interface — **F-04** / T-011 e T-012.
- Qualquer endpoint de negócio (`/api/categorias`, `/api/lancamentos`, …) — M1 em diante.

---

## 3. Comportamento detalhado

### 3.1 Carga da credencial e abertura da planilha (T-004)

1. `Settings.google_credentials_path` é resolvido relativamente ao diretório do processo (`backend/`); o padrão `../credentials.json` aponta para a raiz do repositório (`02` §6).
2. Credencial carregada com **`Credentials.from_service_account_file(caminho, scopes=ESCOPOS)`** — o método correto, não `from_service_file` (`02` §5.3).
3. Escopos, exatamente os de `02` §5.3:
   - `https://www.googleapis.com/auth/spreadsheets`
   - `https://www.googleapis.com/auth/drive`
4. `gspread.authorize(credenciais)` e **`open_by_key(settings.spreadsheet_id)`** — nunca `open()` por nome (`02` §5.2).
5. O único campo do `credentials.json` que o código lê explicitamente é **`client_email`** (Q2), usado só na mensagem de 403 de permissão. Nenhum outro campo — em especial `private_key` — é lido, logado ou devolvido (RNF-05).
6. Toda chamada ao gspread usa **argumentos nomeados** (`02` §5.4).

### 3.2 Retry com backoff (T-004)

Conforme `02` §5.5, apenas para falhas **transitórias**:

| Situação | Retenta? |
|---|---|
| HTTP 429 (cota) | sim |
| HTTP 5xx | sim |
| Erro de transporte/conexão | sim |
| HTTP 403 (sem permissão) | **não** — fail fast |
| HTTP 404 / `SpreadsheetNotFound` | **não** — fail fast |
| Credencial ausente/inválida | **não** — fail fast |
| Outro código HTTP (ex.: 400) | **não** — não é transitório; reporta como `ErroPlanilha` |
| Exceção que não é falha de planilha (defeito nosso) | **não** — sobe intacta, vira `ERRO_INTERNO` |

Até **4 tentativas**. A espera usa `min(2**falhas + aleatorio(0, 1), 16)` segundos, onde `falhas` é quantas tentativas já falharam — ou seja **2 s, 4 s e 8 s** (mais o jitter) antes das tentativas 2, 3 e 4; o teto de 16 s só vale se o número de tentativas crescer. `02` §5.5 escreve `2^n` sem fixar o `n`; esta é a leitura adotada em T-004. Esgotadas as tentativas → `PlanilhaIndisponivel`.

### 3.3 Tradução de erros (T-004)

Implementa a tabela de `02` §5.6 — que esta feature **ampliou** com a linha do 403 de API desativada (Q5, `02` → 1.6):

| Situação | Detecção | Exceção | HTTP | Mensagem |
|---|---|---|---|---|
| Credencial ausente/inválida | `FileNotFoundError` / `ValueError` | `CredenciaisInvalidas` | 503 | "Arquivo de credenciais não encontrado ou inválido." |
| Planilha não compartilhada | `APIError` 403 | `SemPermissaoPlanilha` | 503 | "Compartilhe a planilha com `<client_email>` como Editor." |
| Sheets API desativada no projeto | `APIError` 403 com `reason` `SERVICE_DISABLED`/`accessNotConfigured` | `ApiSheetsDesabilitada` | 503 | "Ative a Google Sheets API no projeto do Google Cloud e tente novamente." |
| ID inexistente | `SpreadsheetNotFound` / 404 | `PlanilhaNaoEncontrada` | 503 | "Planilha não encontrada. Confira SPREADSHEET_ID." |
| Cota/instabilidade após retries | 429 / 5xx | `PlanilhaIndisponivel` | 503 | "Google Sheets indisponível no momento. Tente novamente." |
| Sem internet | erro de transporte | `PlanilhaIndisponivel` | 503 | idem |

### 3.4 Inicialização e estado da conexão (T-005)

1. No lifespan: carregar `Settings` e tentar conectar **uma única vez**, sem a política de retry (Q4) — o servidor sobe rápido mesmo sem internet. **Falha não derruba o servidor** (`03` §4.5) — a exceção é guardada.
2. O estado fica em um objeto de conexão criado em `main.py` e exposto aos routers por `api/deps.py` — o router **não** importa `infra` (regra de camadas, `03` §4.2).
3. O `bootstrap` (criação de abas) é chamado deste mesmo lifespan, mas só existe em T-008; aqui o passo fica ausente, não simulado.

### 3.5 `GET /api/health` (T-005)

1. Responde **sempre 200**, mesmo com a planilha inacessível — é o que alimenta o banner do frontend (`03` §7.2), e um 503 aqui impediria o app de distinguir "backend caiu" de "planilha com problema".
2. Se ainda não há conexão, **tenta conectar na hora**, com **uma única tentativa** (sem a política de retry) — é isso que faz o botão "Tentar novamente" funcionar sem reiniciar o processo (CA-16.2).
3. Conexão bem-sucedida: devolve o título real da planilha.
4. Falha: devolve `planilha.ok = false` com o `codigo` e a `mensagem` da tabela §3.3.

### 3.6 Handlers de erro (T-005)

1. Cada exceção de conexão → resposta no formato de `03` §6.2, com HTTP 503 e o `codigo` correspondente.
2. `RequestValidationError` do Pydantic → **422** com `codigo: "VALIDACAO"` e um item em `detalhes` por campo inválido (`campo` = caminho do campo sem o prefixo `body`).
3. Exceção não prevista → **500** `ERRO_INTERNO`, mensagem genérica; o detalhe vai só para o log (`03` §6.2).
4. Nenhum handler expõe *traceback* nem caminho de arquivo na resposta.

### 3.7 README (T-006)

Seções, na ordem: pré-requisitos (Python 3.12+, Node 24) · preparação única da planilha (criar planilha, achar o `client_email` no próprio `credentials.json`, compartilhar como Editor, copiar o ID da URL) · `.env` a partir do `.env.example` · como rodar backend e frontend · como rodar testes · o que fazer diante de cada mensagem de erro da tabela §3.3.

---

## 4. Critérios de aceite

**Herdados de `01` (REQ-16)**

- [x] **CA-16.1** Dado que a planilha não foi compartilhada com a service account, quando o backend tenta abri-la, então a falha vira `SemPermissaoPlanilha` → HTTP 503 `SEM_PERMISSAO_PLANILHA`, e a mensagem diz para compartilhar a planilha **como Editor**. *(T-004: exceção e texto; T-005: o 503 no envelope.)*
- [x] **CA-16.2** Dado que a conexão falhou por causa temporária e o usuário corrigiu a causa, quando `GET /api/health` é chamado de novo, então a resposta passa a `planilha.ok = true` **sem reiniciar o processo**.

> **CA-16.3** (linhas inválidas ignoradas e contadas) **não** é desta feature — é T-009, em F-03.

**Refinados desta feature**

- [x] **CA-F02.1** Dado o módulo de infraestrutura, quando as credenciais são carregadas, então usa `from_service_account_file` com exatamente os dois escopos de `02` §5.3, e a planilha é aberta com `open_by_key` (nunca `open()` por nome).
- [x] **CA-F02.2** Dado um erro 429, quando a operação é executada, então há **até 4 tentativas** com espera crescente e, se todas falharem, o resultado é `PlanilhaIndisponivel`.
- [x] **CA-F02.3** Dado um erro 403 ou 404, quando a operação é executada, então **não há retry** (exatamente 1 chamada ao Google) e a exceção específica é levantada de imediato.
- [x] **CA-F02.4** Dada cada linha da tabela de `02` §5.6, quando a situação correspondente ocorre, então a exceção de domínio e a mensagem são as daquela linha — uma verificação por linha.
- [x] **CA-F02.5** Dado qualquer erro tratado por esta feature, quando a resposta HTTP é gerada, então o corpo segue `03` §6.2 (`{"erro": {"codigo", "mensagem", "detalhes"}}`) com status 503 e o `codigo` da tabela de §6.2.
- [x] **CA-F02.6** Dado um corpo de requisição inválido, quando o Pydantic rejeita, então a resposta é 422 `VALIDACAO` no formato de `03` §6.2, com um item em `detalhes` por campo.
- [x] **CA-F02.7** Dada uma exceção não prevista em um endpoint, quando a resposta é gerada, então é 500 `ERRO_INTERNO` com mensagem genérica, **sem** traceback nem caminho de arquivo no corpo.
- [x] **CA-F02.8** Dada a planilha acessível, quando `GET /api/health` é chamado, então responde 200 com `status: "ok"`, `planilha.ok = true` e `planilha.titulo` igual ao título real da planilha.
- [x] **CA-F02.9** Dada a planilha inacessível por qualquer causa da tabela §3.3, quando `GET /api/health` é chamado, então responde **200** (não 503) com `planilha.ok = false` e `planilha.erro` contendo `codigo` e `mensagem` daquela causa.
- [x] **CA-F02.10** Dada a planilha inacessível na inicialização, quando o servidor sobe, então `uvicorn` **continua no ar** e qualquer requisição é atendida (nada de processo morto — `03` §4.5).
- [x] **CA-F02.11** Dado qualquer caminho de erro desta feature, quando os logs e as respostas são inspecionados, então não aparece nenhum campo de `credentials.json` além de `client_email` (RNF-05).
- [x] **CA-F02.12** Dado o router de health, quando seus imports são inspecionados, então ele não importa `gspread` nem `app.infra` — só `main.py` e `api/deps.py` conhecem a implementação concreta (`03` §4.2).
- [x] **CA-F02.14** Dado um 403 cujo `reason` é `SERVICE_DISABLED` ou `accessNotConfigured`, quando o erro é traduzido, então a exceção é `ApiSheetsDesabilitada` com a mensagem de ativar a API; dado qualquer outro 403, então é `SemPermissaoPlanilha`.
- [~] **CA-F02.13** Dado o `README.md` da raiz, quando um leitor novo o segue do zero, então há passo a passo para obter o `client_email`, compartilhar a planilha, pegar o ID, preencher o `.env` e subir backend e frontend, além de uma linha por mensagem de erro da tabela §3.3. *(T-006: as duas partes automáticas — códigos/mensagens e passos essenciais — têm teste; a leitura "do zero" com planilha real depende do usuário.)*

---

## 5. Casos de borda

| # | Caso | Comportamento esperado | Regra |
|---|---|---|---|
| 1 | `GOOGLE_CREDENTIALS_PATH` aponta para arquivo inexistente. | `CredenciaisInvalidas`; o caminho tentado pode ir ao log, o conteúdo nunca. | `02` §5.6 |
| 2 | `credentials.json` existe mas é JSON inválido ou não é de service account. | `CredenciaisInvalidas` (`ValueError`/`KeyError` na carga), mesma mensagem. | `02` §5.6 |
| 3 | Sem internet na inicialização. | Servidor sobe; `/api/health` responde 200 com `PLANILHA_INDISPONIVEL`. | CA-F02.10 |
| 4 | Sem internet quando `/api/health` é chamado. | Uma tentativa, falha rápida, 200 com `ok=false`. Não bloqueia por 30 s tentando 4 vezes. | §3.5 |
| 5 | `SPREADSHEET_ID` com o **nome** da planilha em vez do ID. | `PlanilhaNaoEncontrada` — "Confira SPREADSHEET_ID". | `02` §5.6 |
| 6 | `SPREADSHEET_ID` com a URL inteira colada. | Mesmo tratamento do caso 5 — `PlanilhaNaoEncontrada`. O backend **não** extrai o ID de uma URL (Q6); o README é explícito sobre qual pedaço copiar. | Q6 |
| 7 | Planilha compartilhada como **Leitor**, não Editor. | O `open_by_key` funciona; a falha só aparece na primeira escrita (T-008/T-009). Em F-02 o health reporta `ok=true`. Registrado para não surpreender depois. | `02` §5.1 |
| 8 | 429 na 1ª e 2ª tentativas, sucesso na 3ª. | Operação conclui normalmente; nenhum erro sobe. | `02` §5.5 |
| 9 | 429 em todas as 4 tentativas. | `PlanilhaIndisponivel`. Tempo total ≈ soma das esperas (≤ ~30 s) — por isso o health não usa retry. | §3.2, §3.5 |
| 10 | Planilha renomeada pelo usuário. | Abrir por ID continua funcionando; `planilha.titulo` reflete o nome novo. | `02` §5.2 |
| 11 | `/api/health` chamado duas vezes em sequência com a planilha ok. | A segunda não repete a autenticação — a conexão estabelecida é reaproveitada. | `02` §5.5 (cotas) |
| 12 | Credencial válida, mas a **Sheets API** está desativada no projeto Google. | 403 desambiguado pelo `reason`: `SERVICE_DISABLED`/`accessNotConfigured` → `ApiSheetsDesabilitada` ("Ative a Google Sheets API"); qualquer outro 403 → `SemPermissaoPlanilha`. | `02` §5.6 (linha nova) |

---

## 6. Contrato e dados

**API** (trecho de `03` §6.1 realizado por esta feature)

| Método | Caminho | Entrada | Saída |
|---|---|---|---|
| GET | `/api/health` | — | `200 {status, planilha: {ok, titulo, erro?}}` |

Esquema proposto (detalhamento que **falta** em `03` §6.3 — depende de Q3):

```jsonc
// 200 — planilha acessível
{ "status": "ok",
  "planilha": { "ok": true, "titulo": "Planilha Financeira", "erro": null } }

// 200 — planilha inacessível (o app abre e mostra banner)
{ "status": "degradado",
  "planilha": { "ok": false, "titulo": null,
                "erro": { "codigo": "SEM_PERMISSAO_PLANILHA",
                          "mensagem": "Compartilhe a planilha com ... como Editor." } } }
```

Formato de erro das **demais** respostas ≥ 400 (de `03` §6.2, sem alteração):

```jsonc
{ "erro": { "codigo": "PLANILHA_INDISPONIVEL", "mensagem": "...", "detalhes": [] } }
```

Códigos usados por esta feature: `PLANILHA_INDISPONIVEL`, `SEM_PERMISSAO_PLANILHA`, `PLANILHA_NAO_ENCONTRADA`, `CREDENCIAIS_INVALIDAS`, `API_SHEETS_DESABILITADA` (503) · `VALIDACAO` (422) · `ERRO_INTERNO` (500). O esquema do health agora está em `03` §6.3.

**Planilha** — F-02 **não lê nem escreve nenhuma célula**. Só abre o documento e lê o título (metadado). Nenhuma aba, coluna ou `versao_schema` é tocada; `03` §5 não muda.

---

## 7. Interface

Sem tela nesta feature — é backend e documentação. O consumo de `/api/health` pelo frontend (banner + "Tentar novamente") é **T-012**, em F-04.

Mensagens ao usuário (pt-BR) produzidas aqui e exibidas depois pelo frontend: exatamente as quatro da tabela §3.3, sem variação de texto, para que F-04 possa exibi-las direto sem reescrever.

---

## 8. Plano de testes

Todos com **fakes**; nada nesta feature fala com o Google de verdade (`02` §8). Um teste `@integracao` real contra `SPREADSHEET_ID_TESTE` só aparece em T-009.

| Teste | Nível | Cobre |
|---|---|---|
| `tests/unit/test_sheets_client.py::test_usa_from_service_account_file_e_escopos__CA_F02_1` | unitário BE | CA-F02.1 |
| `...::test_abre_por_id_e_nao_por_nome__CA_F02_1` | unitário BE | CA-F02.1 |
| `...::test_retenta_ate_quatro_vezes_no_429__CA_F02_2` | unitário BE | CA-F02.2 |
| `...::test_sucesso_na_terceira_tentativa__CA_F02_2` | unitário BE | CA-F02.2, borda 8 |
| `...::test_espera_cresce_e_tem_teto_de_16s__CA_F02_2` | unitário BE | CA-F02.2 (relógio falso) |
| `...::test_nao_retenta_403_e_404__CA_F02_3` | unitário BE | CA-F02.3 |
| `...::test_erro_inesperado_sobe_intacto_sem_retry__CA_F02_3` | unitário BE | CA-F02.3 (defeito nosso não é retentado) |
| `...::test_mensagem_de_403_nomeia_a_conta_de_servico__CA_16_1` | unitário BE | **CA-16.1** (texto e `client_email`) |
| `...::test_403_de_api_desativada_vira_excecao_propria__CA_F02_14` | unitário BE | CA-F02.14 |
| `...::test_traduz_cada_erro_do_google__CA_F02_4` (parametrizado por linha de `02` §5.6) | unitário BE | CA-F02.4 |
| `...::test_credencial_ausente_e_invalida__CA_F02_4` | unitário BE | CA-F02.4, bordas 1 e 2 |
| `...::test_nao_loga_conteudo_da_credencial__CA_F02_11` | unitário BE | CA-F02.11 |
| `tests/api/test_health.py::test_health_ok_com_titulo__CA_F02_8` | API BE | CA-F02.8 |
| `...::test_health_200_com_planilha_inacessivel__CA_F02_9` (parametrizado pelas 4 causas) | API BE | CA-F02.9 |
| `...::test_health_reconecta_sem_reiniciar__CA_16_2` | API BE | **CA-16.2** |
| `...::test_health_sem_permissao_pede_compartilhar_como_editor__CA_16_1` | API BE | **CA-16.1** |
| `...::test_health_nao_reautentica_quando_ja_conectado__CA_F02_8` | API BE | borda 11 |
| `tests/api/test_erros.py::test_formato_de_erro_503__CA_F02_5` | API BE | CA-F02.5 |
| `...::test_rota_inexistente_usa_o_envelope_padrao__CA_F02_5` | API BE | CA-F02.5 (erro do framework) |
| `...::test_validacao_pydantic_vira_422__CA_F02_6` | API BE | CA-F02.6 |
| `...::test_excecao_inesperada_vira_500_generico__CA_F02_7` | API BE | CA-F02.7 |
| `tests/api/test_app.py::test_app_sobe_com_planilha_inacessivel__CA_F02_10` | API BE | CA-F02.10 |
| `tests/unit/test_camadas.py::test_router_nao_importa_infra__CA_F02_12` | unitário BE | CA-F02.12 |
| `...::test_domain_importa_apenas_biblioteca_padrao__CA_F02_12` | unitário BE | CA-F02.12 |
| `...::test_infra_nao_importa_api_nem_services__CA_F02_12` | unitário BE | CA-F02.12 |
| `tests/api/test_app.py::test_health_e_a_unica_rota_da_api__CA_F02_8` | API BE | fronteira: nada de endpoint de negócio antes de M1 |
| `tests/unit/test_readme.py::test_readme_documenta_cada_erro_de_planilha__CA_F02_13` (parametrizado por subclasse de `ErroPlanilha`) | unitário BE | CA-F02.13 |
| `...::test_readme_cobre_a_preparacao_e_a_execucao__CA_F02_13` | unitário BE | CA-F02.13 |
| Leitura do `README.md` seguindo os passos numa planilha nova | manual (DOC) | CA-F02.13 (parte não automatizável) |

---

## 9. Divisão em tarefas

| Tarefa | Escopo nesta feature | Arquivos principais |
|---|---|---|
| **T-004** (BE) | Cliente da planilha: credencial, escopos, `open_by_key`, retry/backoff, tradução de erros. Exceções de domínio de conexão (ver Q1). | `backend/app/domain/__init__.py`, `backend/app/domain/erros.py`, `backend/app/infra/__init__.py`, `backend/app/infra/sheets_client.py`, `backend/tests/unit/test_sheets_client.py` |
| **T-005** (BE) | Handlers HTTP no formato `03` §6.2, lifespan tolerante a falha, `GET /api/health` com nova tentativa. | `backend/app/api/erros.py`, `backend/app/api/deps.py`, `backend/app/api/schemas.py`, `backend/app/api/routers/health.py`, alterações em `backend/app/main.py`, `backend/tests/api/test_health.py`, `backend/tests/api/test_erros.py`, `backend/tests/unit/test_camadas.py` |
| **T-006** (DOC) | README da raiz: pré-requisitos, preparação da planilha, `.env`, execução, testes e o que fazer em cada erro. | `README.md` |

Ordem: T-004 → T-005; T-006 depende só de T-004 (`05` §4) e pode ser escrita em paralelo com T-005.

`api/deps.py` não aparece no texto de T-005 em `05`, mas é **exigido** pela regra de camadas de `03` §4.2 (o router não pode importar `infra`) e já consta da árvore de `03` §3 — então entra em T-005.

---

## 10. Decisões tomadas nesta feature

| Decisão | Motivo | Virou ADR? |
|---|---|---|
| `/api/health` responde **sempre 200**, inclusive com a planilha quebrada. | É o que permite ao frontend distinguir "backend fora" de "planilha com problema" e mostrar o banner (`03` §7.2). Os 503 de `03` §6.2 valem para os endpoints de negócio. | Não |
| `/api/health` tenta reconectar, com **uma** tentativa, sem a política de retry. | É o mecanismo de CA-16.2 ("tentar novamente sem reiniciar"); usar as 4 tentativas faria o botão travar a interface por ~30 s. | Não |
| Retry só para 429/5xx/transporte; 403/404/credencial falham na primeira. | `02` §5.5 fala de cota e instabilidade; repetir um erro de permissão gasta cota e atrasa a mensagem correta. | Não |
| Conexão exposta aos routers via `api/deps.py`. | Regra de camadas de `03` §4.2: `api` não importa `infra`, exceto `deps.py`/`main.py`. | Não |
| `domain/erros.py` passa de T-005 para **T-004** (Q1). | T-004 traduz os erros do Google e precisa das exceções; T-005 vem depois. Texto das duas tarefas ajustado em `05`. | Não |
| A mensagem de 403 traz o `client_email` real (Q2). | É o que torna CA-16.1 acionável. O código lê **só** esse campo; `private_key` nunca é lida, logada ou devolvida (RNF-05). | Não |
| `status` do health: `"ok"` / `"degradado"` (Q3). | `03` §6.1 não definia os valores; esquema acrescentado a `03` §6.3. | Não |
| 403 desambiguado por `reason`, com exceção própria para API desativada (Q5). | A mensagem única mandaria o usuário mexer em compartilhamento quando o problema é outro. Linha nova em `02` §5.6 e código novo em `03` §6.2. | Não |
| `SPREADSHEET_ID` estrito: URL colada não é normalizada (Q6). | Menos código mágico; o erro já diz "Confira SPREADSHEET_ID" e o README mostra o que copiar. | Não |
| `infra` recebe `caminho_credenciais` e `spreadsheet_id` avulsos, não `Settings` (T-004). | A regra de camadas de `03` §4.2 não autoriza `infra` a importar `config`; e a função fica trivial de testar. | Não |
| Exceções de domínio carregam `codigo` + `mensagem`, **sem** status HTTP (T-004). | `domain` só importa stdlib e pydantic; o mapa `codigo` → HTTP mora em `api/erros.py` (T-005), como `03` §6.2 define. | Não |
| Backoff: `falhas` como expoente → 2 s, 4 s, 8 s (T-004). | `02` §5.5 deixa o `n` ambíguo; ver §3.2. | Não |
| Erro que não é falha de planilha **sobe intacto**, sem retry (T-004). | Retentar e reetiquetar um `AttributeError` como "Google indisponível" esconderia defeito nosso por ~14 s; `03` §6.2 já prevê `ERRO_INTERNO` para o imprevisto. | Não |
| `open_by_key` no gspread 6 levanta `APIError` 404, não `SpreadsheetNotFound` (T-004). | As duas formas são tratadas; `SpreadsheetNotFound` é de `open()` por nome. | Não |
| `obter_client_email` nunca levanta (T-004). | Montar uma mensagem de erro não pode gerar outro erro; sem o arquivo, a mensagem cai na versão genérica. | Não |
| `ConexaoPlanilha` vive em `infra/sheets_client.py`; o router a recebe pelo alias `ConexaoDep` de `deps.py` (T-005). | Ela guarda um `Spreadsheet` do gspread, logo é infraestrutura; o alias mantém o arquivo do router sem importar `infra` (CA-F02.12). `03` §3 atualizado. | Não |
| `criar_app(conexao=...)` para os testes (T-005). | O estado nasce no lifespan, onde `dependency_overrides` de `02` §8 não alcança. Extensão natural de ADR-12. | Não |
| Erros do framework entram no envelope de `03` §6.2 (T-005). | §6.2 diz "todas as respostas ≥ 400"; uma única forma simplifica o `erro.interceptor.ts` de T-011. Registrado em `03` → 1.4. | Não |
| Handler registrado para a `HTTPException` do **Starlette** (T-005). | O 404 de roteamento levanta a classe-mãe; registrar só a do FastAPI deixava passar `{"detail": ...}`. Descoberto por teste. | Não |
| `logging.basicConfig` em nível INFO dentro de `criar_app` (T-005). | Cumpre `02` §3; sem isso o aviso de retry e o registro de abertura da planilha não apareciam no terminal do uvicorn. | Não |
| `conftest` aponta `GOOGLE_CREDENTIALS_PATH` para arquivo inexistente (T-005). | O padrão `../credentials.json` é o arquivo real: com o lifespan, cada `pytest` tentaria autenticar no Google. Agora a suíte falha rápido, sem rede e sem tocar na credencial (RNF-05). | Não |
| README manda descobrir o `client_email` pelo próprio `/api/health` (T-006). | A mensagem de 403 já traz o e-mail: evita mandar o usuário abrir a credencial. A instrução manual fica como alternativa. | Não |
| Guarda automatizado do README (T-006). | A última cláusula de CA-F02.13 ("uma linha por mensagem de erro") é o que mais apodrece; o teste lê as subclasses de `ErroPlanilha` e cobra documentação quando um erro novo aparece. Validado com teste negativo. | Não |

---

## 11. Questões em aberto

**Respondidas em 2026-09-29 — nenhuma em aberto.**

- [x] **Q1** → `domain/erros.py` move para **T-004**; T-005 fica com `api/erros.py`, `api/deps.py`, lifespan e health. `05` ajustado.
- [x] **Q2** → **Sim**, a mensagem traz o `client_email` real; o código lê exclusivamente esse campo.
- [x] **Q3** → `status` é `"ok"` ou `"degradado"`; esquema registrado em `03` §6.3.
- [x] **Q4** → **uma** tentativa de conexão na inicialização.
- [x] **Q5** → 403 desambiguado pelo `reason`; nova exceção `ApiSheetsDesabilitada` e linha nova em `02` §5.6 (+ `API_SHEETS_DESABILITADA` em `03` §6.2).
- [x] **Q6** → `SPREADSHEET_ID` estrito; sem extração de ID a partir de URL.

---

## Revisões

| Data | Alteração |
|---|---|
| 2026-09-29 | Criação (`/especificar-feature F-02`). Status `Rascunho` — 6 questões em aberto. |
| 2026-09-29 | Q1–Q6 respondidas → status **Aprovada**. Acrescentados CA-F02.14 e o tratamento do 403 ambíguo; `02` → 1.6 e `03` → 1.3. |
| 2026-09-29 | **T-004 concluída.** CA-F02.1, .2, .3, .4, .11 e .14 verificados por 20 testes unitários; CA-16.1 coberta na parte de domínio. §3.2 ganhou o expoente do backoff e as linhas de "não retenta". Restam CA-16.2, CA-F02.5..10, .12 (T-005) e .13 (T-006). |
| 2026-09-29 | **T-005 concluída.** CA-16.1 (completa), CA-16.2 e CA-F02.5..10 e .12 verificados por 17 testes novos (46 no total) e por teste de fumaça com uvicorn real. `03` → 1.4. Resta CA-F02.13 (T-006, README). |
| 2026-09-29 | **T-006 concluída — tarefas de F-02 completas.** `README.md` na raiz com preparação da planilha, execução e tabela de erros; 6 testes novos guardam a documentação. `03` → 1.5. CA-F02.13 aguarda apenas a leitura de ponta a ponta pelo usuário. |
