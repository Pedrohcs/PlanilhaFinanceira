import { mensagemDoMinimo, previaDasParcelas, textoDaPrevia } from './parcelas';

/** Mesmos exemplos de `backend/tests/unit/test_parcelamento_service.py` (F-12 Q1). */
describe('parcelas', () => {
  it('previa__RN_07', () => {
    expect(previaDasParcelas(1000, 3)).toEqual({ primeira: 333.34, demais: 333.33 });
    expect(previaDasParcelas(1000, 10)).toEqual({ primeira: 100, demais: 100 });
    expect(previaDasParcelas(0.1, 3)).toEqual({ primeira: 0.04, demais: 0.03 });
    expect(previaDasParcelas(100, 48)).toEqual({ primeira: 2.24, demais: 2.08 });
    expect(previaDasParcelas(0.29, 29)).toEqual({ primeira: 0.01, demais: 0.01 }); // 0,29 × 100 sem erro binário
    expect(previaDasParcelas(0.05, 10)).toEqual({ minimo: 0.1 });
  });

  it('textos__CA_F12_12', () => {
    const texto = (s: string) => s.replace(/\u00a0/g, ' ');
    expect(texto(textoDaPrevia(3, { primeira: 333.34, demais: 333.33 }))).toBe(
      '3× — 1ª de R$ 333,34 e 2× de R$ 333,33',
    );
    expect(texto(textoDaPrevia(10, { primeira: 100, demais: 100 }))).toBe('10× de R$ 100,00');
    expect(texto(mensagemDoMinimo(10, 0.1))).toBe(
      '10 parcelas exigem um valor total de no mínimo R$ 0,10.',
    );
  });
});
