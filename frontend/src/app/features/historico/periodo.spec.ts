import { comFim, comInicio, lerPeriodo } from './periodo';

describe('historico/periodo (F-11 §3.2.1–2, Q2)', () => {
  it('sem_parametros_vale_o_padrao__CA_F11_11', () => {
    expect(lerPeriodo({})).toEqual({ periodo: null, descartar: false });
    expect(lerPeriodo({ mes: '2026-09' })).toEqual({ periodo: null, descartar: false });
  });

  it('periodo_valido_da_url__CA_F11_11', () => {
    expect(lerPeriodo({ inicio: '2026-01', fim: '2026-06' })).toEqual({
      periodo: { inicio: '2026-01', fim: '2026-06' },
      descartar: false,
    });
    // Um mês só e exatamente 36 meses são aceitos (bordas 4 e 5).
    expect(lerPeriodo({ inicio: '2026-09', fim: '2026-09' }).periodo).not.toBeNull();
    expect(lerPeriodo({ inicio: '2024-01', fim: '2026-12' }).periodo).not.toBeNull();
  });

  it.each([
    [{ inicio: '2026-01' }],
    [{ fim: '2026-01' }],
    [{ inicio: '2026-13', fim: '2026-12' }],
    [{ inicio: '2026-01', fim: 'junho' }],
    [{ inicio: '2026-09', fim: '2026-01' }], // invertido (borda 7)
    [{ inicio: '2024-01', fim: '2027-01' }], // 37 meses (borda 5)
    [{ inicio: ['2026-01', '2026-02'], fim: '2026-06' }],
  ])('url_invalida_descartada__CA_F11_12 %j', (params) => {
    expect(lerPeriodo(params)).toEqual({ periodo: null, descartar: true });
  });

  it('de_e_ate_se_ajustam__CA_F11_13', () => {
    const atual = { inicio: '2026-01', fim: '2026-06' };

    expect(comInicio(atual, '2026-03')).toEqual({ inicio: '2026-03', fim: '2026-06' });
    expect(comFim(atual, '2026-12')).toEqual({ inicio: '2026-01', fim: '2026-12' });
    // "De" depois do "Até" puxa o "Até"; "Até" antes do "De" puxa o "De".
    expect(comInicio(atual, '2026-08')).toEqual({ inicio: '2026-08', fim: '2026-08' });
    expect(comFim(atual, '2025-11')).toEqual({ inicio: '2025-11', fim: '2025-11' });
    // Acima de 36 meses, a outra ponta encosta no limite.
    expect(comInicio(atual, '2022-01')).toEqual({ inicio: '2022-01', fim: '2024-12' });
    expect(comFim(atual, '2029-06')).toEqual({ inicio: '2026-07', fim: '2029-06' });
  });
});
