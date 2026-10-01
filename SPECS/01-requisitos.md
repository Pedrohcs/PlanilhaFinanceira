# 01 — Requisitos do Produto

| Campo | Valor |
|---|---|
| Documento | `SPECS/01-requisitos.md` |
| Versão | 1.2 |
| Atualizado em | 2026-10-01 |
| Status | Em revisão (ver [Premissas a confirmar](#8-premissas-a-confirmar)) |
| Responde | **O quê** o sistema faz e **por quê** — sem decisões técnicas |
| Alimenta | `03-arquitetura.md`, `04-roadmap.md`, `features/F-xx-*.md` |

> **Regra para IA:** este documento descreve comportamento observável pelo usuário. Ele não cita linguagens, bibliotecas, endpoints nem nomes de arquivos. Se uma implementação exigir mudar um requisito, **pare e proponha a alteração aqui primeiro** (comando `/mudanca-de-requisito`).

---

## 1. Visão do produto

Um aplicativo pessoal, usado no próprio computador, que ajuda o usuário a **saber para onde vai o seu dinheiro**. O usuário registra cada gasto (e cada receita) com poucos cliques; os registros ficam guardados numa planilha Google que pertence a ele. O aplicativo mostra somatórios e gráficos do mês corrente e a evolução ao longo dos meses.

### 1.1 Objetivos

- **O-1** Registrar um gasto em poucos segundos, a qualquer momento, sem abrir a planilha.
- **O-2** Ver quanto foi gasto no mês, em quê e como foi pago.
- **O-3** Comparar meses e perceber tendências (gasto x receita, categorias que crescem).
- **O-4** Automatizar lançamentos previsíveis (assinaturas, contas fixas, compras parceladas).
- **O-5** Manter os dados numa planilha legível, que o usuário pode abrir e consultar diretamente.

### 1.2 Usuário

Um único usuário, que também é quem instala e executa o aplicativo no próprio computador. Não há contas, perfis nem compartilhamento entre pessoas.

---

## 2. Glossário

| Termo | Significado |
|---|---|
| **Lançamento** | Registro de uma movimentação de dinheiro. É sempre um *gasto* ou uma *receita*. |
| **Gasto** | Lançamento de saída de dinheiro. |
| **Receita** | Lançamento de entrada de dinheiro (salário, freelance, rendimentos...). |
| **Categoria** | Classificação de um lançamento (ex.: Alimentação, Salário). Cada categoria é de gastos **ou** de receitas. |
| **Forma de pagamento** | Meio usado num gasto (Pix, cartão de crédito, etc.). |
| **Mês de referência** | Mês/ano ao qual o lançamento pertence para somatórios e gráficos. |
| **Parcelamento** | Compra dividida em N parcelas mensais; cada parcela é um lançamento. |
| **Recorrência** | Regra que gera automaticamente um lançamento por mês (ex.: assinatura de streaming, aluguel, salário). |
| **Saldo do mês** | Total de receitas menos total de gastos no mês de referência. |
| **Planilha** | A planilha Google do usuário onde todos os dados ficam armazenados. |

---

## 3. Requisitos funcionais

Cada requisito tem um ID estável (`REQ-xx`) usado no roadmap, nas specs de feature, nos testes e nos commits. **Nunca reutilize nem renumere um ID**; requisitos removidos ficam marcados como `(removido)`.

Critérios de aceite no formato **Dado / Quando / Então**. Eles são o contrato de "pronto" de cada requisito.

### Registro de lançamentos

#### REQ-01 — Registrar gasto
O usuário registra um gasto informando data, valor, descrição, categoria, forma de pagamento e, opcionalmente, uma observação. A ação **"Registrar gasto"** fica visível em todas as telas.

- **CA-01.1** Dado qualquer tela aberta, quando o usuário aciona "Registrar gasto", então um formulário abre com a data de hoje já preenchida.
- **CA-01.2** Dado um formulário válido, quando o usuário confirma, então o gasto é gravado na planilha, o formulário fecha e uma confirmação é exibida.
- **CA-01.3** Dado um campo obrigatório vazio ou valor ≤ 0, quando o usuário tenta confirmar, então o sistema indica o campo inválido e não grava nada.
- **CA-01.4** Dado que a gravação falhou, quando o erro é exibido, então os dados digitados continuam no formulário para nova tentativa.
- **CA-01.5** Dado um gasto recém-registrado, quando o usuário vê a listagem e o resumo do mês, então o gasto já aparece e os totais já o consideram.

#### REQ-02 — Registrar receita
Igual a REQ-01, mas para entradas de dinheiro. Forma de pagamento é opcional para receitas; só aparecem categorias de receita.

- **CA-02.1** Dado o formulário de receita, quando o usuário escolhe a categoria, então só categorias ativas do tipo receita são oferecidas.
- **CA-02.2** Dado um formulário de receita válido sem forma de pagamento, quando o usuário confirma, então a receita é gravada.

#### REQ-03 — Listar lançamentos do mês
O usuário vê todos os lançamentos de um mês, ordenados por data (mais recente primeiro), com filtros por tipo, categoria e forma de pagamento, e o total do que está filtrado.

- **CA-03.1** Dado um mês com lançamentos, quando a listagem abre, então mostra data, descrição, categoria, forma de pagamento, valor e indicação de parcela (ex.: "3/10") ou de recorrência.
- **CA-03.2** Dado um filtro aplicado, quando a lista atualiza, então o total exibido corresponde à soma dos itens visíveis (gastos e receitas separados).
- **CA-03.3** Dado um mês sem lançamentos, quando a listagem abre, então uma mensagem de "nenhum lançamento" é exibida.

#### REQ-04 — Navegar entre meses
Listagem e resumo mensal mostram por padrão o mês corrente e permitem ir para o mês anterior/seguinte ou escolher um mês.

- **CA-04.1** Dado o aplicativo recém-aberto, quando o usuário entra no resumo ou na listagem, então o mês corrente é exibido.
- **CA-04.2** Dado um mês selecionado, quando o usuário troca entre resumo e listagem, então o mesmo mês permanece selecionado.

#### REQ-05 — Editar lançamento
O usuário altera qualquer campo de um lançamento existente.

- **CA-05.1** Dado um lançamento na listagem, quando o usuário escolhe editar, então o formulário abre com os dados atuais.
- **CA-05.2** Dado uma edição válida confirmada, então a linha correspondente na planilha é atualizada (e nenhuma outra).
- **CA-05.3** Dado que a data foi alterada para outro mês, então o lançamento passa a contar no novo mês.

#### REQ-06 — Excluir lançamento
O usuário exclui um lançamento, com confirmação.

- **CA-06.1** Dado um lançamento, quando o usuário escolhe excluir, então o sistema pede confirmação mostrando descrição e valor.
- **CA-06.2** Dado a confirmação, então a linha é removida da planilha e os totais são recalculados.

### Parcelamentos

#### REQ-07 — Registrar compra parcelada
Ao registrar um gasto, o usuário pode marcá-lo como parcelado e informar o número de parcelas. O sistema cria um lançamento por parcela, um em cada mês.

- **CA-07.1** Dado um gasto de R$ 1.000,00 em 3 parcelas com data 15/01, quando confirmado, então são criados 3 lançamentos: R$ 333,34 em 15/01, R$ 333,33 em 15/02 e R$ 333,33 em 15/03 (ver RN-07).
- **CA-07.2** Dado uma compra em 31/01 em 2 parcelas, então a 2ª parcela fica em 28/02 (ou 29/02 em ano bissexto).
- **CA-07.3** Dado parcelas criadas, quando listadas, então cada uma exibe "k/N" e a descrição original.

#### REQ-08 — Manter parcelamento
O usuário pode editar ou excluir uma parcela individualmente, ou excluir o parcelamento inteiro (todas as parcelas) de uma vez.

- **CA-08.1** Dado uma parcela, quando o usuário a edita, então apenas aquela parcela muda.
- **CA-08.2** Dado uma parcela, quando o usuário escolhe "excluir parcelamento inteiro" e confirma, então todas as parcelas daquele parcelamento são removidas, em qualquer mês.

### Recorrências

#### REQ-09 — Gerenciar recorrências
O usuário cadastra, edita, pausa, reativa e encerra recorrências. Uma recorrência tem: tipo (gasto/receita), descrição, valor, categoria, forma de pagamento (se gasto), dia do mês, mês de início e mês de fim opcional.

- **CA-09.1** Dado a tela de recorrências, então todas aparecem com seu estado (ativa/pausada/encerrada) e o próximo mês a gerar.
- **CA-09.2** Dado uma recorrência editada, então só os lançamentos gerados **depois** da edição usam os novos dados.

#### REQ-10 — Geração automática de lançamentos recorrentes
Ao abrir o aplicativo, o sistema gera os lançamentos das recorrências ativas para cada mês de vigência, desde o último mês gerado até o mês corrente.

- **CA-10.1** Dado uma recorrência ativa desde julho, e o app aberto pela primeira vez em setembro, então são gerados os lançamentos de julho, agosto e setembro.
- **CA-10.2** Dado que o app é aberto várias vezes no mesmo mês, então nenhum lançamento é duplicado.
- **CA-10.3** Dado que o usuário excluiu um lançamento gerado, quando o app é reaberto, então ele **não** é gerado de novo.
- **CA-10.4** Nunca são gerados lançamentos para meses futuros.

### Categorias

#### REQ-11 — Gerenciar categorias
O usuário cria, renomeia, escolhe a cor, ativa/desativa e exclui categorias. Na primeira execução existe um conjunto padrão (RN-15).

- **CA-11.1** Dado um nome já existente no mesmo tipo (ignorando maiúsculas/acentos), quando o usuário tenta criar/renomear, então o sistema recusa com mensagem clara.
- **CA-11.2** Dado uma categoria renomeada, então todos os lançamentos dela exibem o novo nome, inclusive os antigos.
- **CA-11.3** Dado uma categoria com lançamentos ou recorrências, quando o usuário tenta excluir, então o sistema recusa e sugere desativar.
- **CA-11.4** Dado uma categoria desativada, então ela não aparece para novos lançamentos, mas continua nos relatórios e na listagem.

### Visão financeira

#### REQ-12 — Resumo do mês
Para o mês selecionado, o sistema mostra: total de gastos, total de receitas, saldo, gasto por categoria (valor e %) e gasto por forma de pagamento.

- **CA-12.1** Dado os lançamentos de um mês, então os totais exibidos batem, centavo a centavo, com a soma dos lançamentos da planilha naquele mês.
- **CA-12.2** Dado um saldo negativo, então ele é destacado visualmente.

#### REQ-13 — Gráficos do mês
Para o mês selecionado: gráfico de gastos por categoria (proporção), gráfico de gastos por forma de pagamento e evolução do gasto acumulado dia a dia.

- **CA-13.1** Dado categorias com cores definidas, então os gráficos usam essas cores.
- **CA-13.2** Dado um mês sem gastos, então os gráficos exibem estado vazio em vez de erro.

#### REQ-14 — Visão histórica
Para um intervalo de meses (padrão: últimos 12 até o corrente), o sistema mostra por mês: total de gastos, total de receitas e saldo; e a evolução de gastos por categoria.

- **CA-14.1** Dado o intervalo padrão, então aparecem 12 meses, inclusive meses sem lançamentos (com zero).
- **CA-14.2** Dado que o usuário muda o intervalo, então gráficos e totais do período se atualizam.
- **CA-14.3** Dado o período exibido, então são mostrados também total gasto no período e média mensal de gastos.

### Operação

#### REQ-15 — Preparação automática da planilha
Na primeira execução com uma planilha vazia, o sistema prepara a estrutura necessária (abas, cabeçalhos, categorias padrão) sem intervenção do usuário. Execuções seguintes não alteram dados existentes.

- **CA-15.1** Dado uma planilha nova e vazia, quando o sistema inicia, então a estrutura é criada e as categorias padrão existem.
- **CA-15.2** Dado uma planilha já preparada, quando o sistema inicia, então nada é duplicado nem sobrescrito.

#### REQ-16 — Feedback de indisponibilidade e erros
Quando a planilha não pode ser acessada (sem internet, sem permissão, planilha inexistente), o usuário vê uma mensagem clara com a causa provável.

- **CA-16.1** Dado que a planilha não foi compartilhada com o sistema, então a mensagem indica que é preciso compartilhá-la.
- **CA-16.2** Dado uma falha temporária, então o usuário pode tentar novamente sem reiniciar o aplicativo.
- **CA-16.3** Dado uma linha editada manualmente na planilha com dado inválido, então o sistema continua funcionando, ignora a linha nos cálculos e informa quantas linhas foram ignoradas.

---

## 4. Regras de negócio

| ID | Regra |
|---|---|
| **RN-01** | Valor é sempre positivo, em reais, com no máximo 2 casas decimais. O **tipo** (gasto/receita) define se é saída ou entrada. |
| **RN-02** | Data é obrigatória; o padrão é o dia de hoje. Datas passadas e futuras são aceitas. |
| **RN-03** | O mês de referência de um lançamento é o mês da sua data — inclusive para cartão de crédito (conta no mês da compra, não da fatura). |
| **RN-04** | Categoria é obrigatória, deve estar ativa (para novos lançamentos) e ser do mesmo tipo do lançamento. |
| **RN-05** | Forma de pagamento é obrigatória para gasto e opcional para receita. Valores: **Pix, Cartão de crédito, Cartão de débito, Dinheiro, Boleto, Transferência**. |
| **RN-06** | Descrição obrigatória, de 1 a 100 caracteres. Observação opcional, até 500 caracteres. |
| **RN-07** | Parcelamento: de 2 a 48 parcelas. O usuário informa o **valor total**; cada parcela = total ÷ N arredondado para baixo no centavo, e a diferença de centavos vai para a **1ª parcela**. A parcela *k* tem data = data da compra + (k−1) meses; se o dia não existir no mês, usa o último dia do mês. |
| **RN-08** | Parcelas são lançamentos independentes para edição; o vínculo entre elas só serve para exibir "k/N" e para excluir o parcelamento inteiro. |
| **RN-09** | Recorrência: valor fixo; dia do mês de 1 a 31 (se não existir no mês, usa o último dia); mês de início obrigatório; mês de fim opcional. Gera **no máximo um lançamento por mês de vigência**, nunca para meses futuros. |
| **RN-10** | A recorrência guarda o último mês já gerado. A geração só cria meses posteriores a ele — por isso um lançamento gerado e depois excluído não reaparece. Lançamentos gerados são editáveis/excluíveis como qualquer outro. |
| **RN-11** | Pausar ou encerrar uma recorrência impede gerações futuras e não altera lançamentos já gerados. Ao reativar uma recorrência pausada, meses do período pausado **não** são gerados retroativamente. |
| **RN-12** | Nome de categoria é único por tipo (comparação sem diferenciar maiúsculas nem acentos). Só pode ser excluída se não houver lançamentos nem recorrências vinculados; caso contrário, apenas desativada. |
| **RN-13** | Saldo do mês = total de receitas do mês − total de gastos do mês. |
| **RN-14** | A planilha é a **fonte da verdade**. Edições manuais feitas diretamente nela, respeitando o formato, são refletidas no aplicativo. Linhas inválidas são ignoradas nos cálculos e contabilizadas como aviso (CA-16.3). |
| **RN-15** | Categorias padrão — **Gastos:** Alimentação, Mercado, Moradia, Contas da casa, Transporte, Saúde, Educação, Lazer, Vestuário, Assinaturas, Outros gastos. **Receitas:** Salário, Freelance, Rendimentos, Outras receitas. |
| **RN-16** | Totais e somatórios são calculados em centavos exatos (sem erro de arredondamento de ponto flutuante). |

---

## 5. Requisitos não funcionais

| ID | Requisito |
|---|---|
| **RNF-01** | Execução local, no computador do usuário, sem login e sem hospedagem externa. |
| **RNF-02** | Persistência exclusivamente na planilha Google do usuário; não há outro armazenamento de dados de negócio. |
| **RNF-03** | Interface em português do Brasil: moeda `R$ 1.234,56`, datas `dd/mm/aaaa`, meses por extenso ("setembro de 2026"). |
| **RNF-04** | Registrar um lançamento leva menos de 3 s em conexão normal; telas de resumo e histórico abrem em menos de 3 s com até 5.000 lançamentos. |
| **RNF-05** | Credenciais de acesso ao Google nunca são versionadas, exibidas na interface nem enviadas ao navegador. O aplicativo só aceita conexões da própria máquina. |
| **RNF-06** | Falhas de comunicação não perdem o que o usuário digitou e oferecem nova tentativa. |
| **RNF-07** | Interface pensada para desktop, utilizável em janela estreita (≥ 360 px). |
| **RNF-08** | Toda regra de negócio (RN-xx) é coberta por teste automatizado. |

---

## 6. Fora de escopo (versão 1)

- Login, múltiplos usuários, compartilhamento.
- Hospedagem em nuvem ou acesso pelo celular.
- Importação de extratos bancários / faturas (OFX, CSV do banco).
- Orçamento/limite por categoria e alertas.
- Controle de fatura de cartão (fechamento, vencimento).
- Múltiplas moedas, investimentos, patrimônio.
- Notificações e lembretes.

Itens fora de escopo só entram via `/mudanca-de-requisito`, que atualiza este documento e o roadmap.

---

## 7. Rastreabilidade (requisito → feature)

A tabela completa (requisito → feature → tarefas) fica em [`04-roadmap.md`](04-roadmap.md#4-matriz-de-rastreabilidade). Todo `REQ-xx` precisa estar coberto por ao menos uma feature.

---

## 8. Premissas a confirmar

Decisões assumidas durante a escrita desta spec. Enquanto estiverem **"A confirmar"**, valem como estão escritas; ao confirmar ou mudar, atualize a regra correspondente e marque aqui.

| ID | Premissa | Regra afetada | Situação |
|---|---|---|---|
| P-01 | Formas de pagamento são uma lista fixa (não gerenciável pelo usuário). | RN-05 | A confirmar |
| P-02 | Gasto no cartão de crédito conta no mês da compra, não no mês da fatura. | RN-03 | A confirmar |
| P-03 | Parcelamento informado pelo valor total; centavos residuais na 1ª parcela. | RN-07 | **Confirmada em 2026-09-29** |
| P-04 | Recorrência tem valor fixo; contas variáveis (luz, água) são geradas com valor estimado e ajustadas manualmente. | RN-09 | **Confirmada em 2026-10-01** |
| P-05 | Recorrências são geradas ao abrir o aplicativo (não em segundo plano). | REQ-10 | **Confirmada em 2026-10-01** |
| P-06 | O usuário cria a planilha e a compartilha com o sistema; o sistema não cria a planilha em si, só a estrutura interna. | REQ-15 | A confirmar |
| P-07 | Moeda única: real (BRL). | RN-01 | A confirmar |

---

## Histórico de alterações

| Data | Versão | Alteração |
|---|---|---|
| 2026-09-29 | 1.0 | Versão inicial. |
| 2026-09-29 | 1.1 | §8: **P-03 confirmada** pelo usuário (parcelamento pelo valor total, resto de centavos na 1ª parcela). RN-07 permanece como estava. |
| 2026-10-01 | 1.2 | §8: **P-04 e P-05 confirmadas** pelo usuário (F-13 Q7): recorrência com valor fixo; geração ao abrir o aplicativo. RN-09 e REQ-10 permanecem como estavam. |
