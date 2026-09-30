import { umaCategoria } from '../../../testing/categorias';
import { corSugerida, PALETA } from './paleta';

describe('paleta de categorias (F-05 §3.4)', () => {
  it('24_cores_unicas_e_sugestao__CA_F05_24', () => {
    expect(PALETA).toHaveLength(24);
    expect(new Set(PALETA).size).toBe(24);
    expect(PALETA.every((cor) => /^#[0-9A-F]{6}$/.test(cor))).toBe(true);

    // As 11 cores padrão de gasto em uso (F-03 §3.4) → a primeira livre é a 12ª da paleta.
    const gastosPadrao = PALETA.slice(0, 11).map((cor, i) =>
      umaCategoria({ id: `g${i}`, nome: `G${i}`, cor: cor.toLowerCase() }),
    );
    expect(corSugerida('GASTO', gastosPadrao)).toBe(PALETA[11]);

    // Cores de outro tipo não contam.
    expect(corSugerida('RECEITA', gastosPadrao)).toBe(PALETA[0]);

    // Todas em uso → a primeira.
    const todas = PALETA.map((cor, i) => umaCategoria({ id: `c${i}`, nome: `C${i}`, cor }));
    expect(corSugerida('GASTO', todas)).toBe(PALETA[0]);
  });
});
