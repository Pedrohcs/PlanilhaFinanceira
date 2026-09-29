---
description: Cria a spec detalhada de uma feature (SPECS/features/F-xx-*.md) a partir do template
argument-hint: F-xx
---

Crie a spec detalhada da feature **$ARGUMENTS**. **Não escreva código de aplicação nesta etapa.**

1. Leia:
   - `SPECS/04-roadmap.md` — a seção da feature $ARGUMENTS (objetivo, requisitos, dependências, tarefas);
   - `SPECS/05-acompanhamento.md` — as linhas das tarefas dessa feature;
   - `SPECS/01-requisitos.md` — somente os REQ, CA, RN e premissas P-xx citados;
   - `SPECS/03-arquitetura.md` — as seções de camadas, planilha, contrato da API e frontend relevantes;
   - `SPECS/02-definicoes-tecnicas.md` — só o necessário para a camada da feature;
   - `SPECS/features/_TEMPLATE.md`.
2. Se já existir `SPECS/features/$ARGUMENTS-*.md`, não sobrescreva: mostre o que falta e pergunte se deve atualizar.
3. Crie `SPECS/features/$ARGUMENTS-<nome-curto-em-kebab-case>.md` preenchendo **todas** as seções do template:
   - critérios de aceite copiados dos requisitos + refinados, testáveis e sem ambiguidade;
   - casos de borda concretos (valores, datas, limites);
   - trecho exato do contrato da API/colunas usadas;
   - plano de testes com nomes de teste que citem `RN_xx`/`CA_xx_y`;
   - divisão por tarefa com arquivos principais.
4. **Não invente requisito.** Tudo que não estiver definido nas specs superiores vai para "Questões em aberto". Se algo contradiz 01/02/03, aponte e sugira `/mudanca-de-requisito`.
5. Status da spec: `Rascunho` se houver questões em aberto; `Aprovada` só depois que o usuário responder.
6. Em `SPECS/05-acompanhamento.md` §2, preencha a coluna "Spec da feature" com o link do arquivo criado.
7. Ao final, apresente um resumo curto e **faça as perguntas em aberto ao usuário**.
