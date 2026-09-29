---
description: Mostra o estado do roadmap e recomenda a próxima tarefa desbloqueada
---

Você vai indicar qual tarefa deve ser feita agora. **Não altere nenhum arquivo.**

1. Leia `SPECS/05-acompanhamento.md` (seções 1, 2 e 4).
2. Se existir alguma tarefa `Iniciada`, informe-a primeiro e recomende concluí-la antes de qualquer outra (a menos que esteja com `BLOQUEIO:` nas Notas — nesse caso, mostre o bloqueio).
3. Liste as tarefas `Não iniciada` cujas dependências estão **todas** `Concluída` ("desbloqueadas").
4. Recomende **uma** delas, nesta ordem de prioridade:
   a. tarefa de uma feature do caminho crítico (`SPECS/04-roadmap.md` §2);
   b. tarefa de uma feature já iniciada;
   c. menor ID.
5. Para a tarefa recomendada, informe:
   - ID, escopo, feature e camada;
   - se já existe spec da feature em `SPECS/features/` — se **não** existir, o próximo passo é `/especificar-feature F-xx`; se existir, é `/implementar-tarefa T-xxx`;
   - premissas `P-xx` ainda "A confirmar" em `SPECS/01-requisitos.md` que afetem essa tarefa.
6. Termine com um resumo de uma linha do progresso geral (concluídas / total).
