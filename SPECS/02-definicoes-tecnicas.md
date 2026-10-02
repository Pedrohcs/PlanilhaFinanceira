# 02 — Definições Técnicas

| Campo | Valor |
|---|---|
| Documento | `SPECS/02-definicoes-tecnicas.md` |
| Versão | 1.14 |
| Atualizado em | 2026-10-02 |
| Status | Aprovado para início |
| Responde | **Com o quê** o sistema é construído: linguagens, bibliotecas, versões, integração com Google, convenções |
| Depende de | `01-requisitos.md` (RNF-xx) |
| Alimenta | `03-arquitetura.md`, todas as tarefas de implementação |

> **Regra para IA:** não adicione dependências fora da tabela da seção 1 sem registrar uma decisão (ADR) na seção 9. Versões são faixas; respeite o limite superior.

---

## 1. Stack

| Camada | Tecnologia | Versão | Observação |
|---|---|---|---|
| Backend – linguagem | Python | 3.12+ | |
| Backend – framework HTTP | FastAPI | `>=0.115,<1` | OpenAPI automática em `/docs` |
| Backend – servidor | Uvicorn | `>=0.30` | `uvicorn[standard]` |
| Backend – validação/modelos | Pydantic v2 + pydantic-settings | `>=2.7,<3` / `>=2.3,<3` | |
| Google Sheets | gspread | `>=6.1,<7` | Wrapper da Sheets API v4 |
| Autenticação Google | google-auth | `>=2.30,<3` | Service account |
| Testes backend | pytest, httpx | `pytest>=8` | `httpx` para `TestClient` |
| Qualidade backend | ruff | `>=0.6` | lint + format |
| Frontend – framework | Angular | `^22.2` | **fixo na major 22** (ADR-10). Suporte ativo até 2027-06, LTS até 2028-06 |
| Frontend – linguagem | TypeScript | `>=6.0 <6.1` | Faixa exigida pelo Angular 22 |
| Frontend – UI | Angular Material + CDK | `^22` | Formulários, diálogos, tabela, snackbar |
| Frontend – fontes | @fontsource/roboto + material-symbols | `^5.3` / `^0.47` | Roboto (só o subconjunto `latin`) e Material Symbols Outlined servidas pelo próprio app, sem Google Fonts (ADR-15) |
| Frontend – gráficos | chart.js | `^4` | Usado **diretamente**, via diretiva própria em `shared/grafico/` (ADR-11) — sem wrapper de terceiros |
| Frontend – testes | Vitest | padrão do Angular CLI 22 (`@angular/build:unit-test`) | Karma está descontinuado desde a v21 |
| Frontend – formatação | prettier | `^3.8` (vem com `ng new` na v22) | Formatador do frontend; `jsdom` acompanha o Vitest como ambiente de DOM (ADR-14) |
| Runtime frontend | Node.js | 24 LTS (aceito `^22.22.3`) | Faixa exigida pelo Angular 22 |
| SO do usuário | Windows | — | Comandos documentados em PowerShell |

### 1.1 Dependências do backend

`backend/requirements.txt`
```text
fastapi>=0.115,<1
uvicorn[standard]>=0.30
pydantic>=2.7,<3
pydantic-settings>=2.3,<3
gspread>=6.1,<7
google-auth>=2.30,<3
```

`backend/requirements-dev.txt`
```text
-r requirements.txt
pytest>=8
httpx>=0.27
ruff>=0.6
```

---

## 2. Ambiente de desenvolvimento

```powershell
# Backend (a partir de ./backend)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env          # preencher SPREADSHEET_ID
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pytest                          # testes (integração com planilha real fica desligada por padrão)
ruff check . ; ruff format .

# Frontend (a partir de ./frontend)
npm install
npm start                       # ng serve com proxy para o backend → http://localhost:4200
npm test                        # ng test
npm run build                   # ng build
```

---

## 3. Backend (Python)

- **FastAPI** expõe uma API REST JSON sob o prefixo `/api` (contrato em `03-arquitetura.md` §6).
- **Pydantic v2** para modelos de entrada/saída e para configuração (`pydantic-settings`, lendo `backend/.env`).
- **Dinheiro:** `decimal.Decimal` em todo o domínio, sempre quantizado em 2 casas (`ROUND_HALF_UP` só onde a regra pedir; parcelas seguem RN-07). Na borda:
  - JSON: serializar como **número** com 2 casas. Pydantic v2 serializa `Decimal` como *string* por padrão — usar um tipo anotado único do projeto:
    ```python
    Dinheiro = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2),
                         PlainSerializer(float, return_type=float, when_used="json")]
    ```
  - Planilha: gravar como número (`float(valor)`), ler e converter com `Decimal(str(round(x, 2)))`.
  - Totais e saldo (que podem ser zero ou negativos) usam o tipo irmão `Montante` (`domain/dinheiro.py`): mesmo `Decimal` de 2 casas e mesma saída como número, sem o `> 0` do `Dinheiro` (RN-13).
- **Datas:** `datetime.date` no domínio; ISO 8601 (`YYYY-MM-DD`) no JSON e na planilha. Mês de referência como string `YYYY-MM`.
- **IDs:** `uuid4().hex` para lançamentos, parcelamentos e recorrências; *slug* imutável para categorias (ex.: `alimentacao`), ver `03-arquitetura.md` §5.
- **Servidor** escuta apenas em `127.0.0.1` (RNF-05). CORS liberado somente para `http://localhost:4200`.
- **Logs:** módulo `logging` padrão, nível `INFO`; nunca logar conteúdo de credenciais.

---

## 4. Frontend (Angular 22)

Padrões obrigatórios (estilo "Angular moderno", padrão do CLI na v22):

- **Zoneless:** projeto sem `zone.js` (padrão para projetos novos desde a v21). A detecção de mudanças depende de signals, eventos de template e `async` pipe — não dependa de `setTimeout`/callbacks externos para atualizar a tela; atualize um signal.
- **Componentes standalone** (sem `NgModule`).
- **Nomes de arquivo:** style guide **2025** (padrão de `ng new` na v22) — sem sufixo `.component` (`app.ts`, classe `App`); sufixos de papel mantidos (`*.store.ts`, `*.interceptor.ts`, `*.directive.ts`, `*.dialog.ts`). Ver ADR-13.
- **Signals** para estado local e de tela (`signal`, `computed`, `effect` com parcimônia); `input()`/`output()` em vez de decorators.
- **Novo control flow** (`@if`, `@for`, `@switch`) — não usar `*ngIf`/`*ngFor`.
- **`inject()`** em vez de injeção por construtor.
- **HttpClient** via `provideHttpClient(withInterceptors([...]))`; interceptors funcionais.
- **Rotas lazy** por feature (`loadComponent` / `loadChildren`).
- **Formulários reativos tipados** (`FormGroup<...>`, `NonNullableFormBuilder`). Não usar Signal Forms enquanto a API estiver marcada como experimental.
- **APIs instáveis:** não usar nada marcado como *experimental* ou *developer preview* na documentação da v22.
- **Change detection:** `ChangeDetectionStrategy.OnPush` em todos os componentes.
- **Locale:** `registerLocaleData(localePt)` + `{ provide: LOCALE_ID, useValue: 'pt-BR' }` + `{ provide: DEFAULT_CURRENCY_CODE, useValue: 'BRL' }`. Datas exibidas com `DatePipe` (`dd/MM/yyyy`), valores com `CurrencyPipe`.
- **Datas no Material:** `provideNativeDateAdapter()` + `MAT_DATE_LOCALE = 'pt-BR'`.
- **Gráficos:** diretiva standalone própria `GraficoDirective` (`shared/grafico/grafico.directive.ts`) aplicada a um `<canvas>`:
  - entradas via `input()`: `tipo` (`'doughnut' | 'bar' | 'line'`), `dados` (`ChartData`, ou uma função `(cores do tema) => ChartData` quando as séries precisam de cores do tema diferentes entre si — reavaliada na troca claro/escuro), `opcoes` (`ChartOptions`, opcional);
  - cria o `Chart` em `afterNextRender`, atualiza com `chart.update()` via `effect` quando as entradas mudam e chama `chart.destroy()` no `DestroyRef`;
  - registra apenas os componentes do Chart.js usados (controllers/elementos/escalas de rosca, barra e linha + `Tooltip` e `Legend`) em `grafico.config.ts`, para manter o bundle pequeno;
  - padrões globais pt-BR (formatação `R$` em tooltips/eixos) ficam no mesmo arquivo de configuração.
- **Proxy de desenvolvimento:** `frontend/proxy.conf.json` redireciona `/api` → `http://127.0.0.1:8000`, então o frontend sempre chama URLs relativas (`/api/...`).
- **O frontend não calcula totais.** Somatórios vêm prontos do backend (RN-16); o front só formata.

---

## 5. Integração com Google Sheets

### 5.1 Tipo de credencial

`credentials.json` na raiz do projeto é uma chave de **service account** (conta de serviço) do Google Cloud, com as APIs **Google Sheets API** e **Google Drive API** ativadas. Uma service account é um "usuário robô" com e-mail próprio (campo `client_email` do JSON).

**Consequência importante:** a service account **não enxerga** as planilhas do usuário até que ele as compartilhe com ela.

### 5.2 Preparação única (feita pelo usuário)

1. Criar uma planilha Google vazia na própria conta (ex.: "Planilha Financeira").
2. Copiar o `client_email` do `credentials.json` e **compartilhar a planilha com esse e-mail como Editor**.
3. Copiar o **ID da planilha** da URL: `https://docs.google.com/spreadsheets/d/<ID>/edit` e colocar em `SPREADSHEET_ID` no `backend/.env`.
4. Iniciar o backend: a estrutura de abas é criada automaticamente (REQ-15).

> Abrir por **ID** (`open_by_key`) em vez de por **nome** (`open`): nomes não são únicos e a busca por nome depende da Drive API; o ID é estável.

### 5.3 Código de referência (corrigido)

O exemplo fornecido tem dois problemas que **não devem ser copiados**: os escopos estão truncados (`"https://googleapis.com"` não é um escopo válido) e o método correto é `from_service_account_file` (não `from_service_file`).

```python
import gspread
from google.oauth2.service_account import Credentials

ESCOPOS = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

credenciais = Credentials.from_service_account_file("credentials.json", scopes=ESCOPOS)
cliente = gspread.authorize(credenciais)

planilha = cliente.open_by_key(SPREADSHEET_ID)       # preferir ID a nome
aba = planilha.worksheet("Lancamentos")

linhas = aba.get_all_values(value_render_option=gspread.utils.ValueRenderOption.unformatted)
aba.append_rows([[...]], value_input_option=gspread.utils.ValueInputOption.raw)
```

Toda chamada ao gspread fica encapsulada em `backend/app/infra/` (ver arquitetura); nenhum outro módulo importa `gspread`.

### 5.4 Opções de leitura e escrita

| Operação | Opção | Motivo |
|---|---|---|
| Escrita | `value_input_option = RAW` | Evita que uma descrição começando com `=` vire fórmula (injeção de fórmula) e que o Google reinterprete datas/números conforme o locale da planilha. |
| Inserção (`append_rows`) | `insert_data_option = INSERT_ROWS` | O padrão da API (`OVERWRITE`) escreve nas linhas logo após a "tabela" detectada; se o usuário deixou uma linha em branco no meio da aba, o append pode cair ali e **sobrescrever** as linhas de baixo. `INSERT_ROWS` insere linhas novas e nunca apaga dado. |
| Leitura | `value_render_option = UNFORMATTED_VALUE` | Números voltam como números (não "R$ 1.234,56"), booleanos como booleanos. |
| Datas | texto ISO `YYYY-MM-DD` | Legível para humanos, ordenável, independente de locale. |
| Chamadas gspread | sempre com **argumentos nomeados** | gspread 6 mudou a ordem de parâmetros de `update()`; nomeados evitam erro silencioso. |

### 5.5 Cotas e desempenho

Limites da Sheets API: **60 requisições de leitura e 60 de escrita por minuto por usuário por projeto** (300/min por projeto). Estouro retorna **HTTP 429**. Estratégia:

- **Ler a aba inteira em uma chamada** e filtrar/agregar em memória (volume pessoal cabe folgado).
- **Cache em memória por aba** com TTL de 30 s, invalidado a cada escrita naquela aba. Endpoint/ação "recarregar" força invalidação (edições manuais — RN-14).
- **Escritas em lote:** parcelamentos e geração de recorrências usam uma única chamada `append_rows`.
- **Retry com backoff exponencial truncado** para 429 e 5xx: até 4 tentativas, espera `min(2^n + aleatório(0–1 s), 16 s)`.
- Erro persistente → exceção de domínio `PlanilhaIndisponivel` → HTTP 503 (REQ-16).

### 5.6 Mapeamento de erros do Google

> **403 tem duas causas distintas.** Antes de concluir "planilha não compartilhada", inspecione o motivo dentro do `APIError`: se for `SERVICE_DISABLED`/`accessNotConfigured`, o problema é a API desativada no projeto, não o compartilhamento. Mensagem errada aqui manda o usuário para o lugar errado na configuração inicial.

| Situação | Detecção | Exceção de domínio | HTTP | Mensagem ao usuário |
|---|---|---|---|---|
| `credentials.json` ausente/inválido | `FileNotFoundError` / `ValueError` na carga | `CredenciaisInvalidas` | 503 | "Arquivo de credenciais não encontrado ou inválido." |
| Planilha não compartilhada | `gspread.exceptions.APIError` 403 | `SemPermissaoPlanilha` | 503 | "Compartilhe a planilha com <client_email> como Editor." |
| Google Sheets API desativada no projeto | `APIError` 403 com `reason` em {`SERVICE_DISABLED`, `accessNotConfigured`} | `ApiSheetsDesabilitada` | 503 | "Ative a Google Sheets API no projeto do Google Cloud e tente novamente." |
| ID inexistente | `SpreadsheetNotFound` / 404 | `PlanilhaNaoEncontrada` | 503 | "Planilha não encontrada. Confira SPREADSHEET_ID." |
| Cota / instabilidade | 429 / 5xx após retries | `PlanilhaIndisponivel` | 503 | "Google Sheets indisponível no momento. Tente novamente." |
| Sem internet | `requests.ConnectionError`/`TransportError` | `PlanilhaIndisponivel` | 503 | idem |
| Cabeçalho da planilha divergente, ou `versao_schema` maior que a do app | Comparação feita pelo `bootstrap` (`03` §5) | `SchemaPlanilhaInvalido` | 503 | "A estrutura da planilha não corresponde ao esperado: <aba>, <problema>." |

---

## 6. Configuração

`backend/.env` (não versionado) — modelo em `backend/.env.example` (versionado):

| Variável | Obrigatória | Padrão | Descrição |
|---|---|---|---|
| `SPREADSHEET_ID` | sim | — | ID da planilha de produção |
| `GOOGLE_CREDENTIALS_PATH` | não | `../credentials.json` | Caminho da chave da service account |
| `CACHE_TTL_SEGUNDOS` | não | `30` | TTL do cache de abas |
| `CORS_ORIGINS` | não | `http://localhost:4200` | Origens permitidas |
| `SPREADSHEET_ID_TESTE` | não | — | Planilha separada para testes de integração |

**Arquivos que nunca podem ser versionados:** `credentials.json`, `backend/.env`, `.venv/`, `node_modules/`, `dist/`, `__pycache__/`, `.pytest_cache/`, `.angular/`.

---

## 7. Convenções de código

| Tema | Convenção |
|---|---|
| Idioma do domínio | Identificadores de domínio **em português, sem acento**, iguais ao glossário: `Lancamento`, `Categoria`, `Recorrencia`, `forma_pagamento`, `mes_referencia`. |
| Termos técnicos | Podem ficar em inglês quando consagrados: `router`, `service`, `repository`, `interceptor`. |
| Python | PEP 8 via ruff; *type hints* obrigatórios; funções de serviço puras sempre que possível; sem lógica de negócio em routers. |
| TypeScript | `strict: true`; sem `any`; interfaces dos contratos em `core/models/` espelhando o JSON da API (**snake_case**, sem mapeamento). |
| JSON da API | `snake_case`; datas ISO; valores monetários como número com 2 casas; enums em MAIÚSCULAS (`GASTO`, `PIX`). |
| Commits | `T-xxx: <descrição no imperativo>` (ex.: `T-015: cria endpoint POST /api/lancamentos`). |
| Branches (opcional) | `feat/F-xx-nome-curto`. |
| Rastreio em testes | Nome/docstring do teste cita a regra: `test_parcelas_centavos_na_primeira__RN_07`. |

---

## 8. Estratégia de testes

| Nível | Onde | O que cobre | Execução |
|---|---|---|---|
| Unitário backend | `backend/tests/unit/` | Serviços e regras (RN-xx) usando **repositórios em memória** | `pytest` (sempre) |
| API backend | `backend/tests/api/` | Endpoints com `TestClient` + `dependency_overrides` para repositórios em memória; formato de erro | `pytest` (sempre) |
| Integração | `backend/tests/integracao/` | App real (`criar_app` + `TestClient`) contra `SPREADSHEET_ID_TESTE`: bootstrap de planilha vazia (apaga e recria as abas do app **só na planilha de teste**), lançamentos, categorias, parcelamento, recorrências, edição manual e desempenho com 5.000 lançamentos (F-15, T-032/T-034); linhas marcadas `teste-integracao-`/`teste-desempenho-` apagadas no início e no fim | `pytest -m integracao` (manual; pulado sem a variável) |
| Unitário frontend | `*.spec.ts` (Vitest) | Services (com `HttpTestingController`), formulários, pipes/utilitários, `GraficoDirective` | `npm test` (`ng test`, execução única com `--watch=false`) |
| Ponta a ponta | roteiro manual em `SPECS/features/F-15-*.md` | Fluxos principais com a planilha real de teste | manual |

Definição de pronto de qualquer tarefa: testes do nível correspondente passando + `ruff check` limpo (backend) + `ng build` sem erros (frontend).

Padrões da suíte do backend (`backend/pyproject.toml`, definidos em T-002): `addopts = "-m 'not integracao'"` — um `pytest` simples **nunca** toca a planilha real, mesmo com `SPREADSHEET_ID_TESTE` definida (para rodar, `pytest -m integracao`, que sobrescreve o padrão); além disso o `conftest` **pula** os testes `integracao` quando a variável não existe — ela é lida do terminal ou, sem ele, do `backend/.env` (T-034) —, uma trava encerra a suíte antes de abrir a planilha se `SPREADSHEET_ID_TESTE` for igual ao `SPREADSHEET_ID` do app, e `filterwarnings` transforma marcador não declarado em falha.

Padrões da suíte do frontend (T-011/T-014): specs que abrem diálogo, menu ou datepicker do Material usam `provideMaterialParaTestes()` (`frontend/src/testing/material.ts`) — o jsdom não dispara fim de animação CSS e dá tamanho zero a todo elemento. Dados de exemplo compartilhados ficam em `frontend/src/testing/` (ex.: `umaCategoria`).

---

## 9. Registro de decisões técnicas (ADR resumido)

| ID | Decisão | Alternativas consideradas | Motivo | Data |
|---|---|---|---|---|
| ADR-01 | FastAPI no backend | Flask, Django | Tipagem com Pydantic, OpenAPI automática, leve | 2026-09-29 |
| ADR-02 | Service account + gspread | OAuth do usuário | Sem fluxo de login; uso local de um único usuário | 2026-09-29 |
| ADR-03 | Abrir planilha por ID | Por nome | Estável, único, não depende da Drive API | 2026-09-29 |
| ADR-04 | Escrita RAW, leitura UNFORMATTED, datas ISO texto | USER_ENTERED | Evita injeção de fórmula e dependência de locale | 2026-09-29 |
| ADR-05 | Cache por aba com TTL + invalidação na escrita | Sem cache; banco local | Respeita cotas (60 req/min) sem criar 2ª fonte de dados | 2026-09-29 |
| ADR-06 | Angular Material (mesma major do Angular — hoje 22) | PrimeNG, Tailwind puro | Oficial, acompanha a versão do framework, cobre diálogos/tabela/form | 2026-09-29 |
| ADR-07 | ~~ng2-charts 8 + Chart.js 4~~ — **Substituída por ADR-11** | ngx-echarts, ApexCharts | Linha 8.x era a do Angular 19 | 2026-09-29 |
| ADR-08 | Totais calculados no backend | Somar no front | Precisão decimal (RN-16) e fonte única de regra | 2026-09-29 |
| ADR-09 | JSON em snake_case espelhado no TS | camelCase com mapeamento | Menos código de conversão; uma única nomenclatura | 2026-09-29 |
| ADR-10 | **Angular 22** (substitui a escolha inicial de Angular 19), com os padrões do CLI 22: zoneless, Vitest, TypeScript 6.0, Node 24 | Angular 19 (sem suporte desde 2026-05); Angular 21 (só LTS, fim em 2027-06) | Versão ativa com maior janela de suporte (ativa até 2027-06, LTS até 2028-06) | 2026-09-29 |
| ADR-11 | Chart.js 4 usado diretamente com diretiva própria (`GraficoDirective`) | ng2-charts (sem release para Angular 22 e manutenção incerta); ngx-echarts | Remove dependência de wrapper que atrasa a cada major do Angular; a diretiva tem ~40 linhas e fica sob nosso controle | 2026-09-29 |
| ADR-12 | Aplicação criada por fábrica (`criar_app()`) e `Settings` obtido preguiçosamente por `obter_settings()` com `lru_cache`; `app = criar_app()` no fim de `main.py` para o uvicorn | Instanciar `Settings` no import do módulo; ler `.env` direto em cada módulo | Importar `app.main` deixa de exigir um `.env` preenchido, então `pytest` roda em qualquer cópia do repo; a fábrica permite criar a aplicação com configuração de teste, o que T-005 (lifespan) e os testes de API reaproveitam | 2026-09-29 |
| ADR-13 | Nomes de arquivo do frontend no style guide **2025** (`app.ts`, classe `App`) | Style guide 2016 (`app.component.ts`), que era o que `03` §3 descrevia | É o padrão do CLI 22 e o que `ng generate` usará daqui para frente; manter o estilo antigo exigiria um flag em toda geração e divergiria da documentação do Angular | 2026-09-29 |
| ADR-14 | Manter o **prettier** que o `ng new` da v22 instala como formatador do frontend (com o `.prettierrc` gerado) | Remover a dependência e não formatar; adotar outro formatador | É o padrão do CLI 22 e `02` §4 manda seguir os padrões do CLI; remover exigiria editar o projeto gerado a cada atualização. **Não** entra na Definição de Pronto: o portão do frontend continua sendo `npm test` + `npm run build` | 2026-09-29 |

| ADR-15 | Servir as fontes **pelo próprio app**: pacotes npm `@fontsource/roboto` (arquivos `latin-300/400/500.css`) e `material-symbols` (`outlined.css`), na lista `styles` do `angular.json`; nada de `fonts.googleapis.com` no `index.html` | Manter o Google Fonts do `ng add`; copiar os arquivos de fonte para `src/` à mão | App 100% local (RNF-01): sem internet, os ícones apareciam como texto ("more_vert"), justamente no caso "sem internet" de REQ-16. Pacotes mantidos pelo npm em vez de binários copiados. Custo: +1,2 kB no CSS inicial (só o subconjunto latino do Roboto; todos os subconjuntos davam +15 kB) e ~3,9 MB da fonte de ícones, carregada do disco local e fora do pacote JS (F-14 Q5, T-031) | 2026-10-01 |

Novas decisões: acrescente uma linha com o próximo ID. Decisões substituídas não são apagadas — marque "Substituída por ADR-xx".

---

## 10. Riscos técnicos

| Risco | Impacto | Mitigação |
|---|---|---|
| Angular 22 sai do suporte ativo em 2027-06 e do LTS em 2028-06. | Baixo | Planejar atualização de major (`ng update`) durante a fase LTS, como nova feature no roadmap via `/mudanca-de-requisito`. |
| Diretiva de gráficos própria precisa acompanhar mudanças do Chart.js. | Baixo | Escopo mínimo (criar/atualizar/destruir); teste unitário da diretiva; Chart.js fixado na major 4. |
| Vazamento da chave `credentials.json` (ex.: commit acidental). | Alto | `.gitignore` é a 1ª tarefa (T-001); `.claude/settings.json` nega `Read`/`Edit`/`Write` sobre o arquivo e também os leitores de terminal mais comuns (`cat`, `head`, `tail`, `less`, `more`, `strings`, comandos PowerShell que o citem) — defesa em profundidade, não hermética, pois qualquer interpretador leria o arquivo por outro caminho; a garantia real é o `.gitignore` + regra 1 do `CLAUDE.md`. Se vazar, revogar a chave no Google Cloud e gerar outra. |
| Edição manual na planilha quebra formato. | Médio | Linhas inválidas ignoradas e contadas (CA-16.3); localizar linha sempre por `id`, nunca por posição guardada. |
| Cota da API (429). | Baixo | Cache + lote + backoff (§5.5). |

---

## Histórico de alterações

| Data | Versão | Alteração |
|---|---|---|
| 2026-09-29 | 1.0 | Versão inicial. |
| 2026-09-29 | 1.1 | Frontend migrado de Angular 19 para **Angular 22** (ADR-10): TypeScript 6.0, Node 24, zoneless, Vitest. Gráficos com Chart.js direto via diretiva própria (ADR-11, substitui ADR-07). Riscos atualizados. |
| 2026-09-29 | 1.2 | §10: mitigação do vazamento de credencial detalhada (T-001) — `deny` de terminal acrescentado a `.claude/settings.json`, com o alcance e os limites explicitados. |
| 2026-09-29 | 1.3 | ADR-12 (fábrica `criar_app()` + `Settings` preguiçoso) e §8: padrões da suíte do backend definidos em T-002. |
| 2026-09-29 | 1.4 | ADR-13 e §4: convenção de nomes de arquivo do frontend (style guide 2025). |
| 2026-09-29 | 1.5 | ADR-14 e §1: prettier (e `jsdom`) registrados como dependências de desenvolvimento trazidas pelo CLI 22 em T-003. |
| 2026-09-29 | 1.6 | §5.6: 403 desambiguado — nova exceção `ApiSheetsDesabilitada` para Sheets API desativada no projeto (decidido em F-02). |
| 2026-09-29 | 1.7 | §5.6: `SchemaPlanilhaInvalido` para cabeçalho divergente e `versao_schema` à frente do app (decidido em F-03). |
| 2026-09-30 | 1.8 | §5.4: inserções com `INSERT_ROWS`, para um append nunca sobrescrever linhas abaixo de uma linha em branco (T-009). |
| 2026-09-30 | 1.9 | §8: padrões da suíte do frontend (`src/testing/`, `provideMaterialParaTestes`) (T-014). |
| 2026-09-30 | 1.10 | §3: tipo `Montante` para totais e saldo (T-017). |
| 2026-10-01 | 1.11 | §4: `dados` da `GraficoDirective` também como função das cores do tema (séries com cores do tema diferentes entre si; F-11, T-025). |
| 2026-10-01 | 1.12 | §1 e §9: fontes servidas pelo próprio app — `@fontsource/roboto` e `material-symbols` (ADR-15; F-14 Q5, T-031). |
| 2026-10-02 | 1.13 | §8: a suíte de integração também mede desempenho com 5.000 lançamentos (`test_desempenho.py`, T-032). Nenhuma dependência nova. |
| 2026-10-02 | 1.14 | §8: suíte de integração completa pelo app real, `SPREADSHEET_ID_TESTE` também do `backend/.env`, trava contra a planilha do app e limpeza das linhas marcadas (T-034; F-15 Q5, Q6). Nenhuma dependência nova (`pydantic-settings` já usado). |
