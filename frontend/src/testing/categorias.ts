import { Categoria } from '../app/core/models/categoria';

/** Categoria de exemplo para os testes, no formato da API (SPECS/03 §6.3). */
export function umaCategoria(
  parcial: Partial<Categoria> & Pick<Categoria, 'id' | 'nome'>,
): Categoria {
  return {
    tipo: 'GASTO',
    cor: '#E57373',
    ativa: true,
    criado_em: '2026-09-29T10:15:00',
    em_uso: false,
    ...parcial,
  };
}
