import { Params } from '@angular/router';
import { PeriodoHistorico } from '../../core/models/resumo';
import { mesesNoPeriodo, mesValido, somarMeses } from '../../core/utils/mes';

/** Tamanho máximo do período do histórico (F-11 Q2; a API recusa mais). */
export const MESES_NO_PERIODO_MAX = 36;

/**
 * `?inicio=&fim=` da URL (F-11 §3.2.2):
 * - nenhum dos dois → `periodo: null` (vale o padrão da API);
 * - período válido → `periodo`;
 * - inválido, incompleto, invertido ou acima do limite → `periodo: null` e
 *   `descartar: true` (a página limpa a URL).
 */
export interface LeituraDoPeriodo {
  periodo: PeriodoHistorico | null;
  descartar: boolean;
}

export function lerPeriodo(params: Params): LeituraDoPeriodo {
  const inicio: unknown = params['inicio'];
  const fim: unknown = params['fim'];
  if (inicio === undefined && fim === undefined) {
    return { periodo: null, descartar: false };
  }
  if (typeof inicio === 'string' && typeof fim === 'string' && periodoValido(inicio, fim)) {
    return { periodo: { inicio, fim }, descartar: false };
  }
  return { periodo: null, descartar: true };
}

/** As duas pontas em `YYYY-MM`, `inicio` ≤ `fim` e no máximo 36 meses (F-11 Q2). */
export function periodoValido(inicio: string, fim: string): boolean {
  if (!mesValido(inicio) || !mesValido(fim)) {
    return false;
  }
  const meses = mesesNoPeriodo(inicio, fim);
  return meses >= 1 && meses <= MESES_NO_PERIODO_MAX;
}

/** Novo "De": um "Até" anterior vem junto; acima do limite, o "Até" encosta no limite. */
export function comInicio(atual: PeriodoHistorico, inicio: string): PeriodoHistorico {
  let fim = atual.fim;
  if (fim < inicio) {
    fim = inicio;
  } else if (mesesNoPeriodo(inicio, fim) > MESES_NO_PERIODO_MAX) {
    fim = somarMeses(inicio, MESES_NO_PERIODO_MAX - 1);
  }
  return { inicio, fim };
}

/** Novo "Até": um "De" posterior vem junto; acima do limite, o "De" encosta no limite. */
export function comFim(atual: PeriodoHistorico, fim: string): PeriodoHistorico {
  let inicio = atual.inicio;
  if (fim < inicio) {
    inicio = fim;
  } else if (mesesNoPeriodo(inicio, fim) > MESES_NO_PERIODO_MAX) {
    inicio = somarMeses(fim, 1 - MESES_NO_PERIODO_MAX);
  }
  return { inicio, fim };
}
