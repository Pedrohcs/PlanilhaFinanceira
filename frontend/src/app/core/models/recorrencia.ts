import { FormaPagamento, StatusRecorrencia, TipoLancamento } from './enums';

/** `POST`/`PUT /api/recorrencias` (SPECS/03 §6.3). Sem observação: a aba não tem a coluna. */
export interface RecorrenciaEntrada {
  tipo: TipoLancamento;
  descricao: string;
  valor: number;
  categoria_id: string;
  forma_pagamento: FormaPagamento | null;
  /** 1 a 31; nos meses sem esse dia, o último dia do mês (RN-09). */
  dia_do_mes: number;
  /** `YYYY-MM`. */
  mes_inicio: string;
  /** `YYYY-MM`, ou `null` = sem fim. */
  mes_fim: string | null;
}

/** Recorrência como a API devolve (SPECS/03 §6.3; F-13). */
export interface Recorrencia extends RecorrenciaEntrada {
  id: string;
  status: StatusRecorrencia;
  ultimo_mes_gerado: string | null;
  /** Próximo mês que a sincronização gera; `null` se pausada, encerrada ou vigência gerada. */
  proximo_mes: string | null;
  criado_em: string;
  atualizado_em: string;
}

/** `POST /api/recorrencias/sincronizar` (SPECS/03 §6.1). */
export interface Sincronizacao {
  lancamentos_gerados: number;
  detalhes: { recorrencia_id: string; meses: string[] }[];
}
