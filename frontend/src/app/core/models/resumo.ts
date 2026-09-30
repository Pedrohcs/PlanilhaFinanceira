import { FormaPagamento } from './enums';

/** Item de `por_categoria`: só gastos, maior primeiro (SPECS/03 §6.3). */
export interface GastoPorCategoria {
  categoria_id: string;
  nome: string;
  cor: string;
  total: number;
  /** 0 a 100 com 1 casa, pronto da API. */
  percentual: number;
}

/** Item de `por_forma_pagamento`: só gastos, maior primeiro. */
export interface GastoPorForma {
  forma_pagamento: FormaPagamento;
  nome: string;
  total: number;
  percentual: number;
}

/** `GET /api/resumo/mensal` (SPECS/03 §6.3). Tudo somado pelo backend (RN-16). */
export interface ResumoMensal {
  mes: string;
  total_gastos: number;
  total_receitas: number;
  saldo: number;
  por_categoria: GastoPorCategoria[];
  por_forma_pagamento: GastoPorForma[];
  /** Um item por dia do mês (F-09 Q2); desenhado em F-10. */
  gasto_acumulado_diario: { dia: number; total: number }[];
  linhas_ignoradas: number;
}
