# F-xx — <Nome da feature>

<!--
Como usar este template:
- Copie para SPECS/features/F-xx-<nome-curto>.md (ex.: F-12-parcelamentos.md). O comando /especificar-feature faz isso.
- Preencha ANTES da primeira tarefa da feature. Seja específico: esta spec é o que o Claude Code segue ao implementar.
- Não contradiga 01/02/03. Se precisar, altere o documento superior primeiro.
- Apague estes comentários ao preencher.
-->

| Campo | Valor |
|---|---|
| Feature | F-xx |
| Marco | Mx |
| Status | Rascunho · Aprovada · Concluída |
| Requisitos | REQ-xx, REQ-yy |
| Regras | RN-xx, RN-yy |
| Depende de | F-xx (concluída?) |
| Tarefas | T-xxx, T-yyy |
| Atualizado em | AAAA-MM-DD |

## 1. Objetivo

<Uma ou duas frases: que problema do usuário esta feature resolve.>

## 2. Escopo

**Inclui**
- ...

**Não inclui** (e onde será tratado)
- ... (F-yy)

## 3. Comportamento detalhado

<Passo a passo do ponto de vista do usuário e do sistema. Cite REQ/RN em cada ponto.>

1. ...

## 4. Critérios de aceite

<Copie os CA dos requisitos cobertos e acrescente os refinados desta feature com sufixo da feature, ex.: CA-07.4 (F-12). Formato Dado / Quando / Então.>

- [ ] **CA-xx.1** Dado ..., quando ..., então ...
- [ ] **CA-xx.2** ...

## 5. Casos de borda

| Caso | Comportamento esperado | Regra |
|---|---|---|
| ... | ... | RN-xx |

## 6. Contrato e dados

**API** (trecho de `03` §6 usado/alterado por esta feature)

| Método | Caminho | Entrada | Saída |
|---|---|---|---|
| | | | |

**Planilha** (abas/colunas lidas ou escritas; alterações de schema exigem atualizar `03` §5 e `versao_schema`)

- ...

## 7. Interface (se houver frontend)

- Tela/rota: ...
- Componentes: ...
- Estados: carregando · vazio · erro · sucesso
- Mensagens ao usuário (pt-BR): ...

## 8. Plano de testes

| Teste | Nível | Cobre |
|---|---|---|
| `test_..._RN_xx` | unitário BE | RN-xx |
| `test_..._CA_xx_y` | API BE | CA-xx.y |
| `....spec.ts` | unitário FE | ... |

## 9. Divisão em tarefas

| Tarefa | Escopo nesta feature | Arquivos principais |
|---|---|---|
| T-xxx | ... | `backend/app/...` |

## 10. Decisões tomadas nesta feature

| Decisão | Motivo | Virou ADR? |
|---|---|---|
| | | |

## 11. Questões em aberto

<Perguntas para o usuário. A feature só passa para "Aprovada" quando esta lista estiver vazia ou com respostas registradas.>

- [ ] ...

## Revisões

| Data | Alteração |
|---|---|
| AAAA-MM-DD | Criação |
