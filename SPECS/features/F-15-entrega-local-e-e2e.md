# F-15 — Entrega local e verificação ponta a ponta

| Campo | Valor |
|---|---|
| Feature | F-15 |
| Marco | M4 |
| Status | Aprovada |
| Requisitos | RNF-01, RNF-08; verificação de todos os REQ (REQ-01 a REQ-16, 44 CA) |
| Regras | RN-01 a RN-16 (verificação — RNF-08); RNF-03 a RNF-07 (conferência no roteiro) |
| Depende de | F-14 (**Concluída**) |
| Tarefas | T-033, T-034, T-035 |
| Atualizado em | 2026-10-02 |

> **IDs de critério:** herdados de `01` mantêm o ID original. Os refinados usam **`CA-F15.y`**.
>
> Marcas **(Qn)** apontam a decisão de §11 que fixou aquele trecho.

---

## 1. Objetivo

Deixar o aplicativo pronto para o uso diário: subir tudo com um comando (RNF-01), provar contra uma planilha do Google de verdade que os fluxos principais funcionam, e verificar requisito por requisito, num roteiro registrado, que a versão 1 cumpre o que `01` promete.

---

## 2. Escopo

**Inclui**
- **T-033 (DOC) — scripts de execução** em `scripts/` (`03` §3): `start-backend.ps1`, `start-frontend.ps1` e `start.ps1` (sobe os dois e abre o navegador).
- **T-034 (BE) — suíte de integração completa** em `backend/tests/integracao/` contra `SPREADSHEET_ID_TESTE`: bootstrap, CRUD, parcelamento e sincronização (`04` T-034), além dos testes que já existem (`test_planilha_real.py`, `test_desempenho.py`).
- **T-035 (DOC) — roteiro E2E** (§3.3) cobrindo **todos** os 44 CA de `01` e as conferências de RNF; execução e registro do resultado nesta spec; **`README.md` final** (§3.4); **matriz RN → teste** (RNF-08, §3.5).
- **Pendências herdadas** que só fecham com planilha real ou navegador:
  - CA-F02.13 — seguir o README com a planilha real (F-02);
  - CA-15.1 / CA-15.2 e CA-F14.16 — `pytest -m integracao` (F-03, F-14);
  - conferência visual do botão "Recarregar dados" e da faixa de linhas ignoradas, que não foi feita em T-032 (F-14 §10), e repetição da conferência visual de T-031 com a planilha real.

**Não inclui** (e onde será tratado)
- Funcionalidade nova ou mudança de comportamento — fora da versão 1 (`01` §6). O que o roteiro achar de errado segue **(Q8)**.
- Empacotamento (instalador, executável, Docker), serviço do Windows ou atalho na área de trabalho — não pedidos em `01`; se o usuário quiser, viram requisito via `/mudanca-de-requisito`.
- Servir o frontend compilado pelo FastAPI — mudaria `03` (estrutura, CORS) e exigiria ADR **(Q1)**.
- Hospedagem ou acesso de outra máquina — proibido por RNF-01/RNF-05.

---

## 3. Comportamento detalhado

### 3.1 Scripts de execução (T-033, RNF-01)

Todos em PowerShell (Windows, `02` §1), com caminhos relativos ao próprio script (`$PSScriptRoot`), para funcionarem a partir de qualquer pasta. Mensagens em pt-BR. Nenhum script lê, mostra ou copia `credentials.json` ou o conteúdo do `backend/.env` (RNF-05): no máximo verificam se o arquivo **existe**.

1. **`scripts/start-backend.ps1`**
   1. Confere o Python (`python --version` ≥ 3.12, `02` §1). Se faltar ou for antigo: "Python 3.12 ou superior não encontrado. Veja o README, seção 1." e sai com código ≠ 0.
   2. Se `backend/.venv` não existe, cria e instala `requirements.txt` **(Q3)**.
   3. Se `backend/.env` não existe: "Falta o arquivo backend/.env. Copie backend/.env.example e preencha SPREADSHEET_ID (README, seção 2.5)." e sai com código ≠ 0. O conteúdo não é validado aqui: SPREADSHEET_ID vazio já gera a mensagem do próprio backend, e problemas de credencial ou planilha aparecem no banner (`/api/health`).
   4. Sobe `uvicorn app.main:app --host 127.0.0.1 --port 8000`, **sem `--reload`** **(Q1)**, usando o Python da `.venv`, sem exigir que o usuário a ative.
2. **`scripts/start-frontend.ps1`**
   1. Confere o Node (24 LTS ou `^22.22.3`, `02` §1), com mensagem e saída ≠ 0 se faltar.
   2. Se `frontend/node_modules` não existe, roda `npm install` **(Q3)**.
   3. Sobe `npm start` (`ng serve` com o proxy `/api` → 8000; `http://localhost:4200`) **(Q1)**.
3. **`scripts/start.ps1`** **(Q2)**
   1. Se `http://127.0.0.1:8000/api/health` já responde e `http://localhost:4200` também, o app já está rodando: só abre o navegador e termina.
   2. Se a porta 8000 ou 4200 está ocupada por outro programa: "A porta 8000 está em uso por outro programa. Feche-o ou veja o README, seção 5." e sai sem subir nada.
   3. Abre **uma janela do PowerShell para cada parte**, com os títulos "Planilha Financeira — backend" e "Planilha Financeira — frontend", rodando os dois scripts acima. Os logs ficam visíveis, e fechar a janela (ou Ctrl+C nela) para aquela parte.
   4. Espera o `/api/health` responder (até 60 s) e depois `http://localhost:4200` (até 180 s, porque o primeiro `ng serve` compila tudo). Assim que o frontend responde, abre o navegador padrão em `http://localhost:4200`.
   5. Esgotado o tempo: "O backend (ou frontend) não respondeu em N s. Veja a janela dele para o erro." Nada é encerrado, para o usuário poder ler o log.
4. **Como executar:** `powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1` (documentado no README). Isso evita exigir uma mudança permanente da política de execução do Windows (configuração do sistema).

### 3.2 Suíte de integração (T-034)

1. **Onde e como:** `backend/tests/integracao/`, marcador `integracao` (`02` §8). Os testes passam pelo **app real** (`criar_app(Settings(...))` + `TestClient`), com a planilha de `SPREADSHEET_ID_TESTE` e a credencial de sempre (fixture `credencial_real`), como `test_desempenho.py`.
2. **De onde vem `SPREADSHEET_ID_TESTE` (Q5):** hoje o `conftest` só olha o ambiente do terminal, mas o `.env.example` e o resumo de `05` sugerem preencher a variável no `backend/.env`. O `conftest` passa a ler `SPREADSHEET_ID_TESTE` também do `backend/.env` (o `Settings` já tem o campo `spreadsheet_id_teste`); o terminal continua valendo e tem precedência.
3. **Trava de segurança (Q5):** se `SPREADSHEET_ID_TESTE` for igual ao `SPREADSHEET_ID` do `.env`, a suíte **falha logo no início** com "SPREADSHEET_ID_TESTE aponta para a mesma planilha do app. Use uma planilha separada." e nada é escrito.
4. **Isolamento e limpeza:** cada teste marca o que cria com `teste-integracao-<12 hex>` (na descrição ou no nome) e apaga no `finally`, mesmo se falhar: pela API quando há endpoint e, na aba, pela marca quando não há (recorrências não têm `DELETE` — `03` §6.1). A planilha de teste termina como começou, a menos da preparação de CA-15.1 **(Q6)**.
5. **Cenários** (um arquivo por grupo):

   | Arquivo | Cenário | Cobre |
   |---|---|---|
   | `test_planilha_real.py` (existe) | bootstrap idempotente + CRUD pelo repositório com `=SOMA(…)` como texto | CA-15.2, CA-F03.9, CA-F03.22 |
   | `test_bootstrap.py` **(Q6)** | apaga as 4 abas do app na planilha de teste (criando antes uma aba vazia de apoio, se preciso: o Google exige ao menos uma aba), sobe o app e confere abas, cabeçalhos e as 15 categorias de RN-15; sobe de novo e nada muda | CA-15.1, CA-15.2, RN-15 |
   | `test_lancamentos_e2e.py` | `POST` gasto e receita sem forma → aparecem no `GET` do mês e no resumo, centavo a centavo; `PUT` muda só a linha do `id` (outra linha marcada fica igual) e a troca de mês move o lançamento; `DELETE` remove a linha e os totais voltam | CA-01.2, CA-01.5, CA-02.2, CA-05.2, CA-05.3, CA-06.2, CA-12.1, RN-13, RN-16 |
   | `test_categorias_e2e.py` | criar, renomear (o lançamento antigo mostra o nome novo), duplicado sem acento/maiúscula → 409, excluir em uso → 409, desativar, excluir sem uso → 204 | CA-11.1 a CA-11.4, RN-12 |
   | `test_parcelamento_e2e.py` | R$ 1.000,00 em 3 a partir de 15/01 → 333,34 / 333,33 / 333,33 em três meses; compra em 31/01 em 2 → 28/02 ou 29/02; `DELETE /api/parcelamentos/{id}` remove todas, em qualquer mês | CA-07.1, CA-07.2, CA-08.2, RN-07, RN-08 |
   | `test_recorrencias_e2e.py` | recorrência ativa com início 2 meses antes do corrente → `sincronizar` gera 3; de novo → 0; excluir um gerado e sincronizar → 0; nada em mês futuro; pausar → 0; reativar no mês seguinte não gera o período pausado (verificado pelo `ultimo_mes_gerado`) | CA-10.1 a CA-10.4, RN-09 a RN-11 |
   | `test_edicao_manual_e2e.py` | grava direto na aba uma linha marcada com valor "abc" → `GET` traz `linhas_ignoradas` ≥ 1 e a linha fora dos totais; corrige na aba e `POST /api/sistema/recarregar` → a linha entra na hora | CA-16.3, RN-14 |
   | `test_desempenho.py` (existe) | 5.000 lançamentos, cada chamada < 3 s com o cache frio | CA-F14.16, RNF-04 |

6. **Execução:** `pytest -m integracao` (manual, `02` §8). Um `pytest` simples continua sem tocar a rede.

### 3.3 Roteiro E2E (T-035)

1. **Ambiente (Q7):** o app subido por `scripts/start.ps1`, com o backend apontando para a **planilha de teste**. `SPREADSHEET_ID` é definido no terminal como o ID de teste antes de subir, o que tem precedência sobre o `.env` (pydantic-settings). Assim a planilha real do usuário não recebe dados de teste. CA-15.1 usa a planilha de teste depois de apagar as abas do app **(Q6)**.
2. **Quem executa (Q7):** o Claude conduz no navegador automatizado (Claude in Chrome), em 1280 px e 360 px, tema claro e escuro, e registra cada item. O usuário confirma no final, olhando a planilha e as telas. Itens que dependem de ação no Google (compartilhamento, editar célula à mão) o Claude faz pelo app quando há caminho, ou pede ao usuário.
3. **Registro:** a tabela de §3.3.4 recebe "OK" ou "Falhou — <o que aconteceu>", com a data, e o resumo vai para §10. Um item que falhar segue **(Q8)**.
4. **Itens** (passos detalhados são refinados em T-035; o esperado é o do CA):

   | # | Verificação | Esperado | Resultado |
   |---|---|---|---|
   | CA-01.1 | Em cada uma das 5 telas, "Registrar gasto" | Formulário com a data de hoje | |
   | CA-01.2 | Gasto válido → Salvar | Linha nova na aba `Lancamentos`, diálogo fecha, aviso de sucesso | |
   | CA-01.3 | Salvar com descrição vazia; depois com valor 0 | Campo marcado, nada gravado na aba | |
   | CA-01.4 | Backend parado → Salvar | Erro mostrado, dados continuam no formulário | |
   | CA-01.5 | Depois de CA-01.2, abrir Lançamentos e Resumo do mês | Gasto listado e somado | |
   | CA-02.1 | "Registrar receita" → Categoria | Só categorias ativas de receita | |
   | CA-02.2 | Receita sem forma de pagamento → Salvar | Gravada | |
   | CA-03.1 | Mês com parcela e recorrente | Data, descrição, categoria, forma, valor, "k/N" ou marca de recorrência | |
   | CA-03.2 | Filtrar por tipo, categoria e forma | Totais = soma do que está visível (gastos e receitas separados) | |
   | CA-03.3 | Mês sem lançamentos | "Nenhum lançamento…" | |
   | CA-04.1 | Abrir o app → Resumo e Lançamentos | Mês corrente | |
   | CA-04.2 | Escolher outro mês e alternar Resumo ↔ Lançamentos | Mesmo mês | |
   | CA-05.1 | Editar um lançamento | Formulário com os dados atuais | |
   | CA-05.2 | Alterar a descrição → Salvar | Só aquela linha muda na aba | |
   | CA-05.3 | Mudar a data para o mês seguinte | Sai do mês atual e aparece no seguinte | |
   | CA-06.1 | Excluir | Confirmação com descrição e valor | |
   | CA-06.2 | Confirmar | Linha some da aba; totais recalculados | |
   | CA-07.1 | R$ 1.000,00 em 3 a partir de 15/01 | 333,34 / 333,33 / 333,33 em 15/01, 15/02, 15/03 | |
   | CA-07.2 | Compra em 31/01 em 2 | 2ª parcela em 28/02 (29/02 em ano bissexto) | |
   | CA-07.3 | Listar as parcelas | "k/N" e a descrição original | |
   | CA-08.1 | Editar uma parcela | Só ela muda | |
   | CA-08.2 | "Excluir parcelamento inteiro" | Todas somem, em todos os meses | |
   | CA-09.1 | Tela Recorrências | Estado e próximo mês de cada uma | |
   | CA-09.2 | Editar o valor de uma recorrência | Lançamentos já gerados mantêm o valor antigo; o próximo usa o novo | |
   | CA-10.1 | Recorrência ativa com início 2 meses atrás; recarregar a página | Gerados os 3 meses | |
   | CA-10.2 | Recarregar de novo | Nenhuma duplicata | |
   | CA-10.3 | Excluir um gerado e recarregar | Não reaparece | |
   | CA-10.4 | Ver o mês seguinte | Nada gerado no futuro | |
   | CA-11.1 | Criar "alimentacao" (já existe "Alimentação") | Recusa com mensagem clara | |
   | CA-11.2 | Renomear categoria com lançamentos antigos | Todos mostram o nome novo | |
   | CA-11.3 | Excluir categoria em uso | Recusa e sugere desativar | |
   | CA-11.4 | Desativar | Some dos formulários, continua na listagem e nos relatórios | |
   | CA-12.1 | Somar à mão a aba do mês | Totais do resumo batem centavo a centavo | |
   | CA-12.2 | Mês com gastos > receitas | Saldo negativo destacado | |
   | CA-13.1 | Gráficos do mês | Cores das categorias | |
   | CA-13.2 | Mês sem gastos | Estado vazio, sem erro | |
   | CA-14.1 | Histórico padrão | 12 meses, inclusive os zerados | |
   | CA-14.2 | Mudar o intervalo | Gráficos e totais atualizam | |
   | CA-14.3 | Período exibido | Total gasto e média mensal | |
   | CA-15.1 | Planilha de teste sem as abas do app → subir | Abas, cabeçalhos e categorias padrão criados | |
   | CA-15.2 | Subir de novo | Nada duplicado nem sobrescrito | |
   | CA-16.1 | Planilha não compartilhada (ID de outra planilha da mesma conta Google, sem compartilhar) | Banner pede para compartilhar com o e-mail da conta de serviço | |
   | CA-16.2 | Desligar a internet (ou o backend) → "Tentar novamente" depois de religar | Volta sem reiniciar o app | |
   | CA-16.3 | Editar à mão uma célula de valor para "abc" → "Recarregar dados" | Faixa "1 linha … ignorada"; corrigir → "Recarregar dados" → faixa some | |
   | RNF-01 | `scripts/start.ps1` numa janela nova | Sobe os dois, abre o navegador; nada fora da máquina | |
   | RNF-03 | Todas as telas | pt-BR, `R$ 1.234,56`, `dd/mm/aaaa`, meses por extenso | |
   | RNF-04 | Registrar, Resumo e Histórico com a planilha de teste | < 3 s (com 5.000 linhas, pelo `test_desempenho`) | |
   | RNF-05 | `git status` / DevTools → Rede | Nenhuma credencial versionada nem enviada ao navegador; backend só em 127.0.0.1 | |
   | RNF-06 | Backend parado ao salvar nos 3 formulários | Dados preservados, nova tentativa possível | |
   | RNF-07 | 5 telas e 4 diálogos em 360 px, claro e escuro, incluindo o botão "Recarregar dados" e a faixa de T-032 | Sem rolagem horizontal; textos quebram | |
   | CA-F02.13 | Seguir o README do zero com a planilha real | Passos suficientes, sem conhecimento prévio | |

### 3.4 README final (T-035)

1. **Como rodar** passa a começar por `scripts/start.ps1` (com o comando de §3.1.4). Os comandos manuais continuam como alternativa: `test_readme.py` exige `uvicorn app.main:app` e `npm start`.
2. **Estrutura:** `scripts/` deixa de ser "(em construção)".
3. **Se algo der errado** ganha: política de execução do PowerShell, porta ocupada com os scripts, "linhas ignoradas" e o botão "Recarregar dados", e `SPREADSHEET_ID_TESTE` conforme Q5.
4. **Testes:** a suíte de integração completa, a trava de §3.2.3 e o aviso de que ela escreve na planilha de teste (e, com Q6, apaga e recria as abas do app nela).
5. **Uso (Q9):** uma seção curta com as 5 telas e o que cada uma faz.
6. O `.env.example` acompanha Q5 (comentário de `SPREADSHEET_ID_TESTE`).

### 3.5 Rastreabilidade RN → teste (T-035, RNF-08)

1. Tabela em §10 com cada RN-01 a RN-16 e os testes que a cobrem (arquivo › nome), gerada a partir dos nomes e docstrings que citam `RN_xx`. Hoje as 16 já aparecem em testes do backend.
2. **Guarda automática (Q10):** `backend/tests/unit/test_rastreabilidade.py` falha se alguma RN de `01` §4 não for citada por nenhum teste do backend nem do frontend. Ela lê os IDs de `SPECS/01-requisitos.md`, o que pega RN nova sem teste.

---

## 4. Critérios de aceite

**Herdados de `01` e de features anteriores**

- [ ] **RNF-01** Dado o computador do usuário, quando ele roda `scripts/start.ps1`, então backend e frontend sobem localmente, sem login nem hospedagem externa.
- [ ] **RNF-08** Dado `01` §4, então toda RN-xx é coberta por pelo menos um teste automatizado (matriz em §10).
- [ ] **Todos os CA de `01`** (CA-01.1 a CA-16.3, 44 itens) com "OK" no roteiro de §3.3.4.
- [ ] **CA-15.1 / CA-15.2** com a suíte de integração passando na planilha de teste.
- [ ] **CA-F14.16** (`test_desempenho`) passando na planilha de teste.
- [ ] **CA-F02.13** Dado o README, quando o usuário o segue do zero com a planilha real, então o app sobe e conecta.

**Refinados — scripts (T-033)**

- [ ] **CA-F15.1** Dado `start.ps1` com nada rodando, então abre duas janelas (backend e frontend), espera o health e o frontend responderem e abre o navegador em `http://localhost:4200`.
- [ ] **CA-F15.2** Dado o app já rodando, quando `start.ps1` é executado de novo, então só abre o navegador, sem subir uma segunda cópia.
- [ ] **CA-F15.3** Dado a porta 8000 ou 4200 ocupada por outro programa, então `start.ps1` mostra qual porta e não sobe nada.
- [ ] **CA-F15.4** Dado `backend/.env` ausente, então `start-backend.ps1` mostra a mensagem de §3.1.1.3 e termina com código ≠ 0; dado Python < 3.12 ou Node fora da faixa, mensagem equivalente.
- [ ] **CA-F15.5** (Q3) Dado um clone novo (sem `.venv` e sem `node_modules`), então os scripts preparam o ambiente na primeira execução e sobem o app.
- [ ] **CA-F15.6** Dado qualquer script, então ele não lê nem imprime `credentials.json` nem o conteúdo do `.env`, e o backend escuta só em `127.0.0.1` (RNF-05).

**Refinados — integração (T-034)**

- [ ] **CA-F15.7** Dado `SPREADSHEET_ID_TESTE` (terminal ou `.env`, Q5), quando `pytest -m integracao` roda, então todos os cenários de §3.2.5 passam.
- [ ] **CA-F15.8** Dado `SPREADSHEET_ID_TESTE` igual ao `SPREADSHEET_ID`, então a suíte falha no início sem escrever nada (Q5).
- [ ] **CA-F15.9** Dado o fim da suíte, com sucesso ou falha, então nenhuma linha marcada `teste-integracao-…` resta nas abas da planilha de teste.
- [ ] **CA-F15.10** Dado `pytest` sem `-m integracao`, então nenhum teste de integração roda e a rede não é tocada (`02` §8, sem regressão).

**Refinados — roteiro, README e rastreabilidade (T-035)**

- [ ] **CA-F15.11** Dado o roteiro de §3.3.4, então cada item tem resultado e data registrados, e o resumo está em §10.
- [ ] **CA-F15.12** Dado o README final, então ele cobre os scripts, os comandos manuais, os testes (inclusive integração) e os problemas de §3.4.3, e `test_readme.py` continua passando.
- [ ] **CA-F15.13** (Q10) Dado uma RN em `01` §4 sem nenhum teste que a cite, então `test_rastreabilidade.py` falha nomeando a RN.

---

## 5. Casos de borda

| # | Caso | Comportamento esperado | Regra |
|---|---|---|---|
| 1 | `start.ps1` executado de dentro de `scripts/` ou de outra pasta qualquer | Funciona igual (`$PSScriptRoot`) | RNF-01 |
| 2 | Caminho do repositório com espaço ou acento (ex.: `C:\Users\João Silva\…`) | Scripts funcionam (caminhos sempre entre aspas) | RNF-01 |
| 3 | Política de execução `Restricted` | Com `-ExecutionPolicy Bypass` no comando documentado, roda sem mudar a configuração do sistema | — |
| 4 | Segundo `start.ps1` com o app no ar | Só abre o navegador (CA-F15.2) | — |
| 5 | Porta 4200 ocupada por outro `ng serve` (outro projeto) | Mensagem de porta ocupada: o health de 8000 não responde como este app | — |
| 6 | Primeiro `ng serve` demorando mais de 60 s | Espera até 180 s antes de desistir | — |
| 7 | Backend sobe, mas a planilha está inacessível | O navegador abre do mesmo jeito; o banner explica a causa (F-04) | REQ-16 |
| 8 | Janela do backend fechada com o frontend aberto | Banner "O servidor do aplicativo não está respondendo…"; rodar `start.ps1` de novo resolve | REQ-16 |
| 9 | `SPREADSHEET_ID_TESTE` vazio | Integração pulada, como hoje | `02` §8 |
| 10 | Teste de integração interrompido (Ctrl+C) | O `finally` limpa as linhas marcadas; o que sobrar tem a marca e é apagado na execução seguinte (varredura por `teste-integracao-` no início) | — |
| 11 | Planilha de teste com dados de outra execução manual | Os testes só olham e apagam as próprias linhas marcadas; os totais são conferidos por diferença ou num mês só dos testes | — |
| 12 | Recorrência de teste criada no fim do mês (dia 31) | Teste usa dia 31 de propósito, para conferir o último dia do mês | RN-09 |
| 13 | Execução da integração em ano bissexto ou não | Esperado de CA-07.2 calculado pelo ano corrente (28 ou 29/02) | RN-07 |
| 14 | Roteiro: item depende de ação no Google que o Claude não pode fazer (compartilhar/descompartilhar) | Pedido ao usuário; registrado como "OK (usuário)" | — |

---

## 6. Contrato e dados

**API** — **nenhum endpoint novo nem alterado.** A suíte e o roteiro usam os de `03` §6.1:

| Método | Caminho | Usado em |
|---|---|---|
| GET | `/api/health` | `start.ps1` (espera o backend), integração |
| GET/POST/PUT/DELETE | `/api/categorias`, `/api/categorias/{id}` | `test_categorias_e2e.py` |
| GET/POST/PUT/DELETE | `/api/lancamentos`, `/api/lancamentos/{id}` | `test_lancamentos_e2e.py` |
| POST/DELETE | `/api/parcelamentos`, `/api/parcelamentos/{parcelamento_id}` | `test_parcelamento_e2e.py` |
| GET/POST/PUT/PATCH | `/api/recorrencias`, `/api/recorrencias/{id}`, `/api/recorrencias/{id}/status` | `test_recorrencias_e2e.py` |
| POST | `/api/recorrencias/sincronizar` | `test_recorrencias_e2e.py` |
| GET | `/api/resumo/mensal`, `/api/resumo/historico` | lançamentos, desempenho |
| POST | `/api/sistema/recarregar` | edição manual, desempenho |

**Planilha** — nenhuma aba ou coluna nova. Os testes escrevem e apagam linhas marcadas nas abas `Lancamentos`, `Categorias` e `Recorrencias` **da planilha de teste**; com Q6, `test_bootstrap.py` apaga e recria as 4 abas do app (`Lancamentos`, `Categorias`, `Recorrencias`, `Config`) **só na planilha de teste**.

**Configuração** (`02` §6) — sem variável nova. `SPREADSHEET_ID_TESTE` passa a ser lida também do `backend/.env` pelos testes (Q5).

---

## 7. Interface

- **Sem mudança de tela.** O roteiro confere as telas existentes (§3.3.4).
- **Scripts** (pt-BR): "Python 3.12 ou superior não encontrado…", "Node.js 24 LTS (ou 22.22.3+) não encontrado…", "Falta o arquivo backend/.env…", "A porta <n> está em uso por outro programa…", "Preparando o ambiente do backend (primeira execução)…", "Instalando dependências do frontend (primeira execução)…", "Aguardando o backend…", "Aguardando o frontend…", "Abrindo http://localhost:4200", "O backend (ou frontend) não respondeu em <n> s…", "O aplicativo já está rodando. Abrindo o navegador.".

---

## 8. Plano de testes

| Teste | Nível | Cobre |
|---|---|---|
| Execução de `start.ps1`: nada rodando / já rodando / porta ocupada / sem `.env` / clone novo | manual (registrada no roteiro) | CA-F15.1 a CA-F15.5, bordas 1–8 |
| Leitura dos scripts (sem `Get-Content` de credencial/`.env`; `--host 127.0.0.1`) | revisão | CA-F15.6, RNF-05 |
| `backend/tests/integracao/conftest.py` › trava de mesma planilha (unitário com `monkeypatch`, fora do marcador `integracao`) — `test_trava_mesma_planilha__CA_F15_8` | unitário BE | CA-F15.8 |
| `backend/tests/unit/test_conftest_integracao.py` › `test_le_planilha_teste_do_env__CA_F15_7` (Q5) | unitário BE | CA-F15.7, borda 9 |
| `tests/integracao/test_bootstrap.py::test_planilha_vazia_preparada__CA_15_1` (Q6) | integração | CA-15.1, CA-15.2, RN-15 |
| `tests/integracao/test_lancamentos_e2e.py::test_crud_e_totais__CA_05_2` | integração | CA-01.2, CA-01.5, CA-02.2, CA-05.2, CA-05.3, CA-06.2, CA-12.1, RN-13, RN-16 |
| `tests/integracao/test_categorias_e2e.py::test_ciclo_de_categoria__RN_12` | integração | CA-11.1 a CA-11.4 |
| `tests/integracao/test_parcelamento_e2e.py::test_parcelas_e_exclusao__RN_07` | integração | CA-07.1, CA-07.2, CA-08.2, RN-08 |
| `tests/integracao/test_recorrencias_e2e.py::test_sincronizacao__RN_10` | integração | CA-10.1 a CA-10.4, RN-09, RN-11, borda 12 |
| `tests/integracao/test_edicao_manual_e2e.py::test_linha_invalida_e_recarregar__RN_14` | integração | CA-16.3, RN-14 |
| `tests/integracao/*` › varredura e limpeza das linhas marcadas | integração | CA-F15.9, borda 10 |
| `pytest` simples (sem `-m integracao`) continua verde e sem rede | API/unitário BE | CA-F15.10 |
| `backend/tests/unit/test_rastreabilidade.py::test_toda_rn_tem_teste__RNF_08` (Q10) | unitário BE | RNF-08, CA-F15.13 |
| `backend/tests/unit/test_readme.py` (existe; atualizado se o README ganhar trechos obrigatórios) | unitário BE | CA-F15.12, CA-F02.13 |
| Roteiro de §3.3.4 | E2E manual | 44 CA de `01`, RNF-01/03/04/05/06/07, CA-F02.13 |

---

## 9. Divisão em tarefas

| Tarefa | Escopo nesta feature | Arquivos principais |
|---|---|---|
| **T-033** (DOC) | Scripts de §3.1 (Q1–Q3) e a parte "Como rodar" do README que os descreve. | `scripts/start-backend.ps1`, `scripts/start-frontend.ps1`, `scripts/start.ps1`, `README.md` (§3) |
| **T-034** (BE) | Suíte de §3.2 (Q5, Q6): `conftest` com `.env` e trava, varredura de limpeza, os 6 arquivos novos; guarda de rastreabilidade (Q10); execução de `pytest -m integracao` na planilha de teste. | `backend/tests/integracao/{conftest.py,test_bootstrap.py,test_lancamentos_e2e.py,test_categorias_e2e.py,test_parcelamento_e2e.py,test_recorrencias_e2e.py,test_edicao_manual_e2e.py}`, `backend/tests/conftest.py`, `backend/tests/unit/{test_conftest_integracao.py,test_rastreabilidade.py}`, `backend/.env.example` |
| **T-035** (DOC) | Roteiro de §3.3 (Q7, Q8): refinar passos, executar, registrar; README final (§3.4, Q9); matriz RN → teste (§3.5). | `SPECS/features/F-15-entrega-local-e-e2e.md`, `README.md`, `SPECS/05-acompanhamento.md` |

Ordem: T-033 e T-034 em qualquer ordem (as duas dependem só de T-032); T-035 depois das duas (`04`/`05`).

---

## 10. Decisões tomadas nesta feature

| Decisão | Motivo | Virou ADR? |
|---|---|---|
| Nenhum endpoint, coluna ou dependência nova. | F-15 entrega e verifica; não muda comportamento (`01` §6). | Não |
| Scripts com `-ExecutionPolicy Bypass` no comando, sem alterar a política do Windows. | Mudar configuração de segurança do sistema não é papel do app. | Não |
| Integração pelo app real (`criar_app` + `TestClient`), não pelos repositórios soltos. | Prova a composição inteira (cache, serviços, handlers) contra o Google de verdade. | Não |
| Limpeza por marca (`teste-integracao-…`) com varredura no início. | Execução interrompida não deixa lixo acumulando na planilha de teste. | Não |
| Scripts sobem `uvicorn` sem `--reload` e `ng serve` com proxy (Q1). | Mesmo fluxo já especificado em `02` §2 e `03`; servir o build pelo FastAPI mudaria a arquitetura. | Não |
| `start.ps1` abre duas janelas com título; com o app no ar, só abre o navegador (Q2). | Logs separados e visíveis; fechar a janela é o jeito óbvio de parar. | Não |
| Primeira execução prepara `.venv` e `node_modules` sozinha (Q3). | Um comando só, mesmo num clone novo (RNF-01). | Não |
| P-01 e P-07 confirmadas; P-02 e P-06 seguem "A confirmar" e valem como escritas (Q4). | Escolha do usuário; `01` → 1.3. | Não |
| `SPREADSHEET_ID_TESTE` lida também do `backend/.env`, terminal com precedência, com trava contra a planilha do app (Q5). | Alinha código, `.env.example` e README; evita escrever na planilha real por engano. | Não |
| CA-15.1 provado apagando as 4 abas do app **só na planilha de teste** (Q6). | Prova a planilha vazia de verdade sem exigir uma planilha extra; protegido pela trava de Q5. | Não |
| Roteiro E2E na planilha de teste, conduzido pelo Claude no Chrome, com o usuário nos passos do Google e na confirmação final (Q7). | A planilha real não recebe dados de teste; o registro fica completo. | Não |
| Falha pequena e dentro do especificado é corrigida em T-035 com teste; mudança de comportamento ou falha grande vira tarefa nova (Q8). | Fecha o marco sem abrir tarefa para cada ajuste mínimo, sem esconder mudança de escopo. | Não |
| README ganha uma seção "Uso" curta (Q9). | O README é o único manual do app. | Não |
| Guarda automática `test_rastreabilidade.py` para RNF-08 (Q10). | RN nova sem teste passa a falhar a suíte. | Não |

*(O resultado do roteiro e a matriz RN → teste entram aqui em T-035.)*

---

## 11. Questões em aberto

**Respondidas em 2026-10-02 — nenhuma em aberto.**

- [x] **Q1** → `uvicorn` sem `--reload` + `ng serve` (§3.1).
- [x] **Q2** → duas janelas com título; app já no ar → só abre o navegador (§3.1.3).
- [x] **Q3** → os scripts preparam `.venv` e `node_modules` na primeira execução (§3.1.1.2, §3.1.2.2).
- [x] **Q4** → **P-01** e **P-07** confirmadas (`01` → 1.3); **P-02** e **P-06** continuam "A confirmar" (valem como escritas).
- [x] **Q5** → `SPREADSHEET_ID_TESTE` também do `backend/.env`, terminal com precedência, trava contra a planilha do app (§3.2.2–3).
- [x] **Q6** → `test_bootstrap.py` apaga as 4 abas do app só na planilha de teste (§3.2.5).
- [x] **Q7** → planilha de teste, roteiro conduzido pelo Claude no Chrome, usuário nos passos do Google e na confirmação (§3.3.1–2).
- [x] **Q8** → defeito pequeno no especificado corrigido em T-035 com teste; o resto vira tarefa nova (§3.3.3).
- [x] **Q9** → README com seção "Uso" curta (§3.4.5).
- [x] **Q10** → guarda automática `test_rastreabilidade.py` (§3.5.2).

---

## Revisões

| Data | Alteração |
|---|---|
| 2026-10-02 | Criação (`/especificar-feature F-15`). Status `Rascunho` — 10 questões em aberto. |
| 2026-10-02 | Q1–Q10 respondidas → status **Aprovada**. Todas na opção recomendada; em Q4, só P-01 e P-07 confirmadas (`01` → 1.3). Dez decisões em §10. |
