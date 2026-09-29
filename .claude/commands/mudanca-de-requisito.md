---
description: Analisa o impacto de uma mudança de escopo e a propaga pelas specs (01 → 02/03 → 04 → 05)
argument-hint: <descrição da mudança>
---

O usuário quer a seguinte mudança: **$ARGUMENTS**

**Não escreva código.** Siga os passos:

1. **Entender** — leia `SPECS/01-requisitos.md` inteiro e `SPECS/04-roadmap.md` §2–§4. Se a mudança for ambígua, faça até 3 perguntas objetivas antes de continuar.
2. **Análise de impacto** — apresente:
   - requisitos/regras novos, alterados ou removidos (IDs novos seguem a numeração; nunca renumere; removidos ficam `(removido)`);
   - premissas `P-xx` afetadas;
   - impacto técnico em `SPECS/02-definicoes-tecnicas.md` (nova dependência → ADR) e `SPECS/03-arquitetura.md` (endpoints, colunas da planilha, `versao_schema`, telas);
   - features/tarefas afetadas: novas (próximos IDs livres), alteradas, e tarefas `Concluída` que precisarão de retrabalho (viram **novas** tarefas; não reabra tarefas concluídas);
   - efeito no grafo de dependências e no caminho crítico.
3. **Aguarde aprovação** do usuário para a análise.
4. **Aplicar**, nesta ordem: `01` → `02`/`03` → `04` (features, grafo, matriz de rastreabilidade) → `05` (novas tarefas `Não iniciada`, resumo, Log) → specs de feature afetadas (seção "Revisões"). Em cada documento alterado, suba a versão e acrescente linha no Histórico de alterações.
5. Conferir consistência: todo REQ está na matriz de `04`; toda tarefa nova está em `05`; os grafos Mermaid continuam válidos.
6. Resuma o que mudou em cada arquivo.
