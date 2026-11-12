# F-03 — Esquema e repositórios da planilha

| Campo | Valor |
|---|---|
| Feature | F-03 |
| Marco | M0 |
| Status | Concluída |
| Requisitos | REQ-15, REQ-16 (CA-16.3), RNF-02, RNF-04 (parcial) |
| Regras | RN-07 (aritmética), RN-14, RN-15, RN-16; base para RN-01..06 e RN-09 |
| Depende de | F-02 (**Concluída**) |
| Tarefas | T-007, T-008, T-009 |
| Atualizado em | 2026-09-30 |
| Premissas em jogo | **P-03** — **confirmada** em 2026-09-29 (`01` → 1.1) |

> **IDs de critério:** herdados de `01` mantêm o ID original (**CA-15.1**, **CA-15.2**, **CA-16.3**). Os refinados usam **`CA-F03.y`**.

---

## 1. Objetivo

Dar ao projeto o vocabulário e a memória: os tipos de domínio que todas as regras usarão (dinheiro em centavos exatos, datas de parcela, enums), a criação automática da estrutura da planilha na primeira execução, e a camada de repositório que lê e escreve linhas — tolerando o que o usuário editar à mão.

---

## 2. Escopo

**Inclui**
- Tipos de domínio: `enums.py`, `dinheiro.py` (tipo `Dinheiro` e divisão em parcelas), `datas.py` (aritmética de meses e dias), `modelos.py` (`Lancamento`, `Categoria`, `Recorrencia`).
- `infra/schema_planilha.py`: as 4 abas e suas colunas de `03` §5, em um único lugar.
- `infra/bootstrap.py`: criação idempotente de abas, cabeçalhos, `versao_schema` e seed de categorias (REQ-15).
- `infra/cache.py`: cache por aba com TTL e invalidação na escrita (`02` §5.5).
- `repositories/base.py` (Protocols de `03` §4.3), `repositories/planilha/` (gspread) e `repositories/memoria/` (para testes).
- Validação de linhas lidas, com contagem de `linhas_ignoradas` (CA-16.3).

**Não inclui** (e onde será tratado)
- Qualquer regra de negócio de serviço: validar categoria ativa, mesmo tipo, obrigatoriedade de forma de pagamento (RN-01..06) — **F-05/F-06**.
- Criar parcelamento de verdade (montar os lançamentos, gravar em lote) — **F-12** / T-026. Aqui entra **só a aritmética** de RN-07.
- Sincronizar recorrências (RN-09..11) — **F-13**. Aqui entram só o modelo e a aba.
- Endpoints HTTP e serviços — M1 em diante. F-03 não cria nenhuma rota.
- `POST /api/sistema/recarregar` — **F-14** / T-032. O cache já nasce com invalidação manual disponível.
- Migração de schema entre versões — só existe a versão 1; planilha com versão à frente do app é recusada com `SchemaPlanilhaInvalido` (§3.4).

---

## 3. Comportamento detalhado

### 3.1 Dinheiro (T-007)

1. Tipo único do projeto, como `02` §3 define:
   ```python
   Dinheiro = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2),
                        PlainSerializer(float, return_type=float, when_used="json")]
   ```
2. **Todo cálculo em `Decimal`**, nunca `float` (RN-16). Somas usam `Decimal` direto; a conversão para `float` acontece **só** na borda: JSON (serializer) e escrita na planilha (`float(valor)`).
3. Leitura da planilha: `Decimal(str(round(valor, 2)))` (`02` §3), para não herdar erro binário de ponto flutuante.
4. **Divisão em parcelas (RN-07)**, dado um total e `N` entre 2 e 48:
   - base = total ÷ N **truncado** para baixo no centavo (`ROUND_DOWN`);
   - resto = total − (base × N), sempre entre 0 e (N−1) centavos;
   - **1ª parcela = base + resto**; as outras N−1 = base;
   - garantia verificável: a soma das parcelas é **exatamente** o total.

   | Total | N | Parcelas |
   |---|---|---|
   | 100,00 | 3 | **33,34** + 33,33 + 33,33 |
   | 10,00 | 3 | **3,34** + 3,33 + 3,33 |
   | 99,99 | 48 | **2,23** + 47 × 2,08 |
   | 0,48 | 48 | 48 × 0,01 (resto zero) |
   | 2,00 | 2 | 1,00 + 1,00 |

5. **Total mínimo (Q3):** cada parcela tem de ser ≥ R$ 0,01, logo o total precisa ser ≥ `N × R$ 0,01`. Abaixo disso a divisão é **recusada** com erro de validação (422 `VALIDACAO`), e a mensagem informa o mínimo para aquele número de parcelas — ex.: 48 parcelas exigem no mínimo R$ 0,48.

### 3.2 Datas (T-007)

1. `ajustar_dia(ano, mes, dia)`: se o dia não existe no mês, usa o **último dia do mês** (RN-07, RN-09).
2. `somar_meses(data, n)`: avança/retrocede meses preservando o dia quando possível, senão o último dia do mês.
3. **Data da parcela `k`** = `somar_meses(data_da_compra, k − 1)` — sempre a partir da **data da compra**, nunca da parcela anterior. A diferença importa:

   | Compra | Parcelas | Correto (a partir da compra) | Errado (encadeado) |
   |---|---|---|---|
   | 31/01/2026 | 3 | 31/01, **28/02**, **31/03** | 31/01, 28/02, **28/03** |

4. Mês de referência de um lançamento = mês da sua data (RN-03), como texto `YYYY-MM`.
5. Utilitários de mês: `mes_de(data)`, `proximo_mes(mes)`, `mes_anterior(mes)`, `meses_entre(inicio, fim)` (inclusivo nas pontas, vazio se `fim < inicio`), `mes_corrente()`.
6. `criado_em`/`atualizado_em` são `datetime` **local sem fuso**, em ISO 8601 com segundos (`2026-09-29T10:15:00`). App de um só usuário, numa máquina, num fuso (RNF-01).

### 3.3 Esquema da planilha (T-008)

1. `schema_planilha.py` é a **fonte única** dos nomes de aba e da ordem das colunas de `03` §5 — nenhum outro módulo escreve nome de coluna literal.
2. Abas: `Lancamentos` (14 colunas), `Categorias` (6), `Recorrencias` (13), `Config` (2).
3. `versao_schema` atual = **1**, gravado na aba `Config`.

### 3.4 Bootstrap idempotente (T-008)

Executado **a cada conexão estabelecida** — no lifespan, depois de a planilha abrir, ou na nova tentativa do `GET /api/health` se a abertura tinha falhado (`03` §4.5). A conexão só conta como estabelecida se o bootstrap passar; `SchemaPlanilhaInvalido` fica guardado como erro da conexão e aparece no health. Primeiro **valida tudo** (só leitura); só depois, se nada divergir, escreve. Para cada aba do schema:

1. **Não existe** → cria a aba e escreve a linha 1 de cabeçalho.
2. **Existe e o cabeçalho confere** → nada a fazer.
3. **Existe e faltam colunas no fim** → acrescenta só as que faltam, preservando os dados (alargando a grade se for preciso).
3a. **Existe com colunas extras depois da última do schema** (ex.: `notas` depois de `atualizado_em`) → aceitas e ignoradas, com log `INFO`. O app não lê nem escreve nelas.
3b. Nomes do cabeçalho são comparados sem os espaços em volta; maiúsculas e minúsculas contam.
4. **Existe com divergência de ordem ou nome no meio** → `SchemaPlanilhaInvalido` (503 `SCHEMA_PLANILHA_INVALIDO`), com a aba e o problema na mensagem. **Nada é alterado** na planilha (Q4).
5. Aba `Config` sem `versao_schema` → grava `1`. Aceita `1`, `1.0` ou `"1"` (o Sheets pode devolver a célula como número ou texto). Com valor **maior** que 1 (planilha de um app mais novo), **menor que 1** ou não numérico → `SchemaPlanilhaInvalido`, também sem alterar nada. Valor **menor** que o atual seria migração — não existe versão anterior, então o caso ainda não ocorre (Q4).
6. Aba `Categorias` **vazia** (só cabeçalho) → seed das 15 categorias de RN-15 (CA-15.1). Com qualquer linha → não mexe (CA-15.2).
7. Reexecutar o bootstrap na mesma planilha não duplica nem sobrescreve nada (CA-15.2).

Categorias padrão (RN-15) — 11 de gasto e 4 de receita, com `id` gerado do nome:

| Tipo | Nome → `id` |
|---|---|
| GASTO | Alimentação → `alimentacao` · Mercado → `mercado` · Moradia → `moradia` · Contas da casa → `contas-da-casa` · Transporte → `transporte` · Saúde → `saude` · Educação → `educacao` · Lazer → `lazer` · Vestuário → `vestuario` · Assinaturas → `assinaturas` · Outros gastos → `outros-gastos` |
| RECEITA | Salário → `salario` · Freelance → `freelance` · Rendimentos → `rendimentos` · Outras receitas → `outras-receitas` |

**Cores padrão (Q2)** — 15 tons distinguíveis entre si e legíveis nos temas claro e escuro. Gastos ocupam a
volta do círculo cromático (quentes para consumo discricionário, frios para obrigações) e receitas ficam em verdes,
para que gasto e receita não se confundam num gráfico. Alimentação usa `#E57373`, que já aparece no exemplo de
`03` §6.3. O usuário pode trocar qualquer uma na tela de categorias (T-014).

| Tipo | Categoria | Cor | Tipo | Categoria | Cor |
|---|---|---|---|---|---|
| GASTO | Alimentação | `#E57373` | GASTO | Vestuário | `#A1887F` |
| GASTO | Mercado | `#FF8A65` | GASTO | Assinaturas | `#BA68C8` |
| GASTO | Moradia | `#7986CB` | GASTO | Outros gastos | `#90A4AE` |
| GASTO | Contas da casa | `#4FC3F7` | RECEITA | Salário | `#66BB6A` |
| GASTO | Transporte | `#4DD0E1` | RECEITA | Freelance | `#9CCC65` |
| GASTO | Saúde | `#F06292` | RECEITA | Rendimentos | `#26A69A` |
| GASTO | Educação | `#7E57C2` | RECEITA | Outras receitas | `#AED581` |
| GASTO | Lazer | `#FFB74D` | | | |

### 3.5 Cache por aba (T-009)

1. Chave = nome da aba; valor = as linhas lidas; TTL = `CACHE_TTL_SEGUNDOS` (padrão 30).
2. Toda escrita numa aba **invalida** a entrada daquela aba, na mesma operação.
3. Invalidação manual de tudo fica disponível para T-032 (`POST /api/sistema/recarregar`).
4. O cache existe para respeitar cota (`02` §5.5), não para ser uma segunda fonte de dados: ele nunca serve dado que a aplicação acabou de alterar.

### 3.6 Leitura, validação e escrita (T-009)

1. Leitura: **uma chamada por aba**, `get_all_values` com `UNFORMATTED_VALUE` (`02` §5.4).
2. Cada linha é validada conforme `03` §5.6. Linha inválida → **ignorada**, contada em `linhas_ignoradas` e registrada em log `WARNING` com aba e número de linha (CA-16.3, RN-14).
3. Motivos de invalidez: `id` vazio · data não ISO · valor não numérico ou ≤ 0 · `tipo`/`forma_pagamento`/`status` fora do enum · campos obrigatórios vazios.
4. Escrita: `append_rows` com `RAW` e `INSERT_ROWS` (`02` §5.4) — **sempre em lote**, mesmo para um item só, para o caminho ser um só. Lista vazia não faz chamada. `inserir` não verifica `id` repetido: os serviços geram `uuid4` (e slug único para categoria).
5. Atualizar/remover: localizar a linha **pelo `id`**, relendo a aba na hora; nunca guardar índice de linha entre requisições (o usuário reordena a planilha à mão).
6. Remoção de vários `id`s: **uma** chamada `batch_update` com os `deleteDimension` de baixo para cima, para os índices não deslizarem. **Tudo ou nada:** se algum `id` não existir, levanta `NaoEncontrado` e nenhuma linha é apagada.
6a. Atualizar reescreve só as colunas do schema (A até a última); colunas extras do usuário na mesma linha ficam intactas.
6b. Linhas **totalmente vazias** no meio da aba são puladas sem contar em `linhas_ignoradas` — são espaço, não dado inválido.
6c. `id` repetido, em qualquer aba: vale a primeira linha; as seguintes são ignoradas e contadas (borda 18).
7. `obter(id)` — e `atualizar`/`remover` — de `id` inexistente → `NaoEncontrado` (código `NAO_ENCONTRADO`, `03` §6.2).
7a. Os repositórios acessam a planilha por `ConexaoPlanilha.executar(operacao)`: sem conexão, levanta o erro guardado (503); com conexão, aplica a política de tentativas de `02` §5.5. A referência de cada aba (`Worksheet`) fica guardada no repositório, para a leitura continuar sendo **uma** chamada por aba.
8. Datas e enums vão para a planilha como **texto**; valores como **número** (`02` §5.4).

### 3.7 Repositório em memória (T-009)

Mesmos Protocols, guardando os itens em listas. É o que os testes de serviço de M1 usarão (`02` §8), então precisa ter o **mesmo comportamento observável**: mesma exceção em `obter` inexistente, mesma semântica de lote, `linhas_ignoradas` sempre 0.

---

## 4. Critérios de aceite

**Herdados de `01`**

- [~] **CA-15.1** Dado uma planilha nova e vazia, quando o sistema inicia, então as 4 abas existem com o cabeçalho correto e as 15 categorias padrão de RN-15 estão lá. *(Verificado com planilha falsa, inclusive subindo a aplicação inteira (T-008). O teste `tests/integracao/test_planilha_real.py` (T-009) cobre a planilha real, mas só roda com `SPREADSHEET_ID_TESTE` — **pendente de execução pelo usuário**, junto com CA-F02.13.)*
- [~] **CA-15.2** Dado uma planilha já preparada, quando o sistema inicia de novo, então nada é duplicado nem sobrescrito: mesma quantidade de abas, de colunas e de linhas. *(Verificado com planilha falsa, inclusive subindo a aplicação inteira (T-008). O teste `tests/integracao/test_planilha_real.py` (T-009) cobre a planilha real, mas só roda com `SPREADSHEET_ID_TESTE` — **pendente de execução pelo usuário**, junto com CA-F02.13.)*
- [x] **CA-16.3** Dado uma linha inválida na aba (editada à mão), quando a listagem é lida, então a linha é ignorada nos resultados, `linhas_ignoradas` reflete a contagem, um `WARNING` cita aba e linha, e as linhas válidas voltam normalmente.

**Refinados — domínio (T-007)**

- [x] **CA-F03.1** Dado um total e `N` parcelas, quando a divisão de RN-07 é aplicada, então a soma das parcelas é **exatamente igual** ao total, para todos os pares de exemplo de §3.1 e para `N` de 2 a 48.
- [x] **CA-F03.2** Dado que há resto de centavos, quando as parcelas são geradas, então **só a primeira** recebe o resto e as demais são iguais entre si (RN-07).
- [x] **CA-F03.3** Dado `N` fora de 2..48, quando a divisão é pedida, então é recusada com erro de validação (RN-07).
- [x] **CA-F03.4** Dado uma compra em dia que não existe no mês de destino, quando a data da parcela `k` é calculada, então usa o último dia daquele mês, **sempre a partir da data da compra** — 31/01/2026 em 3× dá 31/01, 28/02 e 31/03 (RN-07).
- [x] **CA-F03.5** Dado 29/02/2024 (ano bissexto), quando se somam 12 meses, então o resultado é 28/02/2025; e `ajustar_dia(2100, 2, 29)` dá 28/02/2100 (2100 não é bissexto).
- [x] **CA-F03.6** Dado dois meses `YYYY-MM`, quando `meses_entre` é chamado, então devolve a sequência inclusiva nas pontas, cruzando a virada de ano, e lista vazia se `fim < inicio`.
- [x] **CA-F03.7** Dado somas de muitos valores, quando o total é calculado em `Decimal`, então o resultado é exato ao centavo — `0.1 + 0.2` como `Dinheiro` dá `0.30`, não `0.30000000000000004` (RN-16).
- [x] **CA-F03.8** Dado um `Lancamento` serializado para JSON, quando o corpo é inspecionado, então `valor` é **número** com 2 casas (não string), datas são `YYYY-MM-DD` e enums vêm em MAIÚSCULAS (`02` §7). *("2 casas" = valor quantizado em centavos; como número JSON, `42.50` sai `42.5`.)*

**Refinados — bootstrap (T-008)**

- [x] **CA-F03.9** Dado uma planilha sem nenhuma das abas, quando o bootstrap roda, então cria as 4 abas com os cabeçalhos **exatamente** nos nomes e na ordem de `03` §5.
- [x] **CA-F03.10** Dado uma aba a que faltam colunas **no final**, quando o bootstrap roda, então acrescenta só as que faltam e nenhum dado de linha é perdido.
- [x] **CA-F03.11** Dado uma aba com coluna renomeada ou fora de ordem, quando o bootstrap roda, então **nada é alterado** e o erro nomeia a aba e a divergência.
- [x] **CA-F03.12** Dado a aba `Categorias` vazia, quando o bootstrap roda, então insere as 15 categorias de RN-15 em **uma única** chamada de escrita, com `id` no formato de slug, tipo correto e `ativa = true`.
- [x] **CA-F03.13** Dado a aba `Categorias` com pelo menos uma linha, quando o bootstrap roda, então nenhuma categoria é inserida (CA-15.2), mesmo que o usuário tenha apagado algumas das padrão.
- [x] **CA-F03.14** Dado o bootstrap executado duas vezes seguidas, quando se comparam abas, colunas e linhas antes e depois da segunda, então são idênticas (CA-15.2).
- [x] **CA-F03.24** Dado `versao_schema` maior que 1 ou não numérico, quando o bootstrap roda, então levanta `SchemaPlanilhaInvalido` e **nenhuma** célula é escrita (Q4).
- [x] **CA-F03.25** Dado as 15 categorias semeadas, quando as cores são lidas, então cada uma tem a cor da tabela de §3.4, no formato `#RRGGBB`, e não há cor repetida (Q2).
- [x] **CA-F03.15** Dado a aba `Config`, quando o bootstrap termina, então existe a chave `versao_schema` com o valor `1`.

**Refinados — repositórios e cache (T-009)**

- [x] **CA-F03.16** Dado uma aba com 3 linhas válidas e 2 inválidas, quando `listar()` é chamado, então devolve 3 itens e `linhas_ignoradas == 2` (CA-16.3).
- [x] **CA-F03.17** Dado uma escrita, quando a leitura seguinte da mesma aba acontece, então ela **não** vem do cache — a entrada foi invalidada na escrita.
- [x] **CA-F03.18** Dado duas leituras da mesma aba dentro do TTL, quando se conta as chamadas ao gspread, então houve **uma** só; passado o TTL, duas.
- [x] **CA-F03.19** Dado que o usuário reordenou as linhas na planilha à mão, quando um item é atualizado pelo `id`, então **apenas a linha daquele `id`** muda.
- [x] **CA-F03.20** Dado vários `id`s removidos de uma vez, quando a remoção termina, então exatamente esses itens desapareceram e nenhum outro (índices não deslizaram).
- [x] **CA-F03.21** Dado `obter(id)` com `id` inexistente, quando chamado, então levanta `NaoEncontrado`, tanto no repositório de planilha quanto no de memória.
- [x] **CA-F03.22** Dado uma descrição começando com `=`, quando é gravada, então volta como **texto** na leitura, não como fórmula (escrita `RAW`, ADR-04).
- [x] **CA-F03.23** Dado os dois repositórios (planilha e memória), quando o mesmo roteiro de operações é aplicado a ambos, então o comportamento observável é o mesmo.

---

## 5. Casos de borda

| # | Caso | Comportamento esperado | Regra |
|---|---|---|---|
| 1 | Total R$ 0,47 em 48 parcelas (parcela daria R$ 0,00). | Recusado com 422 `VALIDACAO`; a mensagem diz que 48 parcelas exigem no mínimo R$ 0,48. | RN-01, Q3 |
| 2 | Total R$ 100,00 em 3. | `33,34 + 33,33 + 33,33`; soma exata. | RN-07 |
| 3 | Compra em 31/01/2026, 3 parcelas. | 31/01, 28/02, 31/03 — a partir da compra, não encadeado. | RN-07 |
| 4 | Compra em 29/02/2024, +12 meses. | 28/02/2025. | RN-07 |
| 5 | `ajustar_dia(2100, 2, 29)`. | 28/02/2100 (2100 não é bissexto). | RN-09 |
| 6 | `meses_entre("2026-11", "2027-02")`. | `["2026-11", "2026-12", "2027-01", "2027-02"]`. | RN-09 |
| 7 | `meses_entre("2027-02", "2026-11")`. | Lista vazia. | RN-09 |
| 8 | Planilha com as 4 abas e uma 5ª criada pelo usuário. | A 5ª é ignorada, não apagada. | RN-14 |
| 9 | Aba `Lancamentos` com a coluna `observacao` renomeada para `obs`. | `SchemaPlanilhaInvalido` citando aba e coluna; nada é alterado. | `02` §5.6 |
| 10 | Aba `Lancamentos` só com as colunas A–H (faltam I–N no fim). | As 6 finais são acrescentadas; as linhas existentes continuam válidas. | `03` §4.5 |
| 11 | `versao_schema` = `2` (planilha de versão futura). | `SchemaPlanilhaInvalido`: o app é mais antigo que a planilha e não sabe ler o formato. | `02` §5.6 |
| 12 | `versao_schema` com texto não numérico. | `SchemaPlanilhaInvalido`, mesma mensagem. | `02` §5.6 |
| 13 | Linha de lançamento com `valor` = `0` ou `-5`. | Ignorada e contada. | `03` §5.6 |
| 14 | Linha com `forma_pagamento` = `PIX ` (espaço no fim). | Normaliza espaços antes de validar; a linha é aceita. | RN-14 |
| 15 | Linha de GASTO sem `forma_pagamento`. | Ignorada (obrigatória para gasto, RN-05). | `03` §5.6 |
| 16 | Linha de RECEITA sem `forma_pagamento`. | Válida (opcional para receita, RN-05). | RN-05 |
| 17 | Valor lido como `42.500000000000004` (ponto flutuante do Sheets). | Vira `Decimal("42.50")`. | RN-16 |
| 18 | Aba `Categorias` com duas linhas de mesmo `id`. | A primeira vale; a segunda é ignorada e contada. | RN-14 |
| 19 | Descrição `=SOMA(A1:A9)`. | Gravada e lida como texto literal. | ADR-04 |
| 20 | 5.000 lançamentos na aba. | Leitura em uma chamada; filtragem em memória (RNF-04 é medido em T-032). | `02` §5.5 |
| 21 | Aba `Categorias` esvaziada de propósito pelo usuário. | O próximo início **re-semeia** as 15 padrão — é o comportamento de `05`/T-008 ("aba vazia → seed"), registrado para não surpreender. | CA-15.1 |

---

## 6. Contrato e dados

**API** — F-03 **não cria nenhum endpoint**. Os Protocols de `03` §4.3 são contratos internos:

```python
class LancamentoRepository(Protocol):
    def listar(self) -> ListagemComAvisos[Lancamento]: ...
    def obter(self, id: str) -> Lancamento: ...          # NaoEncontrado
    def inserir(self, itens: list[Lancamento]) -> None: ...  # sempre em lote
    def atualizar(self, item: Lancamento) -> None: ...
    def remover(self, ids: list[str]) -> None: ...
```

`ListagemComAvisos[T]` = `{itens: list[T], linhas_ignoradas: int}`, definido no domínio.

**Planilha** — as 4 abas de `03` §5, usadas exatamente como lá está: `Lancamentos` (A–N), `Categorias` (A–F), `Recorrencias` (A–M), `Config` (A–B). Esta feature **implementa** esse modelo; não o altera. `versao_schema = 1`.

**Erro novo** — `SchemaPlanilhaInvalido` → 503 `SCHEMA_PLANILHA_INVALIDO`, já registrado em `02` §5.6 (→ 1.7) e em `03` §6.2 (→ 1.6). Mensagem: "A estrutura da planilha não corresponde ao esperado: <aba>, <problema>."

---

## 7. Interface

Nenhuma. F-03 é backend puro. O aviso de `linhas_ignoradas` chega à tela em **T-032** (F-14); a listagem que o exibe é **T-018**.

Mensagens ao usuário nascidas aqui (exibidas depois): `SCHEMA_PLANILHA_INVALIDO` e o aviso de linhas ignoradas, cujo texto final é de T-032.

---

## 8. Plano de testes

Unitários com repositório em memória e planilha falsa; **um** teste `@integracao` contra `SPREADSHEET_ID_TESTE` (`02` §8).

| Teste | Nível | Cobre |
|---|---|---|
| `tests/unit/test_dinheiro.py::test_parcelas_somam_o_total__RN_07` (parametrizado) | unitário BE | CA-F03.1 |
| `...::test_parcelas_centavos_na_primeira__RN_07` | unitário BE | CA-F03.2 |
| `...::test_parcelas_recusa_n_fora_da_faixa__RN_07` | unitário BE | CA-F03.3 |
| `...::test_parcelas_recusa_total_menor_que_um_centavo_por_parcela__RN_07` | unitário BE | CA-F03.3, borda 1 |
| `...::test_soma_em_decimal_sem_erro_de_ponto_flutuante__RN_16` | unitário BE | CA-F03.7 |
| `...::test_valor_lido_da_planilha_vira_decimal_de_2_casas__RN_16` | unitário BE | CA-F03.7, borda 17 |
| `tests/unit/test_datas.py::test_data_da_parcela_parte_da_compra__RN_07` | unitário BE | CA-F03.4 |
| `...::test_ajustar_dia_em_fim_de_mes_e_ano_bissexto__RN_09` | unitário BE | CA-F03.5 |
| `...::test_meses_entre_inclusivo_e_virada_de_ano__RN_09` | unitário BE | CA-F03.6 |
| `tests/unit/test_modelos.py::test_json_com_valor_numerico_e_enum_maiusculo__CA_F03_8` | unitário BE | CA-F03.8 |
| `tests/unit/test_bootstrap.py::test_cria_as_quatro_abas_com_cabecalho__CA_15_1` | unitário BE | CA-15.1, CA-F03.9 |
| `...::test_semeia_as_quinze_categorias_padrao__RN_15` | unitário BE | CA-F03.12 |
| `...::test_nao_semeia_se_ja_houver_categoria__CA_15_2` | unitário BE | CA-F03.13 |
| `...::test_rodar_duas_vezes_nao_duplica__CA_15_2` | unitário BE | CA-F03.14, CA-15.2 |
| `...::test_acrescenta_colunas_que_faltam_no_fim__CA_F03_10` | unitário BE | CA-F03.10, borda 10 |
| `...::test_divergencia_de_cabecalho_da_erro_claro__CA_F03_11` | unitário BE | CA-F03.11, borda 9 |
| `...::test_grava_versao_schema__CA_F03_15` | unitário BE | CA-F03.15 |
| `...::test_versao_schema_a_frente_do_app_da_erro__CA_F03_24` | unitário BE | CA-F03.24, bordas 11 e 12 |
| `...::test_categorias_padrao_tem_cor_unica__CA_F03_25` | unitário BE | CA-F03.25 |
| `tests/unit/test_cache.py::test_segunda_leitura_no_ttl_nao_chama_o_google__CA_F03_18` | unitário BE | CA-F03.18 |
| `...::test_escrita_invalida_o_cache_da_aba__CA_F03_17` | unitário BE | CA-F03.17 |
| `tests/unit/test_repositorio_planilha.py::test_ignora_linhas_invalidas_e_conta__CA_16_3` (parametrizado por motivo) | unitário BE | CA-16.3, CA-F03.16 |
| `...::test_atualiza_so_a_linha_do_id_apos_reordenacao__CA_F03_19` | unitário BE | CA-F03.19 |
| `...::test_remove_varios_ids_sem_deslizar_indices__CA_F03_20` | unitário BE | CA-F03.20 |
| `...::test_descricao_com_igual_nao_vira_formula__CA_F03_22` | unitário BE | CA-F03.22, borda 19 |
| `...::test_receita_sem_forma_de_pagamento_e_valida__RN_05` | unitário BE | bordas 15 e 16 |
| `tests/unit/test_repositorio_memoria.py::test_obter_inexistente_levanta_nao_encontrado__CA_F03_21` | unitário BE | CA-F03.21 |
| `tests/unit/test_repositorios_equivalentes.py::test_mesmo_comportamento_nos_dois_repositorios__CA_F03_23` | unitário BE | CA-F03.23 |
| `tests/integracao/test_planilha_real.py::test_bootstrap_e_crud_em_planilha_de_teste__CA_15_1` | integração BE | CA-15.1, CA-15.2, CA-F03.9 na planilha real |

---

## 9. Divisão em tarefas

| Tarefa | Escopo nesta feature | Arquivos principais |
|---|---|---|
| **T-007** (BE) | Domínio base: enums, `Dinheiro` e divisão RN-07, aritmética de datas e meses, modelos. Acrescenta `NaoEncontrado` (`NAO_ENCONTRADO`) e `ErroValidacao` (`VALIDACAO`) a `domain/erros.py`. | `backend/app/domain/{enums,dinheiro,datas,modelos}.py`, `backend/app/domain/erros.py` (alteração), `backend/tests/unit/{test_dinheiro,test_datas,test_modelos}.py` |
| **T-008** (BE) | Schema como fonte única e bootstrap idempotente, ligado ao lifespan. | `backend/app/infra/{schema_planilha,bootstrap}.py`, `backend/app/main.py` (alteração), `backend/tests/unit/test_bootstrap.py` |
| **T-009** (BE) | Cache, Protocols, repositório de planilha (com validação de linhas) e de memória. | `backend/app/infra/cache.py`, `backend/app/repositories/base.py`, `backend/app/repositories/planilha/*.py`, `backend/app/repositories/memoria/*.py`, `backend/tests/unit/test_{cache,repositorio_planilha,repositorio_memoria,repositorios_equivalentes}.py`, `backend/tests/integracao/test_planilha_real.py` |

Ordem obrigatória: T-007 → T-008 → T-009 (`05` §4; T-008 também depende de T-005, já concluída).

**Pré-requisito externo:** o teste `@integracao` de T-009 precisa de uma **planilha separada** em `SPREADSHEET_ID_TESTE`, que só o usuário pode criar e compartilhar. Sem ela o teste é pulado (CA-F01.7) e a verificação real fica pendente, como já acontece com CA-F02.13.

---

## 10. Decisões tomadas nesta feature

| Decisão | Motivo | Virou ADR? |
|---|---|---|
| Data da parcela `k` calculada a partir da **data da compra**, não da parcela anterior. | RN-07 diz "data da compra + (k−1) meses". Encadear produziria 28/03 em vez de 31/03 no exemplo de §3.2 — erro clássico e silencioso. | Não |
| `criado_em`/`atualizado_em` em hora **local sem fuso**, ISO com segundos. | `02` §3 fixa ISO mas não o fuso; app de um usuário, uma máquina, um fuso (RNF-01). Guardar UTC exigiria converter só para exibir. | Não |
| `inserir` sempre recebe **lista**, mesmo com um item. | É o contrato de `03` §4.3 e mantém um único caminho de escrita, já em lote (`02` §5.5). | Não |
| Repositório em memória tem de ser **observacionalmente equivalente** ao de planilha, com teste dedicado. | Os testes de M1 usam o de memória (`02` §8); se divergirem, a suíte fica verde e o app quebra. | Não |
| Espaços em volta de valores lidos são normalizados antes de validar. | Edição manual costuma deixar espaço sobrando; recusar a linha por isso contraria o espírito de RN-14. | Não |
| `ErroValidacao` (código `VALIDACAO`) no domínio (T-007). | §3.1.5 pede 422 `VALIDACAO` para divisão recusada; sem uma exceção de domínio com esse código, um `ValueError` viraria 500. O mapa `VALIDACAO → 422` já existia em `api/erros.py`. | Não |
| Os modelos de domínio garantem a **linha válida** de `03` §5, inclusive as regras entre campos: `forma_pagamento` obrigatória se GASTO (`Lancamento` e `Recorrencia`) e o trio `parcelamento_id`/`parcela_numero`/`parcela_total` todo preenchido ou todo vazio, com 1 ≤ k ≤ N ≤ 48 (T-007). | A validação de linhas de T-009 passa a ser "o modelo aceitou?", sem duplicar regra, e os dois repositórios só guardam dado válido (CA-F03.23). Regras que dependem de outros dados — categoria ativa e do mesmo tipo (RN-04) — e as mensagens amigáveis continuam nos serviços (F-05/F-06). | Não |
| `data_da_parcela(compra, k)` fica em `domain/datas.py` (T-007). | Fixa num só lugar que a data parte da compra (§3.2.3); `parcelamento_service` (T-026) só a chama. | Não |
| Bootstrap roda a cada conexão estabelecida, injetado em `ConexaoPlanilha` por `main.py` (T-008). | Com o app aberto sem internet, a conexão só nasce no "Tentar novamente" do health; rodar só no lifespan deixaria as abas sem criar até reiniciar. A injeção evita import circular entre `sheets_client` e `bootstrap`. `03` → 1.9. | Não |
| Validação inteira antes de qualquer escrita (T-008). | CA-F03.11 e .24 exigem planilha intocada quando algo diverge — inclusive quando a divergência está numa aba posterior a outra que precisaria ser criada. | Não |
| Colunas extras depois da última do schema são aceitas e ignoradas (T-008, decisão do usuário). | Mesmo espírito da 5ª aba do usuário (borda 8): o que o app não conhece, ele não toca. Uma futura coluna nova do schema nessa posição seria detectada como divergência. | Não |
| `versao_schema` < 1 é inválido (T-008). | Não existe versão anterior à 1; tratar como migração seria inventar comportamento. | Não |
| Seed de RN-15 fica no `bootstrap`, não no `categoria_service` (T-008). | `infra` não pode chamar `services` (`03` §4.2); `03` §4.4 citava o seed no serviço, em contradição com §4.5. `03` → 1.9. | Não |
| Inserções com `INSERT_ROWS` (T-009), inclusive no bootstrap. | Com o padrão `OVERWRITE`, um append depois de uma linha em branco deixada pelo usuário pode sobrescrever dados. `02` → 1.8. | Não |
| `remover` tudo-ou-nada (T-009). | CA-F03.20 pede "exatamente esses itens e nenhum outro"; remoção parcial deixaria o parcelamento (T-026) pela metade sem aviso. | Não |
| Linha totalmente vazia não conta como ignorada; `id` repetido vale a primeira em todas as abas (T-009). | Contar espaço em branco geraria aviso falso; a regra do repetido era só de `Categorias` (borda 18) e vale igual para as outras. | Não |
| Composição (instância única do cache e dos repositórios em `api/deps.py`) fica para o primeiro endpoint de negócio, T-013. | Nenhuma rota usa repositório em F-03; montar antes seria código morto. | Não |
| P-03 **confirmada**; resto de centavos na 1ª parcela (Q1). | Resposta do usuário; `01` → 1.1 com a premissa marcada. RN-07 não mudou. | Não |
| Paleta de 15 cores proposta por mim (Q2). | RN-15 não define cores e `03` §5.2 exige `#RRGGBB`. Tons distinguíveis, legíveis em tema claro e escuro, receitas em verdes; `#E57373` para Alimentação por coerência com `03` §6.3. Trocáveis em T-014. | Não |
| Total mínimo `N × R$ 0,01` para parcelar (Q3). | Parcela de R$ 0,00 violaria RN-01; recusar é explícito, reduzir o número de parcelas seria silencioso. | Não |
| `SchemaPlanilhaInvalido` → 503 `SCHEMA_PLANILHA_INVALIDO`, app sobe degradado, planilha intocada (Q4). | A mensagem genérica não diria o que consertar; correção automática poderia destruir dado intencional. `02` → 1.7, `03` → 1.6. | Não |

---

## 11. Questões em aberto

**Respondidas em 2026-09-29 — nenhuma em aberto.**

- [x] **Q1** → **P-03 confirmada**: parcelamento pelo valor total, resto na 1ª parcela (`01` → 1.1).
- [x] **Q2** → paleta proposta por mim, na tabela de §3.4; editável pelo usuário em T-014.
- [x] **Q3** → recusar com 422 `VALIDACAO` quando o total for menor que `N × R$ 0,01`.
- [x] **Q4** → `SchemaPlanilhaInvalido` (503 `SCHEMA_PLANILHA_INVALIDO`); app sobe degradado e a planilha não é tocada. Registrado em `02` §5.6 e `03` §6.2.

---

## Revisões

| Data | Alteração |
|---|---|
| 2026-09-29 | Criação (`/especificar-feature F-03`). Status `Rascunho` — 4 questões em aberto. |
| 2026-09-29 | Q1–Q4 respondidas → status **Aprovada**. Paleta das 15 categorias, total mínimo por parcela e `SchemaPlanilhaInvalido` incorporados; CA-F03.24 e .25 acrescentados. `01` → 1.1, `02` → 1.7, `03` → 1.6. |
| 2026-09-30 | T-007 concluída: CA-F03.1 a .8 verificados por teste. `ErroValidacao` acrescentado ao escopo de T-007 (§9) e três decisões registradas em §10 (validação entre campos nos modelos, `ErroValidacao`, `data_da_parcela`). |
| 2026-09-30 | T-008 concluída: CA-F03.9 a .15, .24 e .25 verificados por teste; CA-15.1/15.2 com planilha falsa (real pendente). §3.4 refinado — bootstrap a cada conexão estabelecida, validação inteira antes de escrever, colunas extras no fim aceitas (decisão do usuário), `versao_schema` < 1 inválido — e cinco decisões em §10. `03` → 1.9. |
| 2026-09-30 | T-009 concluída → **feature Concluída**. CA-16.3 e CA-F03.16 a .23 verificados por teste; CA-15.1/15.2 com teste de integração pronto, aguardando execução na planilha real. §3.6 refinado (`INSERT_ROWS`, remoção tudo-ou-nada, linha vazia não conta, `id` repetido em todas as abas, `executar`) e quatro decisões em §10. `02` → 1.8, `03` → 1.10. |
| 2026-11-12 | **Revisão (F-16, `/mudanca-de-requisito`):** schema passa à **versão 2** — abas `Cartoes` e `Importacoes`, categorias reservadas "A classificar" no seed e na migração 1 → 2 (`03` §5.4, §5.7, §5.8); `Lancamento` aceita parcela **sem** `parcelamento_id` (parcela importada; `parcelamento_id` continua exigindo número e total); `Repositorio[T]` ganha `atualizar_varios` (uma chamada, tudo-ou-nada). Trabalho em **T-036**; o comportamento desta spec fica valendo para a versão 1. |
