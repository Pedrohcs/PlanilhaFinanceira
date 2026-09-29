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

    def __init__(self, mensagem: str | None = None) -> None:
        self.mensagem = mensagem or type(self).mensagem
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
