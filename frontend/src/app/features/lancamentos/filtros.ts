import { Params } from '@angular/router';
import { FormaPagamento, TipoLancamento } from '../../core/models/enums';
import { FiltrosLancamentos } from '../../core/models/lancamento';

const TIPOS: readonly TipoLancamento[] = ['GASTO', 'RECEITA'];
const FORMAS: readonly FormaPagamento[] = [
  'PIX',
  'CREDITO',
  'DEBITO',
  'DINHEIRO',
  'BOLETO',
  'TRANSFERENCIA',
];

/** Nomes dos parâmetros na URL (iguais aos da API — ADR-09). */
export const PARAMETROS_DE_FILTRO = ['tipo', 'categoria_id', 'forma_pagamento'] as const;

export interface LeituraDeFiltros {
  filtros: FiltrosLancamentos;
  /** Algum parâmetro tinha valor inválido e foi descartado: a URL precisa ser corrigida. */
  descartou: boolean;
}

/**
 * Filtros a partir da URL (F-07 Q1). Tipo e forma fora do enum são
 * descartados; `categoria_id` é texto livre (inexistente = lista vazia).
 */
export function lerFiltros(params: Params): LeituraDeFiltros {
  const texto = (chave: string): string | null => {
    const valor: unknown = params[chave];
    return typeof valor === 'string' && valor !== '' ? valor : null;
  };
  const tipoBruto = texto('tipo');
  const formaBruta = texto('forma_pagamento');
  const tipo = TIPOS.find((t) => t === tipoBruto) ?? null;
  const forma = FORMAS.find((f) => f === formaBruta) ?? null;
  return {
    filtros: { tipo, categoria_id: texto('categoria_id'), forma_pagamento: forma },
    descartou: (tipoBruto !== null && tipo === null) || (formaBruta !== null && forma === null),
  };
}

/** Parâmetros de URL para os filtros; `null` remove o parâmetro. */
export function filtrosParaParams(filtros: FiltrosLancamentos): Params {
  return {
    tipo: filtros.tipo,
    categoria_id: filtros.categoria_id,
    forma_pagamento: filtros.forma_pagamento,
  };
}

export function temFiltro(filtros: FiltrosLancamentos): boolean {
  return PARAMETROS_DE_FILTRO.some((chave) => filtros[chave] !== null);
}
