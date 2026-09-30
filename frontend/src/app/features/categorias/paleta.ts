import { Categoria } from '../../core/models/categoria';
import { TipoLancamento } from '../../core/models/enums';

/**
 * Paleta de cores das categorias (F-05 §3.4, Q2): as 15 das categorias padrão
 * e mais 9, todas distinguíveis entre si e legíveis nos temas claro e escuro.
 * É regra da interface: a API aceita qualquer `#RRGGBB`.
 */
export const PALETA: readonly string[] = [
  // Padrão (F-03 §3.4)
  '#E57373',
  '#FF8A65',
  '#7986CB',
  '#4FC3F7',
  '#4DD0E1',
  '#F06292',
  '#7E57C2',
  '#FFB74D',
  '#A1887F',
  '#BA68C8',
  '#90A4AE',
  '#66BB6A',
  '#9CCC65',
  '#26A69A',
  '#AED581',
  // Extras
  '#64B5F6',
  '#FFD54F',
  '#DCE775',
  '#4DB6AC',
  '#9575CD',
  '#F48FB1',
  '#FF7043',
  '#8D6E63',
  '#78909C',
];

/** Primeira cor da paleta que nenhuma categoria do tipo usa; todas usadas → a primeira. */
export function corSugerida(tipo: TipoLancamento, categorias: readonly Categoria[]): string {
  const usadas = new Set(
    categorias.filter((categoria) => categoria.tipo === tipo).map((c) => c.cor.toUpperCase()),
  );
  return PALETA.find((cor) => !usadas.has(cor)) ?? PALETA[0];
}
