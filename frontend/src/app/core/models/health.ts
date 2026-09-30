/** Resposta de `GET /api/health` — sempre HTTP 200 (SPECS/03 §6.3). */
export interface RespostaHealth {
  status: 'ok' | 'degradado';
  planilha: {
    ok: boolean;
    titulo: string | null;
    erro: { codigo: string; mensagem: string } | null;
  };
}
