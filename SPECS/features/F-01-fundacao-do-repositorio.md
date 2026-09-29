# F-01 — Fundação do repositório

| Campo | Valor |
|---|---|
| Feature | F-01 |
| Marco | M0 |
| Status | Concluída |
| Requisitos | RNF-01, RNF-05 (parcial), RNF-03 (locale), RNF-08 (infra de testes) |
| Regras | — (nenhuma RN de negócio nesta feature) |
| Depende de | — |
| Tarefas | T-001, T-002, T-003 |
| Atualizado em | 2026-09-29 |

> **Nota sobre IDs de critério:** F-01 não cobre nenhum `REQ-xx` (só requisitos não funcionais, que não têm `CA-xx.y` em `01`). Os critérios desta feature usam o prefixo **`CA-F01.y`**, exclusivo dela, para não colidir com a numeração de `01-requisitos.md`.

---

## 1. Objetivo

Deixar o repositório versionado com segurança (a chave da service account nunca entra no Git) e os dois esqueletos — backend FastAPI e frontend Angular 22 — subindo vazios, com testes, lint e build funcionando. É a base sobre a qual as outras 32 tarefas são construídas.

---

## 2. Escopo

**Inclui**
- `git init` na raiz, `.gitignore` cobrindo tudo de `02` §6, e verificação explícita de que `credentials.json` está ignorado (RNF-05).
- Pastas `backend/`, `frontend/`, `scripts/` conforme `03` §3.
- Esqueleto do backend: dependências, `pyproject.toml` (ruff + pytest com marcador `integracao`), `app/main.py` (app FastAPI + CORS), `app/config.py` (`Settings`), `.env.example`, `tests/conftest.py` e um teste trivial.
- Esqueleto do frontend: `ng new frontend` com Angular CLI 22 (standalone, zoneless, SCSS, Vitest), Angular Material 22, `chart.js@^4`, `proxy.conf.json`, locale pt-BR/BRL.

**Não inclui** (e onde será tratado)
- `GET /api/health`, handlers de erro, exceções de domínio e lifespan (**F-02** / T-005).
- Qualquer código gspread, autenticação Google ou leitura da planilha (**F-02** / T-004).
- Tipos de domínio (`Dinheiro`, `datas`, `modelos`, enums), repositórios e cache (**F-03** / T-007..T-009).
- Shell visual (barra superior, navegação, rotas lazy), `GraficoDirective`, stores, interceptor de erro (**F-04** / T-010..T-012).
- `scripts/*.ps1` — a pasta é criada aqui, o conteúdo vem em **F-15** / T-033.

Também inclui (decidido em Q6): reforço das regras de `deny` de `Bash` em `.claude/settings.json`, para que `credentials.json` também não possa ser lido por comando de terminal (RNF-05).

---

## 3. Comportamento detalhado

Esta feature não tem comportamento visível ao usuário final; o "usuário" aqui é quem desenvolve e executa o app na própria máquina (RNF-01).

### T-001 — Repositório versionado com segurança

1. O `.gitignore` é criado **antes** de qualquer `git add`, porque `credentials.json` já existe na raiz do projeto (RNF-05, risco registrado em `02` §10).
2. `git init -b main` na raiz `PlanilhaFinanceira/` (Q1), um único repositório (sem repositórios aninhados em `backend/` nem `frontend/`).
3. São criadas as pastas `backend/` e `scripts/` (cada uma com `.gitkeep`, pois o Git não versiona pasta vazia) e `frontend/` (criada **vazia, sem `.gitkeep`**, para não impedir o `ng new` de T-003 — ver caso de borda 5 e Questão Q3).
4. Verificação: `git status --porcelain` não lista `credentials.json`; `git check-ignore -v credentials.json` confirma qual regra o ignora.
5. São versionados: `CLAUDE.md`, `SPECS/`, `.claude/settings.json`, `.claude/commands/`, `.gitignore`.
6. `.claude/settings.json` ganha regras de `deny` para `Bash` cobrindo a leitura de `credentials.json` por terminal (Q6), somando-se às de `Read`/`Edit`/`Write` já existentes.
7. Ao final, com T-001 pronta e as verificações registradas, é feito o commit `T-001: inicializa repositório com .gitignore e estrutura de pastas` (autorizado em Q1).

Conteúdo previsto de `.gitignore` (lista obrigatória de `02` §6 + extensões da Questão Q4):

```gitignore
# Credenciais e configuração local (RNF-05)
credentials.json
backend/.env
.env

# Python
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/

# Node / Angular
node_modules/
dist/
.angular/

# Ferramentas locais
.claude/settings.local.json

# IDEs e SO
.idea/
.vscode/
Thumbs.db
desktop.ini
```

### T-002 — Esqueleto do backend

1. `backend/requirements.txt` e `backend/requirements-dev.txt` exatamente com o conteúdo de `02` §1.1.
2. `backend/pyproject.toml` com `requires-python = ">=3.12"` e configuração de **ruff** (lint + format) e **pytest** (`testpaths`, `markers = ["integracao: ..."]`).
3. `backend/app/config.py`: `Settings(BaseSettings)` lendo `backend/.env`, com os campos de `02` §6 — `SPREADSHEET_ID` (obrigatório), `GOOGLE_CREDENTIALS_PATH` (padrão `../credentials.json`), `CACHE_TTL_SEGUNDOS` (padrão `30`), `CORS_ORIGINS` (padrão `http://localhost:4200`), `SPREADSHEET_ID_TESTE` (opcional). O valor de `GOOGLE_CREDENTIALS_PATH` é apenas um caminho — o arquivo **não** é lido nesta tarefa e seu conteúdo nunca vai a log (RNF-05).
4. `backend/app/main.py`: `FastAPI()` com título/versão, `CORSMiddleware` restrito a `CORS_ORIGINS`, e **nenhuma rota de negócio**. `/openapi.json` e `/docs` existem automaticamente.
5. `backend/tests/conftest.py` com uma fixture `cliente` (`TestClient`) e o teste trivial verificando que o app sobe.
6. O servidor escuta apenas `127.0.0.1` (RNF-05) — garantido pelo comando documentado em `02` §2, não por código.

### T-003 — Esqueleto do frontend

1. `ng new frontend` com Angular CLI 22, aceitando os padrões da v22 (standalone, **zoneless**, roteamento, **Vitest**), SCSS, sem SSR e **sem `git init` próprio** (`--skip-git`).
2. `ng add @angular/material` (major 22) — tema, tipografia e animações. Tema definido em Q2: primária **azul** (`$azure-palette`) com `color-scheme: light dark`, ou seja, claro/escuro conforme o sistema. `provideNativeDateAdapter()`/`MAT_DATE_LOCALE` só serão usados quando houver formulário (F-06), mas o pacote já entra aqui.
3. `npm i chart.js@^4` (usado diretamente, ADR-11; **sem wrapper** — a `GraficoDirective` é T-010/F-04).
4. `frontend/proxy.conf.json` redirecionando `/api` → `http://127.0.0.1:8000`; `npm start` = `ng serve --proxy-config proxy.conf.json`.
5. `src/app/app.config.ts` com `provideZonelessChangeDetection()`, `provideHttpClient(withFetch())`, `registerLocaleData(localePt)`, `LOCALE_ID = 'pt-BR'`, `DEFAULT_CURRENCY_CODE = 'BRL'` (RNF-03).
6. Conferir Node 24 LTS e TypeScript na faixa `>=6.0 <6.1` (`02` §1). Ambiente atual verificado: Node **v24.19.0**, npm **11.17.0**, Python **3.13.7** — todos dentro das faixas aceitas.
7. A página padrão do Angular permanece; o shell real é T-010 (F-04).

---

## 4. Critérios de aceite

Origem em `04` §3 ("Concluída quando: `git status` não lista `credentials.json`; `uvicorn` sobe e `ng serve` abre página padrão; `pytest` e `npm test` rodam"), refinados abaixo em critérios verificáveis.

**T-001 — repositório**

- [x] **CA-F01.1** Dado o projeto na raiz, quando `git status --porcelain` é executado, então `credentials.json` **não** aparece na saída, e `git check-ignore -v credentials.json` sai com código 0 apontando a regra do `.gitignore`.
- [x] **CA-F01.2** Dado o `.gitignore`, quando se testa cada caminho de `02` §6 (`credentials.json`, `backend/.env`, `.venv/`, `node_modules/`, `dist/`, `__pycache__/`, `.pytest_cache/`, `.angular/`), então **todos** são reportados como ignorados por `git check-ignore`.
- [x] **CA-F01.3** Dado o repositório inicializado, quando se lista a raiz, então existem `backend/`, `frontend/` e `scripts/`, e `git status` mostra `backend/.gitkeep` e `scripts/.gitkeep` como rastreáveis.
- [x] **CA-F01.4** Dado que existe `.git` apenas na raiz, quando se procura `.git` em `backend/` e `frontend/`, então nada é encontrado (nenhum repositório aninhado).
- [x] **CA-F01.19** Dado o repositório inicializado, quando `git rev-parse --abbrev-ref HEAD` é executado, então o resultado é `main` (Q1).
- [x] **CA-F01.20** Dado `.claude/settings.json`, quando as regras são inspecionadas, então há `deny` para `Read`/`Edit`/`Write` **e** para `Bash` sobre `credentials.json` (Q6), e o arquivo continua versionado (RNF-05).

**T-002 — backend**

- [x] **CA-F01.5** Dado `.venv` com `requirements-dev.txt` instalado e um `.env` válido, quando `uvicorn app.main:app --host 127.0.0.1 --port 8000` é executado, então o servidor sobe sem erro e `GET /openapi.json` responde **200**.
- [x] **CA-F01.6** Dado o esqueleto, quando `pytest` é executado, então a suíte termina **verde**, com pelo menos 1 teste coletado e **0** falhas.
- [x] **CA-F01.7** Dado um teste marcado com `@pytest.mark.integracao`, quando `pytest` roda sem argumentos, então ele é **desselecionado** pelo `addopts` padrão (`-m 'not integracao'`) e nunca falha; e quando roda com `pytest -m integracao` **sem** `SPREADSHEET_ID_TESTE`, então é **pulado** com motivo explícito. Em nenhum dos casos há aviso de marcador desconhecido (`filterwarnings` o transforma em falha).
- [x] **CA-F01.8** Dado o código do backend, quando `ruff check .` e `ruff format --check .` são executados, então ambos terminam sem apontamentos.
- [x] **CA-F01.9** Dado um `.env` com as 5 variáveis de `02` §6, quando `Settings()` é instanciado, então cada campo recebe o valor do arquivo; e com `.env` contendo só `SPREADSHEET_ID`, então `GOOGLE_CREDENTIALS_PATH == "../credentials.json"`, `CACHE_TTL_SEGUNDOS == 30` e `CORS_ORIGINS == ["http://localhost:4200"]`.
- [x] **CA-F01.10** Dado nenhum `SPREADSHEET_ID` no ambiente nem no `.env`, quando `Settings()` é instanciado, então é levantado `ValidationError` mencionando `SPREADSHEET_ID` (mensagem acionável — ver Questão Q5).
- [x] **CA-F01.11** Dado o app, quando uma requisição chega com `Origin: http://localhost:4200`, então a resposta traz `access-control-allow-origin: http://localhost:4200`; com `Origin: http://exemplo.com`, então esse cabeçalho **não** é devolvido.
- [x] **CA-F01.12** Dado `backend/.env.example` versionado, quando comparado com `02` §6, então lista as 5 variáveis, sem nenhum valor real de `SPREADSHEET_ID`, e `backend/.env` não é versionado.

**T-003 — frontend**

- [x] **CA-F01.13** Dado `npm install` concluído, quando `npm start` é executado, então `http://localhost:4200` abre a página padrão do Angular sem erro no console.
- [x] **CA-F01.14** Dado o backend rodando em `127.0.0.1:8000`, quando o frontend em `4200` chama uma URL relativa sob **`/api`** (único prefixo no `proxy.conf.json`), então a resposta é a do backend, byte a byte, sem erro de CORS no navegador. Caminhos fora de `/api` são servidos pelo próprio `ng serve`.
- [x] **CA-F01.15** Dado o projeto, quando `npm test` é executado (Vitest, execução única), então a suíte termina verde; e quando `npm run build` é executado, então termina sem erro.
- [x] **CA-F01.16** Dado `frontend/package.json`, quando as versões são inspecionadas, então `@angular/*` e `@angular/material` estão em `^22`, `typescript` em `>=6.0 <6.1`, `chart.js` em `^4`, e **`zone.js` não consta** em `dependencies` (projeto zoneless).
- [x] **CA-F01.17** Dado `app.config.ts`, quando o app é inicializado num teste, então `LOCALE_ID` é `pt-BR` e `DEFAULT_CURRENCY_CODE` é `BRL`; formatar `1234.56` com `CurrencyPipe` resulta em `R$ 1.234,56` e `2026-09-29` com `DatePipe`/`dd/MM/yyyy` em `29/09/2026` (RNF-03).
- [x] **CA-F01.18** Dado o frontend, quando se procura por wrapper de gráficos (`ng2-charts`, `ngx-echarts`, etc.) em `package.json`, então nenhum está presente (ADR-11).
- [x] **CA-F01.21** Dado `src/styles.scss`, quando o tema é inspecionado, então usa `mat.theme` com primária azul e `color-scheme: light dark`, e a página padrão abre legível tanto no modo claro quanto no escuro do sistema (Q2).

---

## 5. Casos de borda

| # | Caso | Comportamento esperado | Regra |
|---|---|---|---|
| 1 | `credentials.json` **já existe** na raiz e o repositório ainda não foi inicializado. | Criar `.gitignore` antes do `git init`/`git add`; nunca executar `git add -A` sem antes confirmar com `git check-ignore`. Se o arquivo chegar ao índice, remover com `git rm --cached credentials.json` antes de qualquer commit. | RNF-05 |
| 2 | `.idea/` já presente na raiz (IDE do usuário). | Ignorado pelo `.gitignore` (Questão Q4). | — |
| 3 | Usuário roda `git add` da raiz com `.venv/` e `node_modules/` já criados. | Nada dessas pastas entra no índice. | `02` §6 |
| 4 | Já existe um `.git` na raiz (usuário inicializou antes). | Não reinicializar; apenas garantir o `.gitignore` e rodar as verificações de CA-F01.1/CA-F01.2. | — |
| 5 | `ng new frontend` numa pasta `frontend/` que já existe. | Funciona se a pasta estiver **vazia**; por isso T-001 não coloca `.gitkeep` em `frontend/`. Se o CLI recusar mesmo vazia, remover a pasta e deixar o próprio `ng new` criá-la. | — |
| 6 | `ng new` tentaria criar um repositório Git dentro de `frontend/`. | Usar `--skip-git`; o repositório é único, na raiz (CA-F01.4). | — |
| 7 | Python instalado é 3.13, não 3.12. | Aceito: `requires-python = ">=3.12"`. | `02` §1 |
| 8 | Node 22.22.x em vez de 24 LTS. | Aceito conforme `02` §1 ("aceito `^22.22.3`"); registrar a versão usada nas Notas de T-003. | `02` §1 |
| 9 | Porta 8000 ou 4200 ocupada. | Falha de ambiente, não do código: documentar no README (T-006) como trocar a porta; o proxy aponta para `127.0.0.1:8000` por padrão. | — |
| 10 | `backend/.env` ausente ao subir o backend. | `Settings()` falha na inicialização com mensagem citando `SPREADSHEET_ID` (CA-F01.10). **Não** é o caso de RNF-06/REQ-16, que tratam a planilha indisponível (T-005). | Q5 |
| 11 | `CORS_ORIGINS` com mais de uma origem no `.env`. | Aceitar lista separada por vírgula e normalizar para `list[str]`. | `02` §6 |
| 12 | `GOOGLE_CREDENTIALS_PATH` aponta para arquivo inexistente. | Irrelevante em T-002: o caminho não é resolvido nem aberto nesta feature (isso é T-004/F-02). | RNF-05 |

---

## 6. Contrato e dados

**API** — F-01 **não cria nenhum endpoint do contrato de `03` §6.1**. Só existem as rotas automáticas do FastAPI:

| Método | Caminho | Entrada | Saída |
|---|---|---|---|
| GET | `/openapi.json` | — | `200` documento OpenAPI (gerado) — usado como prova de vida em CA-F01.5 |
| GET | `/docs` | — | `200` Swagger UI (gerado) |

> `GET /api/health` pertence a **T-005 (F-02)** e **não** deve ser criado nesta feature. Nenhum endpoint sob `/api` é adicionado aqui.

**Planilha** — nenhuma aba é lida ou escrita; nenhuma alteração em `03` §5 e nenhuma mudança de `versao_schema`.

**Arquivos de configuração criados** (contrato de configuração, `02` §6)

| Arquivo | Versionado | Conteúdo |
|---|---|---|
| `.gitignore` | sim | seção 3 desta spec |
| `backend/.env.example` | sim | as 5 variáveis de `02` §6, sem valores reais |
| `backend/.env` | **não** | preenchido pelo usuário |
| `frontend/proxy.conf.json` | sim | `/api` → `http://127.0.0.1:8000` |

---

## 7. Interface

Nenhuma tela do produto é criada nesta feature.

- Tela/rota: apenas a página padrão gerada pelo `ng new` (substituída em T-010/F-04).
- Componentes: nenhum componente de negócio.
- Estados: não se aplica (o frontend ainda não chama a API).
- Mensagens ao usuário (pt-BR): nenhuma na interface. As únicas mensagens desta feature são de terminal (erro de configuração do backend, CA-F01.10) e devem estar em português, citando o nome da variável.

---

## 8. Plano de testes

Nomes seguem `02` §7 (o nome do teste cita o critério coberto).

| Teste | Nível | Cobre |
|---|---|---|
| Verificação manual documentada (`git status --porcelain`, `git check-ignore -v`, `git rev-parse --abbrev-ref HEAD`, inspeção de `.claude/settings.json`), saída registrada nas Notas de T-001 | manual (DOC) | CA-F01.1..CA-F01.4, CA-F01.19, CA-F01.20 |
| `tests/api/test_app.py::test_openapi_responde__CA_F01_5` | API BE | CA-F01.5 |
| `tests/unit/test_config.py::test_settings_le_env__CA_F01_9` | unitário BE | CA-F01.9 |
| `tests/unit/test_config.py::test_settings_aplica_padroes__CA_F01_9` | unitário BE | CA-F01.9 |
| `tests/unit/test_config.py::test_cors_origins_aceita_lista__CA_F01_9` | unitário BE | CA-F01.9, borda 11 |
| `tests/unit/test_config.py::test_settings_exige_spreadsheet_id__CA_F01_10` | unitário BE | CA-F01.10 |
| `tests/unit/test_config.py::test_obter_settings_mensagem_em_portugues__CA_F01_10` | unitário BE | CA-F01.10 + §7 (mensagem em pt-BR) |
| `tests/api/test_app.py::test_sem_rotas_de_negocio__CA_F01_5` | API BE | fronteira com T-005 (§6) |
| `tests/api/test_cors.py::test_cors_permite_localhost_4200__CA_F01_11` | API BE | CA-F01.11 |
| `tests/api/test_cors.py::test_cors_rejeita_outra_origem__CA_F01_11` | API BE | CA-F01.11 |
| `tests/integracao/test_marcador.py::test_integracao_pulado_sem_variavel__CA_F01_7` | integração BE (pulado por padrão) | CA-F01.7 |
| `pytest` + `ruff check .` + `ruff format --check .` na conclusão de T-002 | comandos | CA-F01.6, CA-F01.8 |
| `src/app/app.config.spec.ts` → `formata_moeda_e_data_ptBR__CA_F01_17` | unitário FE (Vitest) | CA-F01.17 |
| `src/app/app.config.spec.ts` → `registra o locale pt-BR e o real como moeda padrão__CA_F01_17` | unitário FE (Vitest) | CA-F01.17 |
| `src/app/app.spec.ts` (gerado pelo CLI, ajustado ao título) | unitário FE (Vitest) | CA-F01.15 |
| `npm test` + `npm run build` na conclusão de T-003 | comandos | CA-F01.15 |
| Inspeção de `frontend/package.json` registrada nas Notas de T-003 | manual (FE) | CA-F01.16, CA-F01.18 |
| Abertura da página padrão nos modos claro e escuro do sistema | manual (FE) | CA-F01.21 |
| `npm start` com o backend no ar, chamando URL relativa | manual (FE) | CA-F01.13, CA-F01.14 |

Observação: T-001 é a única tarefa da feature sem teste automatizado — quando ela roda, ainda não existe executor de testes no repositório. A verificação é por comando, com a saída registrada nas Notas de `05`.

---

## 9. Divisão em tarefas

| Tarefa | Escopo nesta feature | Arquivos principais |
|---|---|---|
| **T-001** (DOC) | `git init -b main` na raiz; `.gitignore`; pastas `backend/`, `frontend/`, `scripts/`; `deny` de Bash para a credencial; verificar que `credentials.json` está ignorado. | `.gitignore`, `backend/.gitkeep`, `scripts/.gitkeep`, `.claude/settings.json` |
| **T-002** (BE) | Dependências, configuração de ferramentas, app FastAPI vazio com CORS, `Settings`, `.env.example`, infraestrutura de testes. | `backend/requirements.txt`, `backend/requirements-dev.txt`, `backend/pyproject.toml`, `backend/.env.example`, `backend/app/__init__.py`, `backend/app/main.py`, `backend/app/config.py`, `backend/tests/conftest.py`, `backend/tests/api/test_app.py`, `backend/tests/api/test_cors.py`, `backend/tests/unit/test_config.py`, `backend/tests/integracao/test_marcador.py` |
| **T-003** (FE) | Projeto Angular 22 zoneless com Material 22, Chart.js 4, proxy e locale pt-BR/BRL. | `frontend/package.json`, `frontend/angular.json`, `frontend/tsconfig.json`, `frontend/proxy.conf.json`, `frontend/src/app/app.config.ts`, `frontend/src/app/app.routes.ts`, `frontend/src/app/app.ts` + `app.html`/`app.scss`/`app.spec.ts`, `frontend/src/app/app.config.spec.ts`, `frontend/src/styles.scss` |

Ordem: T-001 → (T-002 ‖ T-003). T-002 e T-003 são independentes entre si; ambas dependem apenas de T-001 (`05` §4).

---

## 10. Decisões tomadas nesta feature

| Decisão | Motivo | Virou ADR? |
|---|---|---|
| Um único repositório Git, na raiz; `ng new --skip-git`. | O projeto é um monorepo simples backend+frontend; repositórios aninhados atrapalhariam o `git status` usado como verificação de RNF-05. | Não (estrutura já implícita em `03` §3) |
| `frontend/` criada vazia por T-001, sem `.gitkeep`; `backend/` e `scripts/` com `.gitkeep`. | O Git não versiona pasta vazia, mas o `ng new` recusa pasta não vazia. Evita conflito entre T-001 e T-003. | Não — **confirmado em Q3** |
| T-002 **não** cria `/api/health`. | O endpoint é o entregável de T-005 e depende do cliente da planilha (T-004). A prova de vida em T-002 é `/openapi.json`. | Não |
| `Settings()` falha na inicialização se faltar `SPREADSHEET_ID`. | Sem o ID o app não tem função alguma; é erro de configuração, não indisponibilidade (RNF-06/REQ-16 tratam a planilha fora do ar, em T-005). | Não — **confirmado em Q5** |
| Branch `main`; commit de T-001 autorizado. | Padrão atual do Git; autorização registrada em Q1 (CLAUDE.md §9). | Não — **confirmado em Q1** |
| Tema Material azul (`$azure-palette`) com `color-scheme: light dark`. | `02`/`03` não definem paleta; azul é neutro para dados financeiros e o modo automático evita uma preferência fixa. Impacta as cores dos gráficos em M2, que precisam funcionar nos dois modos. | Não — **confirmado em Q2** |
| `deny` de `Bash` sobre `credentials.json` em `.claude/settings.json`. | Fecha a lacuna da mitigação descrita em `02` §10 (hoje só `Read`/`Edit`/`Write` são bloqueados). | Não — **confirmado em Q6** |
| O `deny` de terminal cobre os leitores óbvios (`cat`, `head`, `tail`, `less`, `more`, `strings`, e qualquer comando PowerShell citando o arquivo), **não** é hermético. | As regras de Bash casam por prefixo de comando e qualquer interpretador (`python`, `sed`, `awk`, `base64`) leria o arquivo por outro caminho. É defesa em profundidade: a garantia de RNF-05 continua sendo o `.gitignore` (CA-F01.1) + regra 1 do `CLAUDE.md`. | Não |
| `.claude/settings.local.json` também no `.gitignore`. | Arquivo de permissões local, por máquina, criado pelo Claude Code; versioná-lo gera ruído. Extensão da decisão de Q4. | Não |
| Fábrica `criar_app()` + `obter_settings()` com `lru_cache` (T-002). | Importar `app.main` não exige `.env` preenchido, então `pytest` roda em qualquer cópia do repo. | **Sim — ADR-12** |
| `obter_settings()` converte `ValidationError` em `RuntimeError` com mensagem em pt-BR citando a variável (T-002). | A mensagem crua do Pydantic sai em inglês e cita `spreadsheet_id`; §7 exige pt-BR citando o nome da variável. `Settings()` direto continua levantando `ValidationError` (CA-F01.10). | Não |
| `GOOGLE_CREDENTIALS_PATH` tipado como `str`, não `Path` (T-002). | CA-F01.9 compara com a string `"../credentials.json"`; o caminho é relativo ao diretório do processo (`backend/`). | Não |
| `pythonpath = ["."]` e `[project]` mínimo no `pyproject.toml` (T-002). | `import app` a partir de `backend/` sem `__init__.py` nas pastas de teste; `[project]` é onde `requires-python` mora. | Não |
| Nomes de arquivo no style guide **2025** (`app.ts`, classe `App`) (T-003). | Padrão do CLI 22; `03` §3 dizia `app.component.ts` e foi atualizado. | **Sim — ADR-13** |
| `prettier` (e `jsdom`) aceitos como vieram do `ng new` (T-003). | São padrão do CLI 22; regra 7 do `CLAUDE.md` exige registrar dependência nova. Não entram na Definição de Pronto. | **Sim — ADR-14** |
| `provideZonelessChangeDetection()` mantido explícito (T-003). | O CLI 22 não o emite mais (sem `zone.js` o padrão já é zoneless), mas a função existe e deixa a garantia visível no código, como §3 desta spec descreve. | Não |
| O teste de moeda normaliza o espaço não-quebrável (T-003). | Em pt-BR o `CurrencyPipe` separa `R$` do número com U+00A0; visualmente é `R$ 1.234,56`, mas a comparação literal falharia. | Não |
| `index.html` com `lang="pt-BR"` e título `Planilha Financeira` (T-003). | RNF-03 (interface em português); o CLI gera `lang="en"` e título `Frontend`. | Não |
| Ruff com `line-length = 100` e regras `E, F, I, UP, B, SIM`. | `02` §7 exige PEP 8 via ruff sem fixar a configuração; 100 colunas acomodam type hints longos sem prejudicar a leitura. | Não — **confirmado em Q7** |
| `.gitignore` estendido além da lista de `02` §6. | A lista de `02` §6 é o mínimo obrigatório; `.idea/`, `.ruff_cache/`, `*.py[cod]` evitam ruído (o `.idea/` já existe na raiz). | Não — **confirmado em Q4** |

`02` §10 diz que "`.claude/settings.json` bloqueia leitura do arquivo pela IA" — a decisão de Q6 mantém essa afirmação verdadeira também para acesso via terminal, portanto **não** há contradição a corrigir em `02`.

Nenhuma decisão desta feature exige novo ADR em `02` §9, e nenhuma dependência fora de `02` §1 é adicionada.

---

## 11. Questões em aberto

**Respondidas em 2026-09-29**

- [x] **Q1 — Branch e commit inicial.** → Branch **`main`** (`git init -b main`); o commit `T-001: inicializa repositório com .gitignore e estrutura de pastas` está **autorizado** ao concluir T-001.
- [x] **Q2 — Tema do Angular Material.** → Primária **azul** (`$azure-palette`), com claro/escuro **seguindo o sistema** (`prefers-color-scheme`). As cores dos gráficos (M2) devem funcionar nos dois modos.
- [x] **Q5 — Falta de `SPREADSHEET_ID`.** → O backend **falha ao iniciar** com mensagem clara citando a variável. Erro de configuração é distinto de planilha indisponível (T-005 sobe degradado nesse outro caso).
- [x] **Q6 — Proteção extra da credencial.** → **Sim**: T-001 acrescenta regras de `deny` para `Bash` em `.claude/settings.json`, cobrindo leitura de `credentials.json` por comando de terminal (`cat`, `type`, `Get-Content`).

- [x] **Q3 — Pasta `frontend/` em T-001.** → **Confirmado**: `frontend/` criada vazia, sem `.gitkeep` (não rastreada pelo Git até T-003), para o `ng new` funcionar.
- [x] **Q4 — `.gitignore` estendido.** → **Confirmado**: além da lista de `02` §6, entram `.idea/`, `.vscode/`, `.ruff_cache/`, `*.py[cod]`, `Thumbs.db`, `desktop.ini`.
- [x] **Q7 — Configuração do ruff.** → **Confirmado**: `line-length = 100` e regras `E, F, I, UP, B, SIM`.

Nenhuma questão em aberto — feature `Aprovada`.

---

## Revisões

| Data | Alteração |
|---|---|
| 2026-09-29 | Criação (`/especificar-feature F-01`). Status `Rascunho` — 7 questões em aberto. |
| 2026-09-29 | Q1, Q2, Q5 e Q6 respondidas pelo usuário: branch `main` + commit de T-001 autorizado; tema Material azul seguindo o sistema; falha na inicialização sem `SPREADSHEET_ID`; `deny` de Bash para a credencial. Acrescentados CA-F01.19..21. Restam Q3, Q4, Q7. |
| 2026-09-29 | Q3, Q4 e Q7 respondidas (`frontend/` vazia sem `.gitkeep`; `.gitignore` estendido; ruff `line-length = 100` com `E, F, I, UP, B, SIM`). Nenhuma questão em aberto — status **Aprovada**; T-001 liberada para `/implementar-tarefa`. |
| 2026-09-29 | **T-001 concluída.** CA-F01.1, .2, .3, .4, .19 e .20 verificados. `.gitignore` real acrescentou `.claude/settings.local.json`; registrada a ressalva sobre o alcance do `deny` de terminal. Restam CA-F01.5..18 e .21 (T-002/T-003). |
| 2026-09-29 | **T-002 concluída.** CA-F01.5 a .12 verificados (9 testes verdes, `ruff` limpo, uvicorn real respondendo 200). CA-F01.7 refinado para o mecanismo de duas camadas (`addopts` + skip do `conftest`). ADR-12 registrado em `02`. Restam CA-F01.13..18 e .21 (T-003). |
| 2026-09-29 | **T-003 concluída — feature F-01 completa.** CA-F01.13 a .18 e .21 verificados (4 testes Vitest verdes, build ok, `ng serve` com proxy encaminhando `/api` ao backend). CA-F01.14 refinado (só `/api` é encaminhado). ADR-13 e ADR-14 em `02`; `03` → 1.2. |
