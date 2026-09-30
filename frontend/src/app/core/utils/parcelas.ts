/**
 * Prévia das parcelas no diálogo (F-12 Q1): espelha RN-07 **só para exibir**.
 * O backend é quem calcula o que é gravado; os testes dos dois lados usam os
 * mesmos exemplos. A conta é em centavos inteiros (RN-16).
 */
import { formatarValor } from './valor';

/** Limites de RN-07, iguais aos da API. */
export const PARCELAS_MIN = 2;
export const PARCELAS_MAX = 48;

export type Previa = { primeira: number; demais: number } | { minimo: number };

/**
 * Total ÷ N truncado no centavo; a sobra de centavos vai toda para a 1ª.
 * Total menor que N × R$ 0,01 → `{ minimo }`. `total` já validado (> 0, 2 casas).
 */
export function previaDasParcelas(total: number, parcelas: number): Previa {
  const centavos = Math.round(total * 100);
  if (centavos < parcelas) {
    return { minimo: parcelas / 100 };
  }
  const base = Math.floor(centavos / parcelas);
  const resto = centavos - base * parcelas;
  return { primeira: (base + resto) / 100, demais: base / 100 };
}

/** "3× — 1ª de R$ 333,34 e 2× de R$ 333,33" ou, se todas iguais, "10× de R$ 100,00". */
export function textoDaPrevia(parcelas: number, previa: { primeira: number; demais: number }) {
  if (previa.primeira === previa.demais) {
    return `${parcelas}× de ${reais(previa.demais)}`;
  }
  return `${parcelas}× — 1ª de ${reais(previa.primeira)} e ${parcelas - 1}× de ${reais(previa.demais)}`;
}

/** "10 parcelas exigem um valor total de no mínimo R$ 0,10." — o mesmo texto da API. */
export function mensagemDoMinimo(parcelas: number, minimo: number): string {
  return `${parcelas} parcelas exigem um valor total de no mínimo ${reais(minimo)}.`;
}

function reais(valor: number): string {
  return `R$ ${formatarValor(valor)}`;
}
