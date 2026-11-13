"""Exceções de domínio.

Cada exceção carrega o `codigo` que aparece no corpo de erro da API
(`SPECS/03` §6.2) e uma mensagem em pt-BR pronta para o usuário. O mapa
`codigo` → status HTTP **não** fica aqui: é responsabilidade de
`api/erros.py`, para o domínio não conhecer semântica HTTP.
"""


class ErroDominio(Exception):
    """Base de todos os erros previstos do domínio."""

    codigo = "ERRO_INTERNO"
    mensagem = "Erro interno."

    def __init__(
        self, mensagem: str | None = None, *, detalhes: list[dict[str, str]] | None = None
    ) -> None:
        self.mensagem = mensagem or type(self).mensagem
        # Mesmo formato de `detalhes` do corpo de erro (`SPECS/03` §6.2): {campo, mensagem}.
        self.detalhes = detalhes or []
        super().__init__(self.mensagem)


class ErroPlanilha(ErroDominio):
    """Falha ao acessar a planilha Google (`SPECS/02` §5.6)."""

    codigo = "PLANILHA_INDISPONIVEL"
    mensagem = "Não foi possível acessar a planilha."


class CredenciaisInvalidas(ErroPlanilha):
    codigo = "CREDENCIAIS_INVALIDAS"
    mensagem = "Arquivo de credenciais não encontrado ou inválido."


class SemPermissaoPlanilha(ErroPlanilha):
    codigo = "SEM_PERMISSAO_PLANILHA"
    mensagem = "Compartilhe a planilha com a conta de serviço como Editor."

    @classmethod
    def para(cls, client_email: str | None) -> "SemPermissaoPlanilha":
        """Mensagem nomeando a conta de serviço, quando ela é conhecida."""
        if not client_email:
            return cls()
        return cls(f"Compartilhe a planilha com {client_email} como Editor.")


class ApiSheetsDesabilitada(ErroPlanilha):
    codigo = "API_SHEETS_DESABILITADA"
    mensagem = "Ative a Google Sheets API no projeto do Google Cloud e tente novamente."


class PlanilhaNaoEncontrada(ErroPlanilha):
    codigo = "PLANILHA_NAO_ENCONTRADA"
    mensagem = "Planilha não encontrada. Confira SPREADSHEET_ID."


class PlanilhaIndisponivel(ErroPlanilha):
    codigo = "PLANILHA_INDISPONIVEL"
    mensagem = "Google Sheets indisponível no momento. Tente novamente."


class SchemaPlanilhaInvalido(ErroPlanilha):
    """Cabeçalho divergente ou `versao_schema` que o app não sabe ler (`SPECS/02` §5.6)."""

    codigo = "SCHEMA_PLANILHA_INVALIDO"
    mensagem = "A estrutura da planilha não corresponde ao esperado."

    @classmethod
    def para(cls, aba: str, problema: str) -> "SchemaPlanilhaInvalido":
        """Mensagem nomeando a aba e o que está errado, para o usuário corrigir."""
        return cls(f"A estrutura da planilha não corresponde ao esperado: {aba}, {problema}.")


class ErroValidacao(ErroDominio):
    """Entrada que viola uma regra de negócio (ex.: RN-07), vista como 422."""

    codigo = "VALIDACAO"
    mensagem = "Dados inválidos."

    @classmethod
    def no_campo(cls, campo: str, mensagem: str) -> "ErroValidacao":
        """Regra violada num campo: o formulário marca o campo certo (F-06 §3.4)."""
        return cls(mensagem, detalhes=[{"campo": campo, "mensagem": mensagem}])


class NaoEncontrado(ErroDominio):
    """`id` inexistente no repositório (`SPECS/03` §4.3)."""

    codigo = "NAO_ENCONTRADO"
    mensagem = "Registro não encontrado."


class CategoriaDuplicada(ErroDominio):
    """Nome já usado por outra categoria do mesmo tipo (RN-12)."""

    codigo = "CATEGORIA_DUPLICADA"
    mensagem = "Já existe uma categoria com esse nome."

    @classmethod
    def para(cls, nome: str, tipo: str) -> "CategoriaDuplicada":
        rotulo = "de gasto" if tipo == "GASTO" else "de receita"
        return cls(f'Já existe uma categoria {rotulo} chamada "{nome}".')


class CategoriaEmUso(ErroDominio):
    """Categoria com lançamentos ou recorrências: só pode ser desativada (RN-12)."""

    codigo = "CATEGORIA_EM_USO"
    mensagem = "A categoria está em uso e não pode ser excluída."

    @classmethod
    def para(cls, nome: str) -> "CategoriaEmUso":
        return cls(
            f'A categoria "{nome}" está em uso em lançamentos ou recorrências e não pode '
            "ser excluída. Desative-a para que não apareça mais em novos lançamentos."
        )


class CategoriaReservada(ErroDominio):
    """A categoria "A classificar" é usada pela importação dos cartões (RN-24)."""

    codigo = "CATEGORIA_RESERVADA"
    mensagem = "A categoria é usada pela importação dos cartões."

    @classmethod
    def ao_excluir(cls, nome: str) -> "CategoriaReservada":
        return cls._para(nome, "excluída")

    @classmethod
    def ao_desativar(cls, nome: str) -> "CategoriaReservada":
        return cls._para(nome, "desativada")

    @classmethod
    def _para(cls, nome: str, acao: str) -> "CategoriaReservada":
        return cls(
            f'A categoria "{nome}" é usada pela importação dos cartões e não pode ser {acao}.'
        )


class CategoriaInativa(ErroDominio):
    """Categoria desativada não recebe lançamentos novos (RN-04)."""

    codigo = "CATEGORIA_INATIVA"
    mensagem = "A categoria está desativada. Escolha uma categoria ativa."

    @classmethod
    def para(cls, nome: str) -> "CategoriaInativa":
        return cls(f'A categoria "{nome}" está desativada. Escolha uma categoria ativa.')


class CategoriaTipoIncompativel(ErroDominio):
    """Categoria de receita num gasto, ou o contrário (RN-04)."""

    codigo = "CATEGORIA_TIPO_INCOMPATIVEL"
    mensagem = "A categoria não é do mesmo tipo do lançamento."

    @classmethod
    def para(
        cls, nome: str, tipo_da_categoria: str, tipo_do_lancamento: str
    ) -> "CategoriaTipoIncompativel":
        categoria = "de gasto" if tipo_da_categoria == "GASTO" else "de receita"
        lancamento = "num gasto" if tipo_do_lancamento == "GASTO" else "numa receita"
        return cls(f'A categoria "{nome}" é {categoria} e não pode ser usada {lancamento}.')


class ErroPluggy(ErroDominio):
    """Falha na integração com o Meu Pluggy (`SPECS/02` §11.6).

    Nunca é `ErroPlanilha`: um problema na Pluggy não pode parecer queda da
    planilha nem acionar o banner (RNF-09).
    """

    codigo = "PLUGGY_INDISPONIVEL"
    mensagem = "Meu Pluggy indisponível no momento. Tente novamente mais tarde."


class PluggyNaoConfigurada(ErroPluggy):
    codigo = "PLUGGY_NAO_CONFIGURADA"
    mensagem = (
        "Integração com o Meu Pluggy não configurada. Preencha PLUGGY_CLIENT_ID, "
        "PLUGGY_CLIENT_SECRET e PLUGGY_ITEM_IDS no backend/.env."
    )


class PluggyCredenciaisInvalidas(ErroPluggy):
    codigo = "PLUGGY_CREDENCIAIS_INVALIDAS"
    mensagem = "Client ID ou Client Secret da Pluggy inválidos. Confira o backend/.env."


class PluggyIndisponivel(ErroPluggy):
    """Rede, timeout, `429`/`5xx` após as tentativas ou resposta fora do formato esperado."""

    codigo = "PLUGGY_INDISPONIVEL"
    mensagem = "Meu Pluggy indisponível no momento. Tente novamente mais tarde."


class ImportacaoEmAndamento(ErroDominio):
    """Só uma importação por vez no processo; a segunda não espera (F-16 §3.7.3)."""

    codigo = "IMPORTACAO_EM_ANDAMENTO"
    mensagem = "Já existe uma busca nos cartões em andamento."
