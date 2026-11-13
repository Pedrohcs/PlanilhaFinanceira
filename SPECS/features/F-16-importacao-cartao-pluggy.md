# F-16 — Importação do cartão de crédito (Meu Pluggy)

| Campo | Valor |
|---|---|
| Feature | F-16 |
| Marco | M5 |
| Status | Aprovada |
| Requisitos | REQ-17 (CA-17.1 a .7), REQ-18 (CA-18.1 a .4), REQ-19 (CA-19.1 a .5), REQ-20 (CA-20.1 a .3); acréscimos: CA-03.4, CA-03.5, CA-08.3, CA-11.5 |
| Regras | RN-01, RN-03 (P-02 confirmada em 2026-11-12), RN-04, RN-06, RN-08, RN-12, RN-14, RN-15, RN-17 a RN-24; RNF-01, RNF-02, RNF-05, RNF-08, RNF-09 |
| Depende de | F-14 (**Concluída**); T-042 também de F-15 (T-035, **Iniciada**) |
| Tarefas | T-036, T-037, T-038, T-039, T-040, T-041, T-042 |
| Atualizado em | 2026-11-13 |

> **IDs de critério:** herdados de `01` mantêm o ID original (**CA-17.1** …). Os refinados usam **`CA-F16.y`**.
>
> Marcas **(Qn)** apontam a decisão do usuário registrada em §11. Referências técnicas: `02` §11 (Pluggy), `03` §4.4 (algoritmo), `03` §5.7–5.8 (abas novas), `03` §6 (contrato).

---

## 1. Objetivo

Os gastos do Pedro são quase todos no cartão de crédito (Itaú e Nubank). Em vez de digitá-los, o aplicativo os busca no **Meu Pluggy** (Open Finance, plano gratuito de uso pessoal) e grava na planilha como lançamentos — sem duplicar o que já foi lançado à mão, por recorrência ou por parcelamento, acompanhando as mudanças que o banco fizer e sem nunca passar por cima do que o usuário editou.

---

## 2. Escopo

**Inclui**
- Configuração por `backend/.env` (`PLUGGY_CLIENT_ID`, `PLUGGY_CLIENT_SECRET`, `PLUGGY_ITEM_IDS`, `PLUGGY_DATA_INICIAL`) **(Q1, Q13)**.
- Cliente da API da Pluggy no backend (`infra/pluggy_client.py`, `02` §11): autenticação, situação das conexões, cartões, transações paginadas.
- Schema da planilha versão 2: abas `Cartoes` e `Importacoes` (livro-razão), categorias reservadas "A classificar" e migração automática (`03` §5.4, §5.7, §5.8).
- `importacao_service` com o algoritmo de `03` §4.4: importa direto em `Lancamentos` **(Q2)**, inclui pendentes **(Q6)**, compras e estornos/cashback **(Q4, Q16)**, categoria aprendida ou "A classificar" **(Q5)**, conciliação **(Q8, Q9)**, atualização/remoção dos não editados **(Q7, Q11)**, excluídos não voltam, proteções.
- Endpoints `GET /api/cartoes`, `GET /api/cartoes/conexoes`, `POST /api/importacoes/pluggy`; `vinculo` e filtro `cartao` em `GET /api/lancamentos`; `reservada` nas categorias.
- Importação na abertura do app (depois das recorrências) e pelo botão **"Buscar do cartão"** **(Q3)**.
- Página `/cartoes` **(Q14)** com aviso de validade 30 dias antes **(Q15)**.
- Listagem: ícone com o cartão + filtro "Cartão" **(Q19)**; parcela importada sem "excluir parcelamento inteiro"; categoria reservada sem excluir/desativar.
- README e roteiro E2E com o item real.

**Não inclui** (e onde está)
- Conectar/autorizar bancos pelo app, widget Pluggy Connect, webhooks, forçar atualização no banco — `01` §6, ADR-17. A Pluggy atualiza uma vez por dia.
- Conta corrente, investimentos, faturas (fechamento/vencimento) — `01` §6.
- Categoria e estabelecimento da Pluggy (exigem plano Pro) — `02` §11.1.
- Aplicar uma categoria a vários "A classificar" iguais de uma vez **(Q17)** — `01` §6.
- Agrupar parcelas importadas num parcelamento (a Pluggy não informa) — RN-08.
- Desfazer a duplicidade de uma recorrência cadastrada depois que o gasto do mês já foi importado (§5, borda 30).

---

## 3. Comportamento detalhado

### 3.1 Configuração (T-037)

1. Integração **ligada** quando `PLUGGY_CLIENT_ID`, `PLUGGY_CLIENT_SECRET` e `PLUGGY_ITEM_IDS` estão preenchidas e `PLUGGY_DATA_INICIAL` está vazia ou é uma data `AAAA-MM-DD` válida. `PLUGGY_ITEM_IDS` é separada por vírgula; espaços e repetidos são descartados, mantendo a ordem.
2. **Desligada**, sem aviso, quando as três estão vazias (CA-17.6).
3. **Incompleta/inválida** em qualquer outro caso: tratada como desligada, e `GET /api/cartoes` devolve `erro_configuracao` com a primeira causa, nesta ordem: "Falta PLUGGY_CLIENT_ID no backend/.env." · "Falta PLUGGY_CLIENT_SECRET no backend/.env." · "Falta PLUGGY_ITEM_IDS no backend/.env." · "PLUGGY_DATA_INICIAL deve estar no formato AAAA-MM-DD.". O backend sobe normalmente (diferente de `SPREADSHEET_ID`).
4. Nenhuma chamada à Pluggy no lifespan; a `apiKey` é pedida na primeira necessidade e fica só em memória (`02` §11.3). Nada de `PLUGGY_CLIENT_SECRET`/`apiKey` em log, resposta da API ou teste (RNF-05).

### 3.2 Conexões e cartões (T-037, T-038)

1. Para cada `itemId`: `GET /items/{id}` → `situacao` pela tabela de `02` §11.4. Importam: `OK`, `PARCIAL`, `ATUALIZANDO`, `DESATUALIZADA`. Não importam (puladas, as outras seguem — CA-20.2): `NAO_ENCONTRADA`, `AUTORIZACAO_VENCIDA`, `ERRO_LOGIN`.
2. `aviso_validade` = `consentExpiresAt` a 30 dias ou menos de hoje **(Q15)**; vencida é `AUTORIZACAO_VENCIDA`.
3. Cartões = contas `CREDIT_CARD` do item. Cada uma vira/atualiza uma linha de `Cartoes` (`03` §5.7). Rótulo: `"<banco> •<final>"` ("Nubank •1234"); sem final, `"<banco> · <nome>"`.
4. **Re-chave:** conta com id desconhecido, quando existe **exatamente um** cartão conhecido com o mesmo banco e final cujo id não apareceu em nenhum item nesta execução → é o mesmo cartão com id novo (ex.: autorização renovada); o cartão e as linhas dele no livro-razão passam ao id novo e a janela **não** é a da primeira importação.
5. **Janela (RN-23):** cartão sem `ultima_importacao` → desde `PLUGGY_DATA_INICIAL` (vazia → dia 1º do mês corrente); senão desde `max(PLUGGY_DATA_INICIAL, hoje − 60 dias)`. Sem data final **(Q10)**.

### 3.3 O que entra e como (RN-17, RN-18) (T-038)

| Transação | Resultado |
|---|---|
| `amount > 0` (compra, parcela, tarifa, juros, IOF, anuidade) | **Gasto**, forma `CREDITO` |
| `amount < 0` e `operationType` ∈ {`ESTORNO`, `CASHBACK`} | **Receita**, forma `CREDITO` |
| `amount < 0` com qualquer outro `operationType` ou `null` (pagamento de fatura, crédito sem tipo) | Ignorada **(Q16)** |
| Valor zero; moeda ≠ BRL sem `amountInAccountCurrency` | Ignorada |
| `status` `PENDING` ou `POSTED` | Os dois entram **(Q6)** |

Campos do lançamento novo: `id` determinístico (ADR-18); `data` = `date` em UTC−3 (`2026-11-12T01:30:00.000Z` → `2026-11-11`); `descricao` = `description` com espaços colapsados, sem espaços nas pontas, cortada em 100 ("Compra no cartão" se vazia); `valor` = módulo de `amountInAccountCurrency` (se houver) ou de `amount`, 2 casas; `categoria_id` por §3.4; `forma_pagamento` = `CREDITO`; `observacao` vazia; `parcela_numero`/`parcela_total` = `installmentNumber`/`totalInstallments` quando 2 ≤ N ≤ 48 e 1 ≤ k ≤ N (senão vazios); `parcelamento_id` e `recorrencia_id` vazios; `criado_em` = `atualizado_em` = agora.

### 3.4 Categoria (RN-19) (T-038)

1. **Descrição normalizada:** sem acentos, minúsculas, espaços colapsados, e sem o sufixo de parcela que casar com `\s*(parc(ela)?\.?\s*)?\d{1,2}\s*/\s*\d{1,2}$` (aplicado uma vez). Ex.: "LOJA X PARC 03/10" → "loja x"; "Ifood *Restaurante 1/2" → "ifood *restaurante"; "Uber   Trip" → "uber trip".
2. Procura, entre os lançamentos da planilha **e** os incluídos antes nesta execução, os do **mesmo tipo** com a mesma descrição normalizada cuja categoria exista, esteja **ativa** e não seja reservada. Vale a do mais recente (maior `data`, depois maior `atualizado_em`).
3. Nenhum → `a-classificar` (gasto) ou `a-classificar-receita` (receita) **(Q5)**.
4. Aprende com **qualquer** lançamento (manual, recorrência, parcela, importado) — basta a descrição bater.

### 3.5 Conciliação (RN-20) (T-038)

1. Só para transação que viraria **gasto** e não tem linha no livro-razão **(Q8)**.
2. Candidatos: lançamentos `GASTO` com `forma_pagamento = CREDITO`, **não vinculados** (sem linha `IMPORTADA`/`CONCILIADA` apontando para eles) e não conciliados antes nesta execução. Vale para os criados à mão, por recorrência ou por parcelamento.
3. Transação **sem parcela** ↔ candidato **sem parcela**: valor **igual** e |datas| ≤ **3 dias**.
4. Transação **k/N** ↔ candidato que seja a parcela **k/N**: |valores| ≤ **R$ 0,05** e |datas| ≤ **40 dias** **(Q9)**.
5. Desempate: menor |Δdata|, menor |Δvalor|, menor `criado_em`, menor `id`. Um lançamento, uma transação (CA-18.4).
6. Vinculado: nada muda no lançamento — data, valor, descrição, categoria, observação continuam os do usuário **(Q18)**; só nasce a linha `CONCILIADA`.

### 3.6 Depois de importado (RN-21, RN-22, RN-24) (T-038)

1. **Editado** = `data`, `tipo`, `valor` ou `descricao` do lançamento diferente da linha do livro-razão. Trocar **só** categoria e/ou observação **não** congela **(Q11)**.
2. Transação já conhecida que mudou: importado não editado → atualiza data, tipo, valor e descrição, preserva categoria e observação (se o **tipo** mudou, a categoria é refeita por §3.4 para o novo tipo; a forma continua `CREDITO`); editado → nada no lançamento; conciliado → nada no lançamento. Em todos, o livro-razão guarda os valores novos (exceto no editado, que guarda só o `status_pluggy`).
3. Transação que **sumiu** (não veio, com data ≥ início da janela): importado não editado → **removido**; importado editado → fica, sem vínculo; conciliado → vínculo desfeito, lançamento intocado (pode ser vinculado de novo depois) **(Q7)**.
4. Lançamento importado ou vinculado que o usuário **excluiu** (no app ou na planilha) → a linha vira `EXCLUIDA` e a transação nunca mais gera nem vincula nada, mesmo reapresentada pelo banco com outro id (CA-19.5).
5. **Trava de segurança:** cartão que não devolveu **nenhuma** transação na janela → nenhuma remoção dele nesta execução (a doc da Pluggy avisa que autorização vencida devolve leituras vazias).
6. **Reapresentação pelo banco** (id novo): reconhecida por `providerId` ou, sem ele, pela chave `(cartão, data, tipo, valor, descrição normalizada)` entre as linhas cujo id antigo não veio nesta execução → é a mesma transação (§3.6.2). Se mudou valor/data/descrição **e** não tem `providerId`, ela parece nova: o importado antigo é removido (se não editado) e a nova entra — e a categoria do antigo é **reaprendida** por §3.4, porque as remoções só acontecem depois que todas as transações foram processadas.

### 3.7 Escritas e falhas (T-038)

1. Ordem e limite de `03` §4.4: até 7 chamadas de escrita, todas em lote. Sem novidade nenhuma, só `Cartoes` é atualizada (`ultima_importacao`).
2. Falha no meio (Google ou Pluggy): a execução seguinte se recupera sem duplicar (id determinístico, `03` §4.4). Erro da Pluggy antes de qualquer escrita → nada gravado.
3. Uma importação por vez no processo: a segunda recebe 409 `IMPORTACAO_EM_ANDAMENTO` (não espera).
4. Planilha inacessível → 503 de F-02 (banner, como qualquer tela). Pluggy inacessível → 502 `PLUGGY_*` (nunca o banner — RNF-09).

### 3.8 API (T-039)

1. `GET /api/cartoes` — só planilha + configuração; nunca chama a Pluggy; responde mesmo com a integração desligada (lista os cartões já conhecidos). Ordem: banco, depois final (sem acento/caixa).
2. `GET /api/cartoes/conexoes` — chama a Pluggy (`GET /items/{id}` e cartões de cada item); nenhuma escrita; desligada → 409 `PLUGGY_NAO_CONFIGURADA`; Pluggy fora → 502. `ultima_importacao` de cada cartão vem de `Cartoes`.
3. `POST /api/importacoes/pluggy` — executa §3.2–§3.7 e devolve `ResultadoImportacao` (`03` §6.3). Conexões puladas vêm com `importou: false` e o motivo; não é erro HTTP.
4. `GET /api/lancamentos` ganha `vinculo` em cada item e o filtro `cartao` (`<id>` ou `SEM_CARTAO`), combinado em E com os demais; totais seguem o filtro (CA-03.2). Valor de `cartao` desconhecido → lista vazia (como `categoria_id`).
5. Categorias: `reservada` no JSON; `DELETE` de reservada → 409 `CATEGORIA_RESERVADA` "A categoria "A classificar" é usada pela importação dos cartões e não pode ser excluída."; `PUT` com `ativa: false` numa reservada → 409 `CATEGORIA_RESERVADA` "A categoria "A classificar" é usada pela importação dos cartões e não pode ser desativada." (nome atual da categoria na mensagem).

### 3.9 Frontend (T-040, T-041)

1. **Shell:** com `CartoesStore.configurada`, botão de ícone **"Buscar do cartão"** (`credit_card`, dica "Buscar do cartão") ao lado de "Recarregar dados"; durante a busca, desabilitado com indicador. Link **"Cartões"** na navegação sempre visível.
2. **Abertura** (`03` §7.2): `GET /api/cartoes` junto com o health; depois da sincronização de recorrências (resposta que não seja 503/backend fora) e se `configurada`, `POST /api/importacoes/pluggy`. **Um** aviso consolidado:
   - partes, nesta ordem e só as não vazias: recorrências ("3 lançamentos recorrentes gerados.") · cartões ("Cartões: 5 incluídos, 2 vinculados, 1 atualizado, 1 removido." — singular "1 incluído", "1 vinculado"…; partes zeradas omitidas) · falha ("Não foi possível buscar os cartões: <mensagem da API>.") · atenção ("Há avisos em Cartões." quando alguma conexão tem `importou: false` ou `aviso_validade`);
   - com "atenção", o aviso tem a ação **"Ver"** (vai para `/cartoes`) e dura 10 s; sem, 5 s e "Fechar";
   - nada a dizer → nenhum aviso;
   - `inseridos + conciliados + atualizados + removidos > 0` → `DadosStore.versao++`; `CartoesStore` recarrega sempre.
   - O mesmo encadeamento roda no "Tentar novamente" que restabelece a conexão.
3. **Botão "Buscar do cartão"** (shell ou página): mesmo resultado em aviso próprio; sem novidade → "Nenhuma novidade nos cartões."; erro → a mensagem da API; 409 em andamento → "Já existe uma busca nos cartões em andamento.".
4. `Avisos.mostrar` ganha ação opcional (`{ rotulo, aoClicar }`) e duração; o `MatSnackBar` continua sob demanda.
5. **Interceptor:** `PLUGGY_NAO_CONFIGURADA`, `PLUGGY_CREDENCIAIS_INVALIDAS`, `PLUGGY_INDISPONIVEL`, `IMPORTACAO_EM_ANDAMENTO` não abrem aviso nem vão ao `ConexaoStore` (`03` §8.4).
6. **Página `/cartoes`** (título "Cartões"):
   - topo: botão **"Buscar do cartão"** (primário, só ligada) e a nota "O Meu Pluggy atualiza os dados dos bancos uma vez por dia.";
   - **desligada:** estado "Integração com o Meu Pluggy não configurada." + `erro_configuracao` (se houver) + o passo a passo de `02` §11.2 resumido em 4 passos + "Depois, reinicie o aplicativo."; se houver cartões conhecidos, lista "Cartões conhecidos";
   - **ligada:** carrega `GET /api/cartoes/conexoes`; um cartão (painel) por conexão: banco (ou "Conexão <itemId>" se não encontrada), selo da situação (verde: Atualizada/Atualizada parcialmente; neutro: Atualização em andamento; amarelo: Desatualizada; vermelho: Erro de login/Autorização vencida/Não encontrada) e a mensagem de `02` §11.4; "Dados do banco atualizados em dd/mm/aaaa hh:mm" (ou "—"); "Autorização válida até dd/mm/aaaa"; com `aviso_validade`: alerta "A autorização vence em N dias." (ou "A autorização venceu.") + como renovar ("Dashboard da Pluggy → sua aplicação → Demo → Connect Account → MeuPluggy. Se o id da conexão mudar, atualize PLUGGY_ITEM_IDS no backend/.env e reinicie."); lista dos cartões com "Última importação: dd/mm/aaaa hh:mm" ou "Ainda não importado";
   - estados: carregando · erro 502 ("Não foi possível consultar o Meu Pluggy: <mensagem>" + "Cartões conhecidos" do `CartoesStore` — CA-20.3) · depois de buscar, recarrega as conexões;
   - responsiva (≥ 360 px), painéis empilhados.
7. **Listagem `/lancamentos`** (T-041):
   - ícone `credit_card` ao lado da descrição quando `vinculo != null`, com dica/`aria-label` "Importado · Nubank •1234" ou "Vinculado ao cartão · Nubank •1234" (CA-03.4); convive com "k/N" e com o ícone de recorrência;
   - filtro **"Cartão"** (só se `CartoesStore` tem ≥ 1 cartão): "Todos", "Sem cartão", e um item por cartão (rótulo); na URL como `cartao=` (`replaceUrl`, F-07 Q1) (CA-03.5);
   - menu ⋮ de parcela **sem** `parcelamento_id`: sem "Excluir parcelamento inteiro" (CA-08.3);
   - diálogo de edição de um **importado** mostra a dica "Veio do cartão. Mudar data, valor, descrição ou tipo faz a importação deixar de atualizar este lançamento." (sem dica para vinculados).
8. **Categorias** (T-041): reservada mostra só "Editar" (nome e cor) no menu ⋮, com a dica "Usada pela importação dos cartões" (CA-11.5).

---

## 4. Critérios de aceite

**Herdados de `01`**

- [ ] **CA-03.4** Dado um lançamento importado ou vinculado a um cartão, quando a listagem abre, então ele é identificado por um ícone com o nome do cartão.
- [ ] **CA-03.5** Dado o filtro "Cartão", quando o usuário escolhe um cartão, então aparecem só os importados ou vinculados a ele; "Sem cartão", só os demais; os totais acompanham o filtro.
- [ ] **CA-08.3** Dado uma parcela importada, então ela exibe "k/N", é editada e excluída individualmente e não oferece "excluir parcelamento inteiro".
- [ ] **CA-11.5** Dado a categoria "A classificar", então o usuário pode renomeá-la e trocar a cor, mas não excluí-la nem desativá-la.
- [ ] **CA-17.1** a **CA-17.7**, **CA-18.1** a **CA-18.4**, **CA-19.1** a **CA-19.5**, **CA-20.1** a **CA-20.3** — texto em `01` §3 ("Importação do cartão de crédito").

**Refinados — configuração e schema (T-036, T-037)**

- [ ] **CA-F16.1** Dado as três variáveis `PLUGGY_*` obrigatórias vazias, quando o backend sobe, então `GET /api/cartoes` → `configurada: false`, `erro_configuracao: null`, e `POST /api/importacoes/pluggy` → 409 `PLUGGY_NAO_CONFIGURADA`.
- [ ] **CA-F16.2** Dado só `PLUGGY_CLIENT_ID` preenchida, então `configurada: false` e `erro_configuracao` = "Falta PLUGGY_CLIENT_SECRET no backend/.env."; com `PLUGGY_DATA_INICIAL=12/11/2026`, "PLUGGY_DATA_INICIAL deve estar no formato AAAA-MM-DD.".
- [x] **CA-F16.3** Dado uma planilha na versão 1 com dados, quando o backend sobe, então surgem as abas `Cartoes` e `Importacoes` com cabeçalho, as duas "A classificar" em `Categorias`, `versao_schema = 2`, e nenhuma outra linha muda; subir de novo não muda nada.
- [x] **CA-F16.4** Dado uma categoria de gasto do usuário chamada "A classificar" na versão 1, quando migra, então a reservada de gasto entra como "A classificar (importados)" com id `a-classificar`.
- [x] **CA-F16.5** Dado uma planilha vazia, quando prepara, então já nasce na versão 2 com 17 categorias (RN-15).
- [x] **CA-F16.6** Dado `atualizar_varios` com 30 itens, então há **uma** chamada de escrita ao Google; com um `id` inexistente, `NaoEncontrado` e nada gravado.
- [x] **CA-F16.7** Dado `DELETE`/`PUT ativa:false` numa reservada, então 409 `CATEGORIA_RESERVADA`; `PUT` mudando nome e cor → 200.

**Refinados — cliente da Pluggy (T-037)**

- [ ] **CA-F16.8** Dado duas chamadas de dados em menos de 1 h 50 min, então só um `POST /auth`; após um `401` numa chamada de dados, uma nova autenticação e uma nova tentativa.
- [ ] **CA-F16.9** Dado `POST /auth` → 401, então `PluggyCredenciaisInvalidas` → 502 `PLUGGY_CREDENCIAIS_INVALIDAS`; dado 429 nas 4 tentativas, `PluggyIndisponivel` → 502 `PLUGGY_INDISPONIVEL`.
- [ ] **CA-F16.10** Dado 3 páginas de transações (cursor `next`), então `listar_transacoes` devolve todas, na ordem, e para no `next: null`.
- [ ] **CA-F16.11** Dado `GET /items/{id}` → 404, então a conexão sai `NAO_ENCONTRADA` sem exceção; `consentExpiresAt` ontem → `AUTORIZACAO_VENCIDA`; daqui a 30 dias → `aviso_validade: true`; 31 dias → `false`.
- [ ] **CA-F16.12** Nenhum log, mensagem de erro ou resposta da API contém o `PLUGGY_CLIENT_SECRET` nem a `apiKey` (teste captura os logs).

**Refinados — importação (T-038)**

- [ ] **CA-F16.13** Dado `amount = 59.9`, `date = 2026-11-12T01:30:00.000Z`, então gasto de R$ 59,90 em **2026-11-11**, forma `CREDITO` (RN-18).
- [ ] **CA-F16.14** Dado créditos com `operationType` `ESTORNO`, `CASHBACK`, `PAGAMENTO_FATURA`, `PAGAMENTO`, `null`, então só os dois primeiros viram receita e `ignoradas` = 3 (RN-17).
- [ ] **CA-F16.15** Dado `amount = 120` com `amountInAccountCurrency = 650.37`, então valor R$ 650,37; dado `currencyCode = USD` sem `amountInAccountCurrency`, ignorada.
- [ ] **CA-F16.16** Dado parcela 3/10, então `parcela_numero = 3`, `parcela_total = 10`, `parcelamento_id` vazio; dado 1/1 ou 2/60, sem parcela.
- [ ] **CA-F16.17** Dado um lançamento antigo "Uber Trip" em Transporte e um mais recente "UBER  TRIP" em Lazer (inativa), quando chega "Uber trip", então a categoria é Transporte; sem nenhum, "A classificar" (RN-19).
- [ ] **CA-F16.18** Dado "LOJA X PARC 03/10" e um lançamento "Loja X" em Vestuário, então a parcela importada vai para Vestuário.
- [ ] **CA-F16.19** Dado duas transações distintas de R$ 10,00 no mesmo dia e um só manual de R$ 10,00, então uma é vinculada e a outra incluída (CA-18.4).
- [ ] **CA-F16.20** Dado o manual de 4 dias antes com o mesmo valor, então não vincula (inclui); dado a parcela local 2/3 a 41 dias, não vincula (RN-20).
- [ ] **CA-F16.21** Dado um gasto gerado por recorrência (R$ 39,90, dia 10) e a cobrança de R$ 39,90 no dia 12, então vincula (RN-20).
- [ ] **CA-F16.22** Dado um importado não editado com o livro-razão em R$ 100,00 e a transação agora em R$ 102,00 (mesmo id), então o lançamento fica com R$ 102,00 e a categoria trocada pelo usuário é mantida; `atualizados = 1` (CA-19.1, CA-19.3).
- [ ] **CA-F16.23** Dado a mesma situação com o usuário tendo mudado a descrição, então o lançamento não muda e `atualizados = 0` (CA-19.2).
- [ ] **CA-F16.24** Dado um importado não editado cuja transação não veio (data dentro da janela), então o lançamento é removido e a linha vira `REMOVIDA_NA_ORIGEM`; se a transação voltar depois, o lançamento é recriado com o **mesmo id** (CA-19.4).
- [ ] **CA-F16.25** Dado um cartão que devolveu zero transações e tem importados na janela, então nada é removido (RN-24).
- [ ] **CA-F16.26** Dado um importado excluído pelo usuário, quando a importação roda, então a linha vira `EXCLUIDA` e nada é recriado — nem se o banco reapresentar a transação com outro `id` e o mesmo `providerId` (CA-19.5).
- [ ] **CA-F16.27** Dado a transação reapresentada com `id` novo e mesmos valores (sem `providerId`), então nada é duplicado: a linha passa ao id novo.
- [ ] **CA-F16.28** Dado um conciliado cuja transação sumiu, então o lançamento fica intocado e pode ser vinculado de novo numa execução seguinte (RN-20).
- [ ] **CA-F16.29** Dado uma falha simulada na escrita do livro-razão depois dos lançamentos incluídos, quando a importação roda de novo, então nenhum lançamento é duplicado e as linhas que faltavam são criadas.
- [ ] **CA-F16.30** Dado duas importações ao mesmo tempo, então a segunda recebe `ImportacaoEmAndamento` (409).
- [ ] **CA-F16.31** Dado uma importação com novidades em 2 cartões, então há no máximo 7 chamadas de escrita na planilha; sem novidade, só a de `Cartoes`.
- [ ] **CA-F16.32** Dado cartão novo com `PLUGGY_DATA_INICIAL=2026-10-01`, então `dateFrom=2026-10-01`; numa segunda execução em 2026-12-20, `dateFrom=2026-10-21`; sem a variável, a primeira usa o dia 1º do mês corrente (RN-23).
- [ ] **CA-F16.33** Dado uma conta com id novo e o mesmo banco/final de um cartão conhecido cujo id sumiu, então o cartão é re-chaveado, suas linhas também, e nada é reimportado.
- [ ] **CA-F16.34** Dado uma conexão `AUTORIZACAO_VENCIDA` e outra `OK`, então só a segunda importa; o resultado traz as duas, a primeira com `importou: false` (CA-20.2).

**Refinados — API (T-039)**

- [ ] **CA-F16.35** `GET /api/lancamentos?mes=2026-11&cartao=acc-1` devolve só os de `vinculo.cartao_id = acc-1`, com totais deles; `cartao=SEM_CARTAO` só os sem vínculo.
- [ ] **CA-F16.36** Cada item da listagem traz `vinculo` (`IMPORTADO`/`CONCILIADO`, `cartao_id`, `cartao_rotulo`) ou `null`; linhas `REMOVIDA_NA_ORIGEM`/`EXCLUIDA` não geram vínculo.
- [ ] **CA-F16.37** Pluggy fora em `POST /api/importacoes/pluggy` → 502 no envelope de `03` §6.2; planilha fora → 503.

**Refinados — frontend (T-040, T-041)**

- [ ] **CA-F16.38** Integração desligada → sem botão no shell; página `/cartoes` com o estado "não configurada" e o passo a passo; nenhuma chamada de importação na abertura.
- [ ] **CA-F16.39** Abertura com 3 recorrentes geradas e cartões com 2 incluídos → um único aviso "3 lançamentos recorrentes gerados. Cartões: 2 incluídos."; com conexão vencida, + "Há avisos em Cartões." e a ação "Ver".
- [ ] **CA-F16.40** Abertura sem novidade em nada → nenhum aviso; botão sem novidade → "Nenhuma novidade nos cartões.".
- [ ] **CA-F16.41** Erro 502 na importação → nada de banner; na abertura entra no aviso consolidado; no botão, aviso com a mensagem.
- [ ] **CA-F16.42** Página `/cartoes` mostra situação, atualização, validade com alerta ≤ 30 dias, cartões e última importação; com 502, mostra a mensagem e os cartões conhecidos.
- [ ] **CA-F16.43** Listagem: ícone com a dica certa; filtro "Cartão" na URL; parcela importada sem "Excluir parcelamento inteiro"; dica no diálogo de edição de importado.
- [ ] **CA-F16.44** Categorias: reservada só com "Editar".

---

## 5. Casos de borda

| # | Caso | Comportamento esperado | Regra |
|---|---|---|---|
| 1 | Compra às 23:30 de 11/11 (02:30Z de 12/11) | Data 11/11 | RN-18, ADR-19 |
| 2 | Parcela 1/1, 0/5, 2/60 | Sem parcela | RN-18 |
| 3 | Descrição com 140 caracteres / vazia | Cortada em 100 / "Compra no cartão" | RN-06, RN-18 |
| 4 | IOF de compra internacional (positivo, `TARIFA`) | Gasto | RN-17 |
| 5 | Compra em dólar com `amountInAccountCurrency` | Valor em reais | RN-17 |
| 6 | Pagamento de fatura (`PAGAMENTO_FATURA`) | Ignorado | RN-17 |
| 7 | Estorno de uma compra | Receita separada (o gasto original fica) | RN-17 |
| 8 | Dois cafés iguais no mesmo dia | Dois lançamentos (ids distintos) | RN-17 |
| 9 | Pendente R$ 100,00 confirmada R$ 102,00 com o mesmo id | Atualiza se não editado | RN-21 |
| 10 | Pendente some e a confirmada chega com id novo, sem `providerId`, outro valor | Antigo removido (não editado), nova incluída com a categoria reaprendida | RN-19, RN-21 |
| 11 | Usuário só recategorizou | Continua acompanhando | RN-21 (Q11) |
| 12 | Usuário mudou o valor e a transação sumiu | Lançamento fica, sem vínculo | RN-21 |
| 13 | Usuário excluiu um importado | Não volta | RN-22 |
| 14 | Usuário excluiu um vinculado (o manual dele) | A transação também não é importada | RN-22 |
| 15 | Usuário apagou a linha do livro-razão à mão | Transação parece nova; id determinístico encontra o importado e só recria a linha; um vinculado pode ser vinculado de novo | ADR-18 |
| 16 | Parcelamento local R$ 1.000,00/3 (333,34 · 333,33 · 333,33) e banco 333,33 · 333,33 · 333,34 | Vincula as 3 (|Δ| ≤ 0,05) | RN-20 |
| 17 | Parcela local 2/3 em 15/02 e do banco em 28/03 (41 dias) | Não vincula; entra como importada (duplicidade visível; o usuário exclui uma) | RN-20 |
| 18 | Recorrência de R$ 39,90 e cobrança de R$ 44,90 | Não vincula; entra a importada | RN-20 |
| 19 | Manual R$ 50,00 em 10/11, transações R$ 50,00 em 08/11 e 12/11 | A de 08/11 (processada antes, mesma distância) vincula; a de 12/11 entra | RN-20 |
| 20 | Autorização vencida (leituras vazias, item `UPDATED`) | Pulada pelo `consentExpiresAt`; e, se passasse, nada removido (cartão vazio) | RN-24 |
| 21 | Conexão `LOGIN_ERROR` | Pulada, com aviso | RN-24 |
| 22 | `itemId` errado | `NAO_ENCONTRADA`, as outras seguem | RN-24 |
| 23 | Autorização renovada com novo `itemId` e novas contas | Usuário atualiza o `.env`; cartões re-chaveados por banco/final | §3.2.4 |
| 24 | Dois cartões conhecidos com mesmo banco e final | Sem re-chave; conta nova vira cartão novo (janela da data inicial; o reconhecimento por `providerId` evita duplicar o que já foi importado) | §3.2.4 |
| 25 | Parcela com data futura | Entra, conta no mês dela | RN-03, RN-23 |
| 26 | `PLUGGY_DATA_INICIAL` no futuro | Nada antes dela; válida | RN-23 |
| 27 | `PLUGGY_ITEM_IDS` com repetidos/espaços | Normalizada | §3.1 |
| 28 | Categoria aprendida foi desativada | Usa o lançamento anterior com categoria ativa; nenhum → "A classificar" | RN-19 |
| 29 | Usuário renomeou "A classificar" para "Revisar" | Continua sendo a reservada (por id) | RN-24 |
| 30 | Recorrência no crédito cadastrada depois de o gasto do mês já ter sido importado | Duplicidade (a importada já existe; a gerada não é conciliada) — o usuário exclui uma | Fora do escopo |
| 31 | App aberto em duas abas | Uma importação; a outra recebe 409, sem aviso na abertura | §3.7.3 |
| 32 | Planilha cai no meio da importação | 503 → banner; a próxima execução se recupera | §3.7.2 |
| 33 | Edição do usuário e importação na mesma linha ao mesmo tempo | Vale a última escrita | `03` §4.4 |

---

## 6. Contrato e dados

**API** (`03` §6)

| Método | Caminho | Entrada | Saída |
|---|---|---|---|
| GET | `/api/cartoes` | — | `200 Cartoes` |
| GET | `/api/cartoes/conexoes` | — | `200 [Conexao]` · 409 `PLUGGY_NAO_CONFIGURADA` · 502 |
| POST | `/api/importacoes/pluggy` | — | `200 ResultadoImportacao` · 409 `PLUGGY_NAO_CONFIGURADA`/`IMPORTACAO_EM_ANDAMENTO` · 502 · 503 |
| GET | `/api/lancamentos` | + `&cartao=<id>\|SEM_CARTAO` | itens com `vinculo` |
| GET/PUT/DELETE | `/api/categorias...` | — | + `reservada`; 409 `CATEGORIA_RESERVADA` |

Esquemas completos em `03` §6.3.

**Planilha** (`03` §5) — `versao_schema` 2.

- `Lancamentos`: sem colunas novas; parcela importada = `parcela_numero`/`parcela_total` sem `parcelamento_id`; importados com id determinístico.
- `Categorias`: `a-classificar`, `a-classificar-receita` (reservadas).
- `Cartoes` (nova, §5.7) e `Importacoes` (nova, §5.8).

**Pluggy** (`02` §11.3): `POST /auth`, `GET /items/{id}`, `GET /accounts?itemId&type=CREDIT`, `GET /v2/transactions?accountId&dateFrom` (plano B: `GET /transactions`).

---

## 7. Interface

- Rotas: `/cartoes` (nova); `/lancamentos` com `cartao=`.
- Componentes: `features/cartoes/cartoes.page.ts`; `core/api/cartoes.api.ts`, `core/api/importacoes.api.ts`; `core/state/cartoes.store.ts`, `core/state/importacao.ts`; alterações em `app.ts` (botão, link), `conexao.store.ts` (encadeamento), `avisos.ts` (ação), `erro.interceptor.ts`, `lancamentos.page`/`filtros.ts`, `lancamento-form.dialog` (dica), `categorias.page`.
- Estados: carregando · vazio/não configurada · erro (502) · sucesso — §3.9.
- Mensagens (pt-BR): todas as de §3.1, §3.8.5, §3.9 e `02` §11.4/§11.6.

---

## 8. Plano de testes

### 8.1 Backend

| Teste | Nível | Cobre |
|---|---|---|
| `test_migracao_v1_para_v2_preserva_dados__CA_F16_3` · `test_reservada_com_nome_em_uso__CA_F16_4` · `test_planilha_nova_na_v2__RN_15` | unitário (planilha falsa) | CA-F16.3–5, RN-15 |
| `test_atualizar_varios_uma_chamada__CA_F16_6` (planilha e memória equivalentes) | unitário | CA-F16.6 |
| `test_reservada_nao_exclui_nem_desativa__RN_24` | unitário + API | CA-11.5, CA-F16.7 |
| `test_parcela_importada_sem_parcelamento__RN_08` | unitário (modelo) | CA-08.3 |
| `test_configuracao_pluggy_ligada_desligada_incompleta__CA_F16_1` / `_2` | unitário (Settings) | CA-F16.1–2 |
| `test_pluggy_client_*` (`MockTransport`: auth em cache, 401 renova, 429/5xx, paginação, 404 item, sem segredo em log) | unitário | CA-F16.8–12 |
| `test_mapeamento__RN_17` · `test_campos_do_importado__RN_18` · `test_data_em_brasilia__RN_18` | unitário | CA-F16.13–16 |
| `test_categoria_aprendida__RN_19` | unitário | CA-F16.17–18 |
| `test_conciliacao__RN_20` (à vista, parcela, recorrência, desempate, limites 3/40 dias, 0,05) | unitário | CA-18.x, CA-F16.19–21 |
| `test_atualiza_nao_editado__RN_21` · `test_editado_congela__RN_21` · `test_remove_nao_editado__RN_21` | unitário | CA-19.1–4, CA-F16.22–24 |
| `test_excluido_nao_volta__RN_22` | unitário | CA-19.5, CA-F16.26 |
| `test_janela__RN_23` | unitário | CA-F16.32 |
| `test_protecoes__RN_24` (vencida, login, não encontrada, cartão vazio) | unitário | CA-20.2, CA-F16.25, .34 |
| `test_reapresentacao_por_provider_e_chave` · `test_rechave_cartao` · `test_recuperacao_falha_parcial` · `test_trava` · `test_no_maximo_7_escritas` | unitário | CA-F16.27–31, .33 |
| `test_cartoes_*`, `test_conexoes_*`, `test_importacao_*`, `test_lancamentos_filtro_cartao__CA_03_5`, `test_vinculo__CA_03_4` | API | CA-F16.1, .35–37 |
| `test_pluggy_contrato.py` (`-m pluggy`, Sandbox, só leitura) | contrato | `02` §11.3–11.4 |
| `test_bootstrap_e2e` ajustado para 6 abas e versão 2 | integração | CA-F16.3, .5 |

### 8.2 Frontend

| Teste | Cobre |
|---|---|
| `cartoes.store.spec.ts`, `importacao.spec.ts` (uma por vez, `versao++` só com novidade) | §3.9.2–3 |
| `conexao.store.spec.ts` (encadeamento e aviso consolidado; sem importação se desligada) | CA-F16.38–41 |
| `erro.interceptor.spec.ts` (`PLUGGY_*` sem aviso nem banner; 502 sem envelope continua "backend fora") | §3.9.5 |
| `avisos.spec.ts` (ação "Ver") | §3.9.4 |
| `cartoes.page.spec.ts` (desligada, ligada, validade, 502, botão) | CA-F16.42, CA-20.x |
| `app.spec.ts` (botão só ligada; link sempre) | §3.9.1 |
| `lancamentos.page.spec.ts`, `filtros.spec.ts` (ícone, filtro na URL, menu sem "parcelamento inteiro") | CA-03.4, CA-03.5, CA-08.3 |
| `lancamento-form.dialog.spec.ts` (dica no importado) | §3.9.7 |
| `categorias.page.spec.ts` (reservada só com Editar) | CA-11.5 |

### 8.3 Roteiro E2E (T-042, com o item real e a planilha **de teste**)

1. `.env` com `PLUGGY_*` reais e `SPREADSHEET_ID` = planilha de teste versão 1 → subir: abas novas, reservadas, versão 2 (CA-F16.3).
2. Antes, lançar à mão um gasto "Cartão de crédito" igual a uma compra recente do Nubank (valor e data ±3 dias).
3. Abrir o app: aviso consolidado; listagem com ícones; o manual aparece "Vinculado ao cartão" (CA-18.1); nenhum duplicado.
4. Página `/cartoes`: 2 conexões, situação, validade, cartões, última importação (CA-20.x).
5. Recategorizar um "A classificar"; editar o valor de outro; excluir um terceiro; "Buscar do cartão" → "Nenhuma novidade nos cartões." e os três como deixados (CA-19.2, .3, .5).
6. Filtro "Cartão" por cada cartão e "Sem cartão": totais batem (CA-03.5).
7. Trocar `PLUGGY_CLIENT_SECRET` por um inválido e reiniciar → "Buscar do cartão" mostra a mensagem de credenciais, sem banner; o resto do app funciona (CA-17.7, RNF-09).
8. Tirar as `PLUGGY_*` e reiniciar → sem botão, página explica a configuração (CA-17.6).

---

## 9. Divisão em tarefas

| Tarefa | Escopo nesta feature | Arquivos principais |
|---|---|---|
| T-036 | Schema v2, migração, reservadas, modelos/enums, parcela importada, `atualizar_varios`, repositórios `Cartoes`/`Importacoes`, RN-24 nas categorias, `data_em_brasilia`, `normalizar_descricao`; suíte de integração para 6 abas | `infra/schema_planilha.py`, `infra/bootstrap.py`, `domain/modelos.py`, `domain/enums.py`, `domain/datas.py`, `domain/textos.py`, `repositories/base.py`, `repositories/planilha/`, `repositories/memoria/`, `services/categoria_service.py`, `api/schemas.py`, `tests/...` |
| T-037 | `Settings` `PLUGGY_*`, `.env.example`, `requirements.txt` (`httpx`), `pluggy_client.py` + `FontePluggy`, erros de domínio, marcador `pluggy`, teste de contrato; verificação v2 × plano B no item real (Log) | `config.py`, `infra/pluggy_client.py`, `domain/erros.py`, `pyproject.toml`, `tests/unit/test_pluggy_client.py`, `tests/integracao/test_pluggy_contrato.py` |
| T-038 | `importacao_service` completo + `pluggy_falso.py` + testes de RN-17..24; tira a marca *(planejada — F-16)* de RN-17..24 em `01` §4 | `services/importacao_service.py`, `tests/pluggy_falso.py`, `tests/unit/test_importacao_service.py` |
| T-039 | Routers `cartoes`/`importacoes`, composição em `deps.py`/`main.py`, erros 409/502, `vinculo` e filtro `cartao` | `api/routers/cartoes.py`, `api/routers/importacoes.py`, `api/deps.py`, `api/erros.py`, `api/schemas.py`, `services/lancamento_service.py`, `main.py`, `tests/api/...` |
| T-040 | APIs/stores, shell, abertura, avisos, interceptor, página `/cartoes` | `core/api/`, `core/state/`, `core/avisos/avisos.ts`, `core/interceptors/erro.interceptor.ts`, `app.ts`, `app.routes.ts`, `features/cartoes/` |
| T-041 | Listagem (ícone, filtro, menu), dica no diálogo, categorias (reservada), modelos TS | `core/models/`, `features/lancamentos/`, `features/categorias/` |
| T-042 | README, roteiro §8.3 executado, matriz RN → teste | `README.md`, esta spec |

---

## 10. Decisões tomadas nesta feature

| Decisão | Motivo | Virou ADR? |
|---|---|---|
| Caminho Meu Pluggy, sem widget/webhooks; itemIds no `.env` | Plano gratuito escolhido (Q1, Q13); app local | ADR-17 |
| `httpx` como dependência de produção | Já no projeto; `MockTransport` | ADR-16 |
| Livro-razão `Importacoes` + `Cartoes`; `Lancamentos` sem colunas; id determinístico | Excluídos não voltam, "editado" detectável, recuperação de falha parcial | ADR-18 |
| Fuso fixo UTC−3 | Sem horário de verão; evita `tzdata` no Windows | ADR-19 |
| "A classificar" reservada com ids fixos | A importação precisa dela sempre (Q5) | Não (RN-24, `03` §5.2) |
| Parcela importada sem `parcelamento_id` | Pluggy não agrupa parcelas | Não (RN-08, `03` §5.1) |
| Janela: data inicial na 1ª vez, 60 dias depois, sem data final | Cobre pendentes e reapresentações sem reler tudo (Q10) | Não (RN-23) |
| Cartão vazio não remove nada | Autorização vencida devolve vazio | Não (RN-24) |
| Erros da Pluggy em 502 e fora do banner | O banner é da planilha (RNF-09) | Não (`02` §11.6) |
| Abertura: recorrências → importação → um aviso | A importação vincula o que a recorrência gerou; um aviso não apaga o outro | Não (`03` §7.2) |
| Dica no diálogo de edição de um importado | Avisa que editar data/valor/descrição/tipo congela (Q11) | Não |
| Segunda importação simultânea recebe 409 em vez de esperar | Chamada lenta (rede); evita fila de requisições | Não |
| Id reservado ocupado por categoria do **outro tipo** → `SCHEMA_PLANILHA_INVALIDO`, sem escrever nada; do mesmo tipo, a categoria existente vira a reservada como está (T-036) | A importação lançaria gastos em categoria de receita; corrigir exige mexer numa linha do usuário | Não (`03` §5.2) |
| `versao_schema = 2` é a última escrita da migração; dados sem a chave contam como versão 1; na versão 2 a reservada apagada à mão não é recriada (T-036) | Migração retomável sem duplicar; a spec só previa a migração a partir da versão 1 | Não (`03` §5.4) |
| `status_pluggy` como `Literal["PENDING", "POSTED"]` no modelo, sem enum próprio (T-036) | `03` §5.5 não lista enum para ele | Não |
| RN-17..24 entram em `01` marcadas *(planejada — F-16)*; o guarda do RNF-08 ignora RN planejadas até T-038 | Sem isso o `pytest` ficaria vermelho até T-038, inclusive para fechar T-035 (aprovado pelo usuário) | Não (`02` §8) |

---

## 11. Questões em aberto

Nenhuma. Decisões do usuário em 2026-11-12:

- [x] **Q1** Plano gratuito → **Meu Pluggy** (conector MeuPluggy, até 5 conexões, sem prazo).
- [x] **Q2** Destino → **direto em `Lancamentos`** (sem caixa de revisão).
- [x] **Q3** Gatilho → **abertura do app + botão "Buscar do cartão"**.
- [x] **Q4** O que entra → **compras + estornos/cashback** (estorno como receita); pagamento de fatura fora.
- [x] **Q5** Categoria → **aprende pela descrição; senão "A classificar"** (nova categoria, gasto e receita).
- [x] **Q6** Pendentes → **entram**.
- [x] **Q7** Mudança/remoção no banco → **atualiza/remove se o usuário não editou**.
- [x] **Q8** Duplicidade com manuais/recorrências/parcelamentos → **conciliação automática** (mesmo valor, ±3 dias).
- [x] **Q9** Parcelas → **conciliação por k/N**, valor ±R$ 0,05, data ±40 dias.
- [x] **Q10** Primeira importação → **data configurável** (`PLUGGY_DATA_INICIAL`; sem ela, dia 1º do mês corrente).
- [x] **Q11** Trocar só categoria/observação → **não congela**.
- [x] **Q12** P-02 → **confirmada**: mês da compra (data da transação; cada parcela na sua data).
- [x] **Q13** Configuração → **`backend/.env`**.
- [x] **Q14** Interface → **página "Cartões" + botão na barra**.
- [x] **Q15** Validade da autorização → **avisar 30 dias antes**.
- [x] **Q16** Crédito sem tipo identificado → **ignorado** (só `ESTORNO`/`CASHBACK` viram receita).
- [x] **Q17** Aplicar categoria a semelhantes → **não** (fora de escopo).
- [x] **Q18** Lançamento conciliado → **mantém os dados do usuário**.
- [x] **Q19** Listagem → **ícone com o cartão + filtro "Cartão"**.
- [x] Guarda do RNF-08 com RN ainda sem código → **ignorar RN marcadas *(planejada)*** (ajuste no teste já feito nesta mudança).
- [x] Análise de impacto (abas novas, reservada, parcela sem agrupamento, janela de 60 dias, trava contra remoção em massa, 502 `PLUGGY_*`, M5/F-16, T-036..T-042) → **aprovada**.

---

## Revisões

| Data | Alteração |
|---|---|
| 2026-11-13 | **T-036 concluída:** CA-F16.3 a CA-F16.7 atendidos (backend); CA-08.3 e CA-11.5 com a parte do modelo e da API prontas (a tela é da T-041). Três decisões registradas em §10 e em `03` 1.37 (id reservado com o tipo errado; versão gravada por último e planilha sem a chave; `status_pluggy`). Os repositórios de `Cartoes` e `Importacoes` existem, mas ainda não entram em `Repositorios` (`api/deps.py`): a composição é da T-039. |
| 2026-11-12 | Criação via `/mudanca-de-requisito` (integração Meu Pluggy). Q1–Q19 respondidas e análise de impacto aprovada → status **Aprovada**. `01` → 1.4, `02` → 1.15, `03` → 1.36, `04` → 1.1. |
