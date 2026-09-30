/**
 * Valor digitado em pt-BR (F-06 §3.2.1, Q2).
 *
 * Só interpreta e formata: nenhuma conta com dinheiro acontece no frontend
 * (RN-16) — o número vai para a API como foi digitado.
 */

export type ResultadoValor = { valor: number } | { erro: 'vazio' | 'casas' | 'invalido' };

const MILHAR = /^\d{1,3}(\.\d{3})+$/;
const INTEIRA_COM_VIRGULA = /^(\d+|\d{1,3}(\.\d{3})+)$/;
const SO_DIGITOS = /^\d+$/;
const PONTO_DECIMAL = /^(\d+)\.(\d+)$/;

const FORMATO = new Intl.NumberFormat('pt-BR', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/**
 * `1.234,56` → 1234.56 · `42,5` → 42.5 · `1.234` → 1234 · `42.50` → 42.5 ·
 * `R$ 10` → 10. Mais de 2 casas → `casas`; qualquer outra forma → `invalido`.
 */
export function interpretarValor(texto: string): ResultadoValor {
  const limpo = texto.replace(/R\$/gi, '').replace(/[\s ]/g, '');
  if (!limpo) {
    return { erro: 'vazio' };
  }

  let inteira: string;
  let decimal = '';
  const partes = limpo.split(',');
  if (partes.length > 2) {
    return { erro: 'invalido' };
  }
  if (partes.length === 2) {
    [inteira, decimal] = partes;
    if (!INTEIRA_COM_VIRGULA.test(inteira) || !SO_DIGITOS.test(decimal)) {
      return { erro: 'invalido' };
    }
    inteira = inteira.replace(/\./g, '');
  } else if (MILHAR.test(limpo)) {
    inteira = limpo.replace(/\./g, '');
  } else if (PONTO_DECIMAL.test(limpo)) {
    [, inteira, decimal] = PONTO_DECIMAL.exec(limpo)!;
  } else if (SO_DIGITOS.test(limpo)) {
    inteira = limpo;
  } else {
    return { erro: 'invalido' };
  }

  if (decimal.length > 2) {
    return { erro: 'casas' };
  }
  return { valor: Number(`${inteira}.${decimal || '0'}`) };
}

/** 1234.5 → `1.234,50` (reescrita do campo ao sair dele). */
export function formatarValor(valor: number): string {
  return FORMATO.format(valor);
}
