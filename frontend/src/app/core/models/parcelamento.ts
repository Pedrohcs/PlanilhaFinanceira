import { FormaPagamento } from './enums';
import { Lancamento } from './lancamento';

/** `POST /api/parcelamentos` (SPECS/03 §6.3). Sem `tipo`: é sempre gasto (REQ-07). */
export interface ParcelamentoEntrada {
  /** Data da compra = data da 1ª parcela, `YYYY-MM-DD`. */
  data: string;
  descricao: string;
  valor_total: number;
  parcelas: number;
  categoria_id: string;
  forma_pagamento: FormaPagamento | null;
  observacao: string | null;
}

/** `201` de `POST /api/parcelamentos`: parcelas em ordem de `parcela_numero`. */
export interface Parcelamento {
  parcelamento_id: string;
  lancamentos: Lancamento[];
}

/** O diálogo de F-06 devolve um lançamento ou, na compra parcelada, o parcelamento. */
export function ehParcelamento(resultado: Lancamento | Parcelamento): resultado is Parcelamento {
  return 'lancamentos' in resultado;
}
