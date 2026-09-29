# Planilha Financeira

Controle financeiro pessoal que roda **no seu computador** e guarda tudo **na sua planilha Google**. Você registra gastos e receitas; o app mostra somatórios, gráficos do mês e o histórico. Não há login, não há servidor na nuvem e não há segundo banco de dados: a planilha é a única fonte dos seus dados.

Backend em Python/FastAPI, frontend em Angular 22. O acesso à planilha usa uma **conta de serviço** do Google — um "usuário robô" com e-mail próprio, que só vê as planilhas que você compartilhar com ele.

> **Estado atual:** em construção (marco M0). Hoje funcionam a conexão com a planilha e `GET /api/health`; a interface ainda mostra a página padrão do Angular. O progresso tarefa por tarefa está em [`SPECS/05-acompanhamento.md`](SPECS/05-acompanhamento.md).

---

## 1. Pré-requisitos

| O quê | Versão | Observação |
|---|---|---|
| Python | 3.12 ou superior | testado em 3.13.7 |
| Node.js | 24 LTS | aceito também `^22.22.3` |
| Conta Google | — | onde a planilha vive |
| Windows | — | os comandos abaixo são PowerShell |

Confira o que você tem:

```powershell
python --version ; node -v ; npm -v
```

---

## 2. Preparação única

Você faz isso **uma vez**. Depois, só rodar o app.

### 2.1 Criar a planilha

Crie uma planilha Google **vazia** na sua conta (ex.: "Planilha Financeira"). Não precisa criar abas nem cabeçalhos: o app monta a estrutura sozinho na primeira execução.

### 2.2 Obter o `credentials.json`

Se você já tem o arquivo na raiz do projeto, pule para 2.3. Para gerar um novo:

1. No [Google Cloud Console](https://console.cloud.google.com/), crie (ou escolha) um projeto.
2. Ative **duas** APIs no projeto: **Google Sheets API** e **Google Drive API**.
3. Em *IAM e administrador → Contas de serviço*, crie uma conta de serviço.
4. Nessa conta, aba *Chaves*, **Adicionar chave → Criar nova chave → JSON**.
5. Salve o arquivo baixado como **`credentials.json`** na raiz deste projeto.

O `.gitignore` já impede que esse arquivo entre no Git. Ele é a chave da sua conta de serviço: se algum dia vazar, revogue a chave no Google Cloud e gere outra.

### 2.3 Compartilhar a planilha com a conta de serviço

A conta de serviço **não enxerga** nenhuma planilha sua até você compartilhar. Precisa do e-mail dela, que termina em `.iam.gserviceaccount.com`.

**Jeito mais fácil:** siga até o passo 2.5, suba o backend e abra <http://127.0.0.1:8000/api/health>. Se a planilha ainda não estiver compartilhada, a resposta traz o e-mail exato para você copiar:

```json
{ "status": "degradado",
  "planilha": { "ok": false, "titulo": null,
    "erro": { "codigo": "SEM_PERMISSAO_PLANILHA",
              "mensagem": "Compartilhe a planilha com ...@....iam.gserviceaccount.com como Editor." } } }
```

**Jeito manual:** abra o `credentials.json` e copie o valor do campo `client_email`.

Com o e-mail em mãos: na planilha, **Compartilhar** → cole o e-mail → permissão **Editor** → enviar.

> Precisa ser **Editor**, não Leitor. Como Leitor o app consegue abrir a planilha, mas falha na primeira gravação.

### 2.4 Copiar o ID da planilha

O ID está na URL, entre `/d/` e `/edit`:

```
https://docs.google.com/spreadsheets/d/1a2B3cD4eF5gH6iJ7kL8mN9oP0qR/edit#gid=0
                                      ├────────── isto ──────────┤
```

Copie **só** esse trecho. Colar a URL inteira não funciona.

### 2.5 Configurar o `.env`

```powershell
cd backend
copy .env.example .env
```

Abra `backend/.env` e preencha `SPREADSHEET_ID` com o ID do passo 2.4. As demais variáveis têm padrão e podem ficar como estão:

| Variável | Obrigatória | Padrão | O que é |
|---|---|---|---|
| `SPREADSHEET_ID` | **sim** | — | ID da sua planilha |
| `GOOGLE_CREDENTIALS_PATH` | não | `../credentials.json` | caminho da chave, **relativo à pasta `backend/`** |
| `CACHE_TTL_SEGUNDOS` | não | `30` | validade do cache de leitura |
| `CORS_ORIGINS` | não | `http://localhost:4200` | origens aceitas pela API |
| `SPREADSHEET_ID_TESTE` | não | — | planilha separada, só para testes de integração |

O `.env` não é versionado. O `.env.example` é.

---

## 3. Como rodar

### Backend (pasta `backend/`)

```powershell
cd backend
python -m venv .venv                      # só na primeira vez
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt       # só na primeira vez
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API: <http://127.0.0.1:8000>
- Documentação interativa: <http://127.0.0.1:8000/docs>
- Estado da conexão: <http://127.0.0.1:8000/api/health>

### Frontend (pasta `frontend/`)

```powershell
cd frontend
npm install                               # só na primeira vez
npm start
```

Abre em <http://localhost:4200>. As chamadas a `/api` são encaminhadas ao backend pelo proxy, então o backend precisa estar rodando.

---

## 4. Testes e verificações

```powershell
# backend (em ./backend, com a .venv ativa)
pytest                                    # unitários e de API; não acessa a rede
ruff check . ; ruff format .
pytest -m integracao                      # só com SPREADSHEET_ID_TESTE definido

# frontend (em ./frontend)
npm test
npm run build
```

Os testes de integração ficam de fora da execução normal de propósito: eles escrevem numa planilha de verdade. Use **uma planilha separada** em `SPREADSHEET_ID_TESTE`, nunca a que guarda seus dados.

---

## 5. Se algo der errado

Toda falha de acesso à planilha aparece com um código e uma mensagem — no `GET /api/health` e, mais tarde, no banner da interface.

| Código | Mensagem | O que fazer |
|---|---|---|
| `CREDENCIAIS_INVALIDAS` | Arquivo de credenciais não encontrado ou inválido. | Confirme que `credentials.json` está na raiz e que `GOOGLE_CREDENTIALS_PATH` aponta para ele — o padrão `../credentials.json` é relativo à pasta `backend/`, de onde você roda o `uvicorn`. |
| `SEM_PERMISSAO_PLANILHA` | Compartilhe a planilha com `<e-mail>` como Editor. | Passo 2.3. O e-mail vem na própria mensagem. Confirme que a permissão é **Editor**. |
| `API_SHEETS_DESABILITADA` | Ative a Google Sheets API no projeto do Google Cloud e tente novamente. | Passo 2.2, item 2. É um 403 de causa diferente do anterior: aqui o problema é o projeto, não o compartilhamento. |
| `PLANILHA_NAO_ENCONTRADA` | Planilha não encontrada. Confira SPREADSHEET_ID. | Passo 2.4. Provavelmente foi colada a URL inteira, ou o nome da planilha, em vez do ID. |
| `PLANILHA_INDISPONIVEL` | Google Sheets indisponível no momento. Tente novamente. | Falha temporária ou falta de internet. O app já tenta de novo automaticamente algumas vezes; chamar `/api/health` outra vez força uma nova tentativa, sem reiniciar nada. |

Outras situações:

- **O servidor sobe, mas a planilha está inacessível.** É proposital: o backend não morre por causa disso. Corrija a causa e chame `/api/health` de novo.
- **`Configuração inválida do backend: verifique SPREADSHEET_ID`** ao subir o uvicorn: falta o `backend/.env` ou a variável está vazia (passo 2.5).
- **Porta 8000 ou 4200 ocupada:** troque com `--port` no uvicorn (e ajuste `frontend/proxy.conf.json`) ou `npm start -- --port 4300`.
- **Erro de ativação da `.venv` no PowerShell:** rode `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` na mesma janela.

---

## 6. Estrutura e documentação

```text
PlanilhaFinanceira/
├── SPECS/            # fonte da verdade: requisitos, arquitetura, roadmap, acompanhamento
├── backend/          # FastAPI + gspread
├── frontend/         # Angular 22
├── scripts/          # scripts de execução (em construção)
└── credentials.json  # sua chave da conta de serviço — nunca versionada
```

Este projeto segue **Spec-Driven Development**: as especificações em [`SPECS/`](SPECS/) descrevem o comportamento antes do código, e o código as cumpre. Comece por [`SPECS/README.md`](SPECS/README.md). Para saber o que já está pronto, veja [`SPECS/05-acompanhamento.md`](SPECS/05-acompanhamento.md).

---

## 7. Segurança

- `credentials.json` e `backend/.env` **nunca** são versionados (garantido pelo `.gitignore`).
- Nenhum campo da credencial vai para log, resposta da API ou navegador. A única exceção é o `client_email`, que aparece na mensagem de "compartilhe a planilha" porque é o que torna o erro acionável — a chave privada nunca sai do arquivo.
- O backend escuta apenas em `127.0.0.1`: nada na sua rede local alcança a API.
- A API aceita chamadas só de `http://localhost:4200`, a origem do frontend em desenvolvimento.
