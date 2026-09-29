---
description: Verifica se o código está aderente às specs e relata divergências (sem corrigir)
argument-hint: "[F-xx | tudo]"
---

Faça uma revisão de aderência entre código e specs. Escopo: **$ARGUMENTS** (se vazio, considere todas as features com status `Iniciada` ou `Concluída`). **Não corrija nada nesta etapa — apenas relate.**

Verifique:

1. **Contrato da API** — endpoints implementados em `backend/app/api/routers/` x tabela `SPECS/03-arquitetura.md` §6.1 (método, caminho, códigos de status, formato de erro §6.2). Endpoints a mais ou a menos.
2. **Modelo da planilha** — `backend/app/infra/schema_planilha.py` x `SPECS/03-arquitetura.md` §5 (abas, nomes e ordem das colunas, enums).
3. **Regras de camadas** — imports proibidos segundo `SPECS/03-arquitetura.md` §4.2 (ex.: `gspread` ou `fastapi` dentro de `services/`).
4. **Regras de negócio** — para cada RN-xx das features no escopo, existe teste que a cubra (procure `RN_xx` nos nomes/docstrings de testes)?
5. **Critérios de aceite** — CA-xx.y das features no escopo marcados como atendidos na spec da feature e com evidência.
6. **Dependências** — pacotes em `requirements*.txt` e `package.json` x `SPECS/02-definicoes-tecnicas.md` §1 / ADRs.
7. **Acompanhamento** — tarefas `Concluída` em `SPECS/05-acompanhamento.md` têm o código correspondente; contagens do §1 batem com a tabela §4.
8. **Segurança** — `credentials.json` e `.env` ignorados pelo git; nenhuma credencial no código ou nos testes.

Produza um relatório com: ✅ aderente · ⚠️ divergência (arquivo, linha, o que diz a spec, o que faz o código, sugestão: corrigir código **ou** atualizar spec) · ❓ spec ambígua. Termine perguntando ao usuário quais divergências tratar e registre a revisão no Log de `SPECS/05-acompanhamento.md`.
