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

/** Totais de um mês do histórico: os mesmos do `ResumoMensal` daquele mês. */
export interface MesDoHistorico {
  mes: string;
  total_gastos: number;
  total_receitas: number;
  saldo: number;
}

/** Gastos de uma categoria mês a mês: `valores` alinhados a `ResumoHistorico.meses`. */
export interface CategoriaNoHistorico {
  categoria_id: string;
  nome: string;
  cor: string;
  valores: number[];
}

/** Período do histórico, `YYYY-MM` nas duas pontas (F-11 Q2). */
export interface PeriodoHistorico {
  inicio: string;
  fim: string;
}

/** `GET /api/resumo/historico` (SPECS/03 §6.3; F-11). Tudo somado pelo backend (RN-16). */
export interface ResumoHistorico extends PeriodoHistorico {
  /** Um item por mês do período, inclusive os sem lançamento (CA-14.1). */
  meses: MesDoHistorico[];
  /** Só gastos, maior total no período primeiro. */
  por_categoria: CategoriaNoHistorico[];
  total_gastos_periodo: number;
  media_mensal_gastos: number;
  linhas_ignoradas: number;
}
