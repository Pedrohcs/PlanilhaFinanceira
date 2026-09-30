/**
 * Enums da API (SPECS/03 §5.5), só como códigos.
 *
 * Os rótulos ("Cartão de crédito" etc.) vêm do backend — `GET
 * /api/formas-pagamento` — para haver uma única fonte (F-04 §10).
 */
export type TipoLancamento = 'GASTO' | 'RECEITA';

export type FormaPagamento = 'PIX' | 'CREDITO' | 'DEBITO' | 'DINHEIRO' | 'BOLETO' | 'TRANSFERENCIA';

export type StatusRecorrencia = 'ATIVA' | 'PAUSADA' | 'ENCERRADA';
