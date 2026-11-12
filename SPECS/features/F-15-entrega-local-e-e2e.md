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
   2. Se `backend/.venv` não existe, cria; e instala `requirements.txt` quando a `.venv` acabou de ser criada **ou** quando `import fastapi, gspread, uvicorn` falha nela (preparação interrompida antes) **(Q3)**.
   3. Se `backend/.env` não existe: "Falta o arquivo backend/.env. Copie backend/.env.example e preencha SPREADSHEET_ID (README, seção 2.5)." e sai com código ≠ 0. O conteúdo não é validado aqui: SPREADSHEET_ID vazio já gera a mensagem do próprio backend, e problemas de credencial ou planilha aparecem no banner (`/api/health`).
   4. Sobe `uvicorn app.main:app --host 127.0.0.1 --port 8000`, **sem `--reload`** **(Q1)**, usando o Python da `.venv`, sem exigir que o usuário a ative.
   5. Com `-SoPreparar`, faz os passos 1–3 e termina com código 0, sem subir o servidor (usado pelo `start.ps1`, item 3.3).
2. **`scripts/start-frontend.ps1`**
   1. Confere o Node (24 LTS ou `^22.22.3`, `02` §1), com mensagem e saída ≠ 0 se faltar.
   2. Se falta `frontend/node_modules\.bin\ng.cmd` (sem `node_modules` ou instalação interrompida), roda `npm install` **(Q3)**.
   3. Sobe `npm start` (`ng serve` com o proxy `/api` → 8000; `http://localhost:4200`) **(Q1)**.
   4. Com `-SoPreparar`, faz os passos 1–2 e termina com código 0, sem subir o servidor.
3. **`scripts/start.ps1`** **(Q2)** — decide **parte por parte** (backend na 8000, frontend na 4200):
   1. **Reconhece o app:** o backend é este app se `http://127.0.0.1:8000/api/health` responde JSON com o campo `planilha`; o frontend é este app se `http://localhost:4200` devolve uma página com `<title>Planilha Financeira</title>`.
   2. Parte já no ar → não sobe de novo. As duas no ar: "O aplicativo já está rodando. Abrindo o navegador." e só abre o navegador.
   3. Porta ocupada por **outro** programa (alguém escuta na porta, mas não é este app): "A porta 8000 está em uso por outro programa. Feche-o ou veja o README, seção 5." e sai **sem subir nada** (nem a outra parte).
   4. **Preparação antes de contar o tempo:** para cada parte a subir, roda o script dela com `-SoPreparar` **na própria janela** (verificações, `.venv`/`pip install`, `npm install`). Se falhar, a mensagem já foi mostrada e o `start.ps1` termina sem abrir janelas.
   5. Abre **uma janela do PowerShell para cada parte a subir**, com os títulos "Planilha Financeira — backend" e "Planilha Financeira — frontend", rodando os dois scripts acima. Os logs ficam visíveis, e fechar a janela (ou Ctrl+C nela) para aquela parte.
   6. Espera o `/api/health` responder (até 60 s) e depois `http://localhost:4200` (até 180 s, porque o primeiro `ng serve` compila tudo). Assim que o frontend responde, abre o navegador padrão em `http://localhost:4200`.
   7. Esgotado o tempo: "O backend (ou frontend) não respondeu em N s. Veja a janela dele para o erro." Nada é encerrado, para o usuário poder ler o log.
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
   | `test_bootstrap_e2e.py` **(Q6)** | apaga as 4 abas do app na planilha de teste (criando antes uma aba vazia de apoio, se preciso: o Google exige ao menos uma aba), sobe o app e confere abas, cabeçalhos e as 15 categorias de RN-15; sobe de novo e nada muda | CA-15.1, CA-15.2, RN-15 |
   | `test_lancamentos_e2e.py` | num mês isolado (2098-03), gastos de 0,10 e 0,20 e receita de 1.000,00 sem forma → totais 0,30 / 1.000,00 / 999,70 no `GET` do mês e no resumo, centavo a centavo; `PUT` muda só a linha do `id` (outra linha marcada fica igual) e a troca de mês move o lançamento; `DELETE` remove a linha e os totais voltam | CA-01.2, CA-01.5, CA-02.2, CA-05.2, CA-05.3, CA-06.2, CA-12.1, RN-13, RN-16 |
   | `test_categorias_e2e.py` | criar, renomear (o lançamento antigo mostra o nome novo), duplicado sem acento/maiúscula → 409, excluir em uso → 409, desativar, excluir sem uso → 204 | CA-11.1 a CA-11.4, RN-12 |
   | `test_parcelamento_e2e.py` | R$ 1.000,00 em 3 a partir de 15/01/2098 → 333,34 / 333,33 / 333,33 em três meses, com "k/N"; 31/01/2096 em 2 → 29/02/2096 e 31/01/2097 em 2 → 28/02/2097; `DELETE /api/parcelamentos/{id}` remove todas, em qualquer mês | CA-07.1 a CA-07.3, CA-08.2, RN-07, RN-08 |
   | `test_recorrencias_e2e.py` | recorrência ativa, dia 31, com início 2 meses antes do corrente → `sincronizar` gera 3 (último dia de cada mês); de novo → 0; excluir um gerado e sincronizar → 0; nada em mês futuro; pausar → 0; reativar → 0 e `ultimo_mes_gerado` igual. O "período pausado não é gerado" ao reativar num mês posterior exige avançar o relógio e fica nos testes unitários de F-13 | CA-10.1 a CA-10.4, RN-09 a RN-11 |
   | `test_edicao_manual_e2e.py` | grava direto na aba uma linha marcada com valor "abc" (2098-05) → depois de `POST /api/sistema/recarregar`, `linhas_ignoradas` sobe 1 e a linha fica fora dos totais; corrige na aba e `POST /api/sistema/recarregar` → a linha entra na hora | CA-16.3, RN-14 |
   | `test_desempenho.py` (existe) | 5.000 lançamentos, cada chamada < 3 s com o cache frio | CA-F14.16, RNF-04 |

6. **Execução:** `pytest -m integracao` (manual, `02` §8). Um `pytest` simples continua sem tocar a rede.
7. **Cota do Google (T-035):** a Sheets API limita as leituras por minuto por usuário (~60), e a suíte inteira passa disso. Antes de cada teste que fala com o Google, uma fixture automática espera até **61 s depois do fim do teste anterior**, para cada um começar com a janela de cota zerada. A suíte leva cerca de 12 minutos. O retry do app (`02` §5.5) não muda.

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
   | CA-F15.5 | Clone novo (sem `.venv` e sem `node_modules`) + `.env` → `scripts\start.ps1` | Prepara o ambiente e sobe | |

5. **Preparação e ordem de execução** (T-035):
   1. `SPREADSHEET_ID_TESTE` preenchido e `pytest -m integracao` verde antes do roteiro: prepara as abas da planilha de teste e já cobre CA-15.1/15.2, CA-F14.16, CA-F15.7 e CA-F15.9 contra o Google.
   2. App apontando para a planilha de teste: fechar qualquer cópia do app no ar e, numa janela do PowerShell, `$env:SPREADSHEET_ID = "<id da planilha de teste>"` e então `scripts\start.ps1` — as janelas abertas herdam a variável, que vale mais que o `.env`. Conferir no título da planilha (banner/health) que é a de teste.
   3. Ordem, para cada item aproveitar o estado do anterior: CA-15.x (abas na planilha) → CA-04 → CA-01/02 → CA-03 → CA-05/06 → CA-07/08 → CA-11 → CA-12/13 (mês corrente) → CA-14 → CA-09/10 (recorrência e recarga da página) → CA-16.3 (célula editada à mão) → RNF-03/04/06/07 → CA-16.1/16.2 (por último, porque derrubam a conexão) → RNF-01 e CA-F15.5 (clone novo) → CA-F02.13 (planilha real, com o usuário) → RNF-05.
   4. Dados: mês corrente e os dois anteriores para resumo, histórico e recorrência; parcelamento com data no mês corrente; descrições começando por "E2E" para achar e apagar no fim.
   5. Fim: apagar na planilha de teste as linhas "E2E" (ou rodar `pytest -m integracao` de novo, que limpa só as marcadas `teste-…`), voltar `SPREADSHEET_ID` ao normal fechando a janela do PowerShell.

### 3.4 README final (T-035)

1. **Como rodar** passa a começar por `scripts/start.ps1` (com o comando de §3.1.4). Os comandos manuais continuam como alternativa: `test_readme.py` exige `uvicorn app.main:app` e `npm start`.
2. **Estrutura:** `scripts/` deixa de ser "(em construção)" (feito já em T-033).
3. **Se algo der errado** ganha: política de execução do PowerShell, porta ocupada com os scripts, "linhas ignoradas" e o botão "Recarregar dados", e `SPREADSHEET_ID_TESTE` conforme Q5.
4. **Testes:** a suíte de integração completa, a trava de §3.2.3 e o aviso de que ela escreve na planilha de teste (e, com Q6, apaga e recria as abas do app nela) — o parágrafo de integração já é corrigido em T-034.
5. **Uso (Q9):** uma seção curta com as 5 telas e o que cada uma faz.
6. O `.env.example` acompanha Q5 (comentário de `SPREADSHEET_ID_TESTE`).

### 3.5 Rastreabilidade RN → teste (T-035, RNF-08)

1. Tabela em §10 com cada RN-01 a RN-16 e os testes que a cobrem (arquivo › nome), gerada a partir dos nomes e docstrings que citam `RN_xx`. Hoje as 16 já aparecem em testes do backend.
2. **Guarda automática (Q10):** `backend/tests/unit/test_rastreabilidade.py` falha se alguma RN de `01` §4 não for citada por nenhum teste do backend nem do frontend. Ela lê os IDs de `SPECS/01-requisitos.md`, o que pega RN nova sem teste.

---

## 4. Critérios de aceite

**Herdados de `01` e de features anteriores**

- [ ] **RNF-01** Dado o computador do usuário, quando ele roda `scripts/start.ps1`, então backend e frontend sobem localmente, sem login nem hospedagem externa.
- [x] **RNF-08** Dado `01` §4, então toda RN-xx é coberta por pelo menos um teste automatizado (matriz em §10). *(T-035: matriz em §10 + guarda `test_rastreabilidade.py` de T-034.)*
- [ ] **Todos os CA de `01`** (CA-01.1 a CA-16.3, 44 itens) com "OK" no roteiro de §3.3.4.
- [ ] **CA-15.1 / CA-15.2** com a suíte de integração passando na planilha de teste.
- [ ] **CA-F14.16** (`test_desempenho`) passando na planilha de teste.
- [ ] **CA-F02.13** Dado o README, quando o usuário o segue do zero com a planilha real, então o app sobe e conecta.

**Refinados — scripts (T-033)**

- [x] **CA-F15.1** Dado `start.ps1` com nada rodando, então abre duas janelas (backend e frontend), espera o health e o frontend responderem e abre o navegador em `http://localhost:4200`. *(T-033: CA-F15.1 a .4 e a borda 8 executados pelo usuário em 2026-10-02 — todos como esperado; CA-F15.6 e a sintaxe pela guarda `test_scripts.py`.)*
- [x] **CA-F15.2** Dado o app já rodando, quando `start.ps1` é executado de novo, então só abre o navegador, sem subir uma segunda cópia.
- [x] **CA-F15.3** Dado a porta 8000 ou 4200 ocupada por outro programa, então `start.ps1` mostra qual porta e não sobe nada.
- [x] **CA-F15.4** Dado `backend/.env` ausente, então `start-backend.ps1` mostra a mensagem de §3.1.1.3 e termina com código ≠ 0; dado Python < 3.12 ou Node fora da faixa, mensagem equivalente.
- [ ] **CA-F15.5** (Q3) Dado um clone novo (sem `.venv` e sem `node_modules`), então os scripts preparam o ambiente na primeira execução e sobem o app. *(T-033: implementado; a execução num clone novo fica para o roteiro de T-035 — RNF-01.)*
- [x] **CA-F15.6** Dado qualquer script, então ele não lê nem imprime `credentials.json` nem o conteúdo do `.env`, e o backend escuta só em `127.0.0.1` (RNF-05).

**Refinados — integração (T-034)**

- [ ] **CA-F15.7** Dado `SPREADSHEET_ID_TESTE` (terminal ou `.env`, Q5), quando `pytest -m integracao` roda, então todos os cenários de §3.2.5 passam. *(T-034: suíte escrita e coletada (9 testes); leitura do `.env` coberta por `test_conftest_integracao.py`. **Execução pendente com o usuário** — `SPREADSHEET_ID_TESTE` vazio; o usuário escolheu concluir sem rodar.)*
- [x] **CA-F15.8** Dado `SPREADSHEET_ID_TESTE` igual ao `SPREADSHEET_ID`, então a suíte falha no início sem escrever nada (Q5). *(T-034: unitário + `pytest -m integracao` com os dois IDs iguais no ambiente — parou com a mensagem e código 4, sem abrir planilha.)*
- [ ] **CA-F15.9** Dado o fim da suíte, com sucesso ou falha, então nenhuma linha marcada `teste-integracao-…` resta nas abas da planilha de teste. *(T-034: lógica da varredura testada na planilha falsa; conferência real junto com CA-F15.7.)*
- [x] **CA-F15.10** Dado `pytest` sem `-m integracao`, então nenhum teste de integração roda e a rede não é tocada (`02` §8, sem regressão).

**Refinados — roteiro, README e rastreabilidade (T-035)**

- [ ] **CA-F15.11** Dado o roteiro de §3.3.4, então cada item tem resultado e data registrados, e o resumo está em §10.
- [x] **CA-F15.12** Dado o README final, então ele cobre os scripts, os comandos manuais, os testes (inclusive integração) e os problemas de §3.4.3, e `test_readme.py` continua passando. *(T-035: "Uso" entrou como subseção de §3 — os scripts citam as seções 1, 2.5, 3 e 5 pelo número; estado "em construção" e "mais tarde, no banner" atualizados.)*
- [x] **CA-F15.13** (Q10) Dado uma RN em `01` §4 sem nenhum teste que a cite, então `test_rastreabilidade.py` falha nomeando a RN.

---

## 5. Casos de borda

| # | Caso | Comportamento esperado | Regra |
|---|---|---|---|
| 1 | `start.ps1` executado de dentro de `scripts/` ou de outra pasta qualquer | Funciona igual (`$PSScriptRoot`) | RNF-01 |
| 2 | Caminho do repositório com espaço ou acento (ex.: `C:\Users\João Silva\…`) | Scripts funcionam (caminhos sempre entre aspas) | RNF-01 |
| 3 | Política de execução `Restricted` | Com `-ExecutionPolicy Bypass` no comando documentado, roda sem mudar a configuração do sistema | — |
| 4 | Segundo `start.ps1` com o app no ar | Só abre o navegador (CA-F15.2) | — |
| 5 | Porta 4200 ocupada por outro `ng serve` (outro projeto) | Mensagem de porta ocupada: a página não tem o título deste app | — |
| 6 | Primeiro `ng serve` demorando mais de 60 s | Espera até 180 s antes de desistir | — |
| 7 | Backend sobe, mas a planilha está inacessível | O navegador abre do mesmo jeito; o banner explica a causa (F-04) | REQ-16 |
| 8 | Janela do backend fechada com o frontend aberto | Banner "O servidor do aplicativo não está respondendo…"; rodar `start.ps1` de novo sobe só o backend e abre o navegador | REQ-16 |
| 8a | Primeira execução: `pip install` ou `npm install` levando minutos | A preparação roda antes de contar os 60/180 s (§3.1.3.4) | RNF-01 |
| 8b | `.venv` criada, mas o `pip install` foi interrompido | Na execução seguinte o import falha e a instalação roda de novo (§3.1.1.2) | — |
| 9 | `SPREADSHEET_ID_TESTE` vazio | Integração pulada, como hoje | `02` §8 |
| 10 | Teste de integração interrompido (Ctrl+C) | O `finally` limpa as linhas marcadas; o que sobrar tem a marca e é apagado na execução seguinte (varredura por `teste-integracao-` no início) | — |
| 11 | Planilha de teste com dados de outra execução manual | Os testes só olham e apagam as próprias linhas marcadas; os totais são conferidos em meses distantes (2096–2098), só dos testes, ou por diferença (`linhas_ignoradas`) | — |
| 12 | Recorrência de teste criada no fim do mês (dia 31) | Teste usa dia 31 de propósito, para conferir o último dia do mês | RN-09 |
| 13 | Fevereiro bissexto e não bissexto | Datas fixas: 31/01/2096 → 29/02/2096 e 31/01/2097 → 28/02/2097, em qualquer ano de execução | RN-07 |
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

**Planilha** — nenhuma aba ou coluna nova. Os testes escrevem e apagam linhas marcadas nas abas `Lancamentos`, `Categorias` e `Recorrencias` **da planilha de teste**; com Q6, `test_bootstrap_e2e.py` apaga e recria as 4 abas do app (`Lancamentos`, `Categorias`, `Recorrencias`, `Config`) **só na planilha de teste**.

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
| `backend/tests/unit/test_scripts.py` › `test_scripts_sem_erro_de_sintaxe__CA_F15_1` (parser do PowerShell) e `test_backend_so_em_localhost_e_sem_ler_segredos__CA_F15_6` | unitário BE | CA-F15.1 a .6 (base), RNF-05, borda 1 |
| `backend/tests/unit/test_conftest_integracao.py` › `test_le_planilha_teste_do_env__CA_F15_7` (Q5) e `test_trava_mesma_planilha__CA_F15_8` (fora do marcador `integracao`) | unitário BE | CA-F15.7, CA-F15.8, borda 9 |
| `backend/tests/unit/test_conftest_integracao.py` › `test_apaga_so_linhas_marcadas__CA_F15_9` (planilha falsa) | unitário BE | CA-F15.9 (lógica da varredura), borda 10 |
| `tests/integracao/test_bootstrap_e2e.py::test_planilha_vazia_preparada__CA_15_1` (Q6) | integração | CA-15.1, CA-15.2, RN-15 |
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
| **T-033** (DOC) | Scripts de §3.1 (Q1–Q3) e as partes "Como rodar" e "Estrutura" do README que os descrevem; guarda `test_scripts.py`. | `scripts/start-backend.ps1`, `scripts/start-frontend.ps1`, `scripts/start.ps1`, `README.md` (§3, §6), `backend/tests/unit/test_scripts.py` |
| **T-034** (BE) | Suíte de §3.2 (Q5, Q6): `conftest` com `.env` e trava, varredura de limpeza, os 6 arquivos novos; guarda de rastreabilidade (Q10); parágrafo de integração do README §4; execução de `pytest -m integracao` na planilha de teste. | `backend/tests/integracao/{ambiente.py,conftest.py,test_bootstrap_e2e.py,test_lancamentos_e2e.py,test_categorias_e2e.py,test_parcelamento_e2e.py,test_recorrencias_e2e.py,test_edicao_manual_e2e.py}`, `backend/tests/conftest.py`, `backend/tests/unit/{test_conftest_integracao.py,test_rastreabilidade.py}`, `backend/.env.example`, `README.md` (§4) |
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
| `-SoPreparar` em `start-backend.ps1`/`start-frontend.ps1`; o `start.ps1` prepara na própria janela antes de contar os 60/180 s (T-033, aprovado). | `pip install`/`npm install` da primeira execução passariam do tempo de espera. Sem arquivo novo em `scripts/`. | Não |
| `start.ps1` decide parte por parte, reconhecendo o app pelo campo `planilha` do health e pelo `<title>` do frontend (T-033, aprovado). | Cobre a borda 8 (uma janela fechada) e distingue "este app" de "outro programa na porta". | Não |
| Reinstalação quando o `import fastapi, gspread, uvicorn` falha na `.venv` ou falta `node_modules\.bin\ng.cmd` (T-033, aprovado). | Preparação interrompida não deixa o ambiente quebrado para sempre. | Não |
| Scripts em UTF-8 **com BOM** e CRLF, cobertos por `test_scripts.py` (T-033). | O Windows PowerShell 5.1 lê `.ps1` sem BOM como ANSI e estragaria os acentos das mensagens. | Não |
| Execução real dos cenários feita pelo usuário, não pelo Claude (T-033). | Escolha do usuário: os scripts abrem janelas e o navegador na máquina dele. | Não |
| Ambiente da integração em `tests/integracao/ambiente.py` (leitura da planilha, trava, varredura, credencial), não no `conftest` (T-034). | Os unitários importam sem rede; e os valores do terminal são guardados num módulo importado uma vez, antes de o `conftest` raiz trocá-los por falsos (importar o `conftest` de novo veria os falsos). | Não |
| `.env` lido por um `BaseSettings` restrito ao arquivo (sem o ambiente) (T-034). | O `conftest` raiz põe um `SPREADSHEET_ID` falso no ambiente; a trava precisa do valor real do `.env`. Sem dependência nova. | Não |
| Cenário de bootstrap em `test_bootstrap_e2e.py` (não `test_bootstrap.py`) (T-034). | Já existe `tests/unit/test_bootstrap.py`; sem `__init__.py`, o pytest não aceita dois módulos com o mesmo nome. Mesmo sufixo dos outros cenários. | Não |
| O cenário de parcelamento também cobre CA-08.1 (editar uma parcela não mexe nas outras) (T-034). | Custa uma chamada a mais e fecha o REQ-08 contra o Google. | Não |
| Suíte concluída sem execução real (T-034). | Escolha do usuário: `SPREADSHEET_ID_TESTE` vazio; CA-F15.7, CA-F15.9, CA-15.1/15.2 e CA-F14.16 seguem pendentes com ele (`pytest -m integracao`). | Não |
| Espera de 61 s entre os testes de integração (§3.2.7) (T-035, aprovado). | A cota de leituras por minuto do Google estourava com a suíte inteira; esperar a janela zerar é mais simples e previsível que mexer no retry do app. | Não |
| Contadores de descrição/observação começam do valor do controle (T-035, Q8). | Defeito achado no roteiro: na edição mostravam "0/100"; correção pequena dentro do especificado, com teste. | Não |

**Matriz RN → teste (RNF-08)** — gerada em T-035 a partir dos nomes dos testes; a guarda `tests/unit/test_rastreabilidade.py` falha se alguma RN ficar sem teste. "Arquivos" conta os arquivos de teste que citam a RN (nome ou docstring); a coluna do meio lista exemplos com o ID no nome.

| RN | Regra | Testes (exemplos) | Arquivos |
|---|---|---|---|
| RN-01 | Valor positivo, até 2 casas | `api/test_lancamentos.py::test_valor_invalido_422__RN_01`, `unit/test_dinheiro.py::test_dinheiro_recusa_zero_negativo_e_mais_de_2_casas__RN_01` | 2 |
| RN-02 | Data obrigatória, passada/futura aceita | `api/test_lancamentos.py::test_data_ausente_422__RN_02`, `unit/test_lancamento_service.py::test_datas_passadas_e_futuras__RN_02` | 2 |
| RN-03 | Mês de referência = mês da data | `unit/test_datas.py::test_mes_de_e_mes_de_referencia__RN_03`, `unit/test_lancamento_service.py::test_listar_filtra_pelo_mes__RN_03` | 4 |
| RN-04 | Categoria ativa e do mesmo tipo | `api/test_lancamentos.py::test_409_de_categoria__RN_04`, `unit/test_lancamento_service.py::test_categoria_inativa_ou_de_outro_tipo__RN_04` | 5 |
| RN-05 | Forma obrigatória em gasto, opcional em receita | `unit/test_modelos.py::test_gasto_exige_forma_de_pagamento__RN_05`, `fe:lancamento-form.dialog.spec.ts › volta_para_gasto_exige_forma__RN_05` | 9 |
| RN-06 | Descrição 1–100, observação até 500 | `api/test_lancamentos.py::test_descricao_observacao_e_enums_422__RN_06`, `unit/test_modelos.py::test_lancamento_aceita_limites_de_texto__RN_06` | 2 |
| RN-07 | Parcelamento 2–48, centavos na 1ª, último dia do mês | `unit/test_dinheiro.py::test_parcelas_centavos_na_primeira__RN_07`, `integracao/test_parcelamento_e2e.py::test_parcelas_e_exclusao__RN_07`, `fe:parcelas.spec.ts › previa__RN_07` | 7 |
| RN-08 | Parcelas independentes; vínculo só para k/N e exclusão total | `unit/test_lancamento_service.py::test_excluir_parcela_so_ela__RN_08`, `unit/test_modelos.py::test_parcela_completa_e_valida__RN_08` | 5 |
| RN-09 | Recorrência: valor fixo, dia 1–31, um por mês, nada futuro | `unit/test_sincronizacao.py::test_dia_31__RN_09`, `unit/test_datas.py::test_ajustar_dia_em_fim_de_mes_e_ano_bissexto__RN_09` | 6 |
| RN-10 | Marca d'água; excluído não volta | `unit/test_sincronizacao.py::test_excluido_nao_volta__CA_10_3__RN_10`, `integracao/test_recorrencias_e2e.py::test_sincronizacao__RN_10` | 3 |
| RN-11 | Pausar/encerrar param; reativar sem retroativos | `unit/test_recorrencia_service.py::test_reativar_sem_retroativos__RN_11`, `unit/test_sincronizacao.py::test_pausada_e_encerrada_nao_geram__RN_11` | 4 |
| RN-12 | Nome único por tipo (sem caixa/acento); excluir só sem uso | `unit/test_categoria_service.py::test_nome_duplicado_ignora_caixa_e_acento__RN_12`, `integracao/test_categorias_e2e.py::test_ciclo_de_categoria__RN_12` | 2 |
| RN-13 | Saldo = receitas − gastos | `unit/test_lancamento_service.py::test_totais_exatos__RN_13_RN_16`, `unit/test_dinheiro.py::test_montante_aceita_zero_e_negativo__RN_13` | 4 |
| RN-14 | Planilha é a fonte da verdade; linhas inválidas ignoradas e contadas | `integracao/test_edicao_manual_e2e.py::test_linha_invalida_e_recarregar__RN_14`, `unit/test_repositorio_planilha.py::test_normaliza_espacos__RN_14`, `fe:sistema.api.spec.ts › recarregar__RN_14` | 6 |
| RN-15 | Categorias padrão | `unit/test_bootstrap.py::test_semeia_as_quinze_categorias_padrao__RN_15`, `unit/test_bootstrap.py::test_resemeia_se_categorias_esvaziada__RN_15` | 7 |
| RN-16 | Somas em centavos exatos | `unit/test_dinheiro.py::test_soma_em_decimal_sem_erro_de_ponto_flutuante__RN_16`, `unit/test_resumo_service.py::test_somas_exatas_em_centavos__RN_16` | 6 |

*(O resultado do roteiro entra aqui quando ele for executado.)*

---

## 11. Questões em aberto

**Respondidas em 2026-10-02 — nenhuma em aberto.**

- [x] **Q1** → `uvicorn` sem `--reload` + `ng serve` (§3.1).
- [x] **Q2** → duas janelas com título; app já no ar → só abre o navegador (§3.1.3).
- [x] **Q3** → os scripts preparam `.venv` e `node_modules` na primeira execução (§3.1.1.2, §3.1.2.2).
- [x] **Q4** → **P-01** e **P-07** confirmadas (`01` → 1.3); **P-02** e **P-06** continuam "A confirmar" (valem como escritas).
- [x] **Q5** → `SPREADSHEET_ID_TESTE` também do `backend/.env`, terminal com precedência, trava contra a planilha do app (§3.2.2–3).
- [x] **Q6** → `test_bootstrap_e2e.py` apaga as 4 abas do app só na planilha de teste (§3.2.5).
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
| 2026-10-02 | T-033 (aprovado pelo usuário): §3.1 com `-SoPreparar` e preparação antes de contar o tempo, decisão parte por parte no `start.ps1` (reconhecimento do app pelo health e pelo título), reinstalação após preparação interrompida; bordas 5, 8, 8a, 8b; README §6 já em T-033; guarda `test_scripts.py` no plano de testes. |
| 2026-10-02 | T-033 concluída: CA-F15.1 a .4 e .6 verificados (5 cenários executados pelo usuário + `test_scripts.py`); CA-F15.5 implementado, execução num clone novo no roteiro de T-035. Cinco decisões em §10. |
| 2026-10-02 | T-034 (aprovado pelo usuário): datas fixas em 2096–2098 (bordas 11 e 13); reativação conferida sem avançar o relógio (o período pausado fica nos unitários de F-13); testes da trava e da varredura em `tests/unit/test_conftest_integracao.py`; `ambiente.py` e README §4 em T-034. |
| 2026-10-02 | T-034 concluída: CA-F15.8, .10 e .13 verificados; CA-F15.7 e .9 com suíte escrita e execução pendente com o usuário. Cenário de bootstrap renomeado para `test_bootstrap_e2e.py`. Cinco decisões em §10. `02` → 1.14. |
| 2026-10-02 | T-035 (parcial): README final (CA-F15.12), matriz RN → teste em §10 (RNF-08), preparação e ordem do roteiro em §3.3.5 e item CA-F15.5 no roteiro. Execução do roteiro bloqueada: planilha de teste e Chrome ausentes. |
| 2026-10-02 | T-035 (aprovado pelo usuário): §3.2.7 — espera de 61 s entre os testes de integração por causa da cota do Google; defeito dos contadores do diálogo de edição ("0/100" com texto preenchido) corrigido por Q8, com teste. |
| 2026-11-12 | **Revisão (F-16, aprovada pelo usuário):** o guarda de §3.5 (`test_rastreabilidade.py`) passa a ignorar RN marcadas *(planejada — F-xx)* em `01` §4 (novo teste `test_rn_planejada_fica_de_fora__RNF_08`); RN-17..RN-24 (F-16) entram marcadas até T-038. O roteiro desta feature continua cobrindo REQ-01..REQ-16; REQ-17..REQ-20 e os CA acrescentados em `01` 1.4 ficam no roteiro de F-16 §8.3. |
