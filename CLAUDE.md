# Planilha Financeira — instruções para o Claude Code

App local e pessoal de controle financeiro: o usuário registra gastos e receitas, que são gravados numa planilha Google; o app mostra somatórios e gráficos do mês e o histórico. Backend **Python/FastAPI** + **gspread** (service account); frontend **Angular 22** (zoneless, Vitest) com Chart.js. Sem login; roda só no computador do usuário (Windows).

## Fonte da verdade: `SPECS/`

Este projeto usa **Spec-Driven Development**. As specs mandam; o código segue.

@SPECS/README.md

- Estado atual das tarefas: `SPECS/05-acompanhamento.md` (não duplique status em outro lugar).
- Leia só as seções indicadas em "Leitura mínima por tipo de tarefa" (README §5).

## Regras invioláveis

1. **Nunca leia, exiba, copie ou faça commit de `credentials.json`.** O código só referencia o caminho (`GOOGLE_CREDENTIALS_PATH`). Nada de credenciais em logs, testes, fixtures ou no frontend.
2. **Spec primeiro.** Se a implementação exigir comportamento, endpoint, coluna, dependência ou estrutura diferente das specs, **pare**, explique e proponha a alteração da spec; só continue após o usuário aprovar.
3. **Uma tarefa por vez** (`T-xxx`), dentro do escopo descrito em `05`. Nada de "melhorias" fora do escopo — anote como sugestão no Log.
4. Não inicie tarefa com dependência que não esteja `Concluída`.
5. Toda tarefa termina com: testes passando, checks limpos, specs afetadas atualizadas e `05-acompanhamento.md` atualizado (README §6 — Definição de Pronto).
6. Respeite as regras de camadas (`SPECS/03-arquitetura.md` §4.2): `gspread` só em `backend/app/infra/` e `repositories/planilha/`; regras de negócio só em `services/`; frontend não calcula totais.
7. Não adicione dependências fora de `SPECS/02-definicoes-tecnicas.md` §1 sem registrar um ADR.
8. Angular 22: zoneless (estado de tela sempre em signals), standalone, `@if/@for`, `inject()`, `OnPush`, formulários reativos tipados. Sem APIs experimentais/developer preview (ex.: Signal Forms). Gráficos só via `GraficoDirective` de `shared/grafico/` — não instalar wrappers de gráfico.
9. Commits no formato `T-xxx: <descrição no imperativo>`; faça commit só quando o usuário pedir ou autorizar.
10. Dúvidas de requisito: pergunte ao usuário em vez de supor. Premissas `P-xx` em `01` valem até serem confirmadas.

## Fluxo de trabalho (comandos)

| Comando | Uso |
|---|---|
| `/proxima-tarefa` | Qual tarefa fazer agora |
| `/especificar-feature F-xx` | Criar a spec detalhada de uma feature antes de implementá-la |
| `/implementar-tarefa T-xxx` | Implementar uma tarefa seguindo o ciclo SDD |
| `/revisar-aderencia [F-xx]` | Checar se código e specs estão alinhados |
| `/mudanca-de-requisito <descrição>` | Propagar uma mudança de escopo pelas specs |

## Comandos do projeto (PowerShell)

```powershell
# Backend — em ./backend
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000   # API em http://127.0.0.1:8000/docs
pytest                     # testes (integração: pytest -m integracao, requer SPREADSHEET_ID_TESTE)
ruff check . ; ruff format .

# Frontend — em ./frontend
npm install
npm start                  # http://localhost:4200 (proxy /api → 8000)
npm test
npm run build
```

> Enquanto a tarefa T-001..T-003 não estiver concluída, as pastas `backend/` e `frontend/` ainda não existem.
