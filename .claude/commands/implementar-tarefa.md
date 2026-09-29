---
description: Implementa uma tarefa T-xxx seguindo o ciclo SDD (plano, testes, código, verificação, atualização das specs)
argument-hint: T-xxx
---

Implemente a tarefa **$ARGUMENTS** seguindo rigorosamente o ciclo abaixo.

## 1. Pré-condições (pare se alguma falhar)
- Em `SPECS/05-acompanhamento.md`, localize $ARGUMENTS. Todas as dependências devem estar `Concluída`. Se não estiverem, diga quais faltam e pare.
- Localize a spec da feature em `SPECS/features/`. Se não existir ou estiver `Rascunho` com questões em aberto, pare e sugira `/especificar-feature F-xx`.
- Se outra tarefa estiver `Iniciada`, avise e pergunte se deve continuar.

## 2. Contexto
Leia a spec da feature e apenas as seções indicadas em `SPECS/README.md` §5 para a camada desta tarefa. Não leia `credentials.json`.

## 3. Marcar início
Em `SPECS/05-acompanhamento.md`: status `Iniciada`, coluna Início com a data de hoje, linha no Log, status da feature em §2 e mapa em §3 (se for a primeira tarefa da feature).

## 4. Plano (aguarde aprovação)
Apresente ao usuário:
- arquivos a criar/alterar;
- testes a escrever (com o CA/RN que cada um cobre);
- qualquer ponto em que a spec seja insuficiente ou precise mudar.
**Aguarde aprovação antes de editar código.** Se a spec precisar mudar, proponha a alteração (spec primeiro) e só siga após aprovação.

## 5. Implementação
- Para regras de negócio (RN-xx), escreva o teste antes ou junto do código.
- Siga `SPECS/02-definicoes-tecnicas.md` §7 (convenções) e `SPECS/03-arquitetura.md` §4.2 (camadas).
- Fique dentro do escopo da tarefa. Ideias extras → anote no Log como sugestão.

## 6. Verificação
- Backend: `pytest` e `ruff check .` (em `backend/`). Frontend: `npm test -- --watch=false` e `npm run build` (em `frontend/`).
- Percorra cada CA/RN da tarefa e informe como foi verificado (teste automatizado ou verificação manual descrita).

## 7. Atualizar specs
- Endpoint, coluna, pasta ou módulo novo/alterado → `SPECS/03-arquitetura.md` (e histórico de alterações).
- Dependência ou decisão técnica nova → ADR em `SPECS/02-definicoes-tecnicas.md` §9.
- Spec da feature: marque os CA atendidos e registre decisões tomadas.

## 8. Marcar conclusão
Em `SPECS/05-acompanhamento.md`: status `Concluída`, Conclusão com a data, Notas com um resumo curto, Log, resumo §1 (contagens e próxima tarefa disponível), e — se for a última tarefa da feature — status da feature em §2 e mapa em §3.

## 9. Commit
Proponha a mensagem `$ARGUMENTS: <descrição no imperativo>` e a lista de arquivos. Faça o commit somente se o usuário autorizar. Confirme que `credentials.json` e `.env` não estão no stage.
