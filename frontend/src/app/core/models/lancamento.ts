import { FormaPagamento, TipoLancamento } from './enums';

/** `POST /api/lancamentos` (SPECS/03 §6.3). */
export interface LancamentoEntrada {
  /** `YYYY-MM-DD`. */
  data: string;
  tipo: TipoLancamento;
  descricao: string;
  valor: number;
  categoria_id: string;
  forma_pagamento: FormaPagamento | null;
  observacao: string | null;
}

/** Lançamento como a API devolve (SPECS/03 §6.3). */
export interface Lancamento extends LancamentoEntrada {
  id: string;
  categoria_nome: string;
  categoria_cor: string;
  parcelamento_id: string | null;
  parcela_numero: number | null;
  parcela_total: number | null;
  recorrencia_id: string | null;
  criado_em: string;
  atualizado_em: string;
}

/** Item de `GET /api/formas-pagamento`. */
export interface FormaPagamentoOpcao {
  codigo: FormaPagamento;
  nome: string;
}

/** Limites de RN-06, iguais aos da API. */
export const DESCRICAO_MAXIMO = 100;
export const OBSERVACAO_MAXIMO = 500;

/** Filtros opcionais da listagem (F-07 §3.1.3); combinados com E. */
export interface FiltrosLancamentos {
  tipo: TipoLancamento | null;
  categoria_id: string | null;
  forma_pagamento: FormaPagamento | null;
}

export const SEM_FILTROS: FiltrosLancamentos = {
  tipo: null,
  categoria_id: null,
  forma_pagamento: null,
};

/** `GET /api/lancamentos` (SPECS/03 §6.3). Totais já somados pelo backend (RN-16). */
export interface ListaLancamentos {
  mes: string;
  itens: Lancamento[];
  totais: { gastos: number; receitas: number; saldo: number };
  linhas_ignoradas: number;
}
