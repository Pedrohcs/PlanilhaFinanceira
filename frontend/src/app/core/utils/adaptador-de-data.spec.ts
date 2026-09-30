import { TestBed } from '@angular/core/testing';
import { DateAdapter, MAT_DATE_LOCALE, provideNativeDateAdapter } from '@angular/material/core';
import { AdaptadorDeDataPtBr, dataParaIso, hoje } from './adaptador-de-data';

describe('AdaptadorDeDataPtBr', () => {
  let adaptador: DateAdapter<Date>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideNativeDateAdapter(),
        { provide: DateAdapter, useClass: AdaptadorDeDataPtBr },
        { provide: MAT_DATE_LOCALE, useValue: 'pt-BR' },
      ],
    });
    adaptador = TestBed.inject(DateAdapter);
  });

  it('interpreta_dd_mm_aaaa__F06_borda_5', () => {
    expect(adaptador.parse('30/09/2026', {})).toEqual(new Date(2026, 8, 30));
    expect(adaptador.parse('05/09/2026', {})).toEqual(new Date(2026, 8, 5)); // não 9 de maio
    expect(adaptador.parse('1/2/2026', {})).toEqual(new Date(2026, 1, 1));
    expect(adaptador.parse('29/02/2024', {})).toEqual(new Date(2024, 1, 29));
    expect(adaptador.parse('', {})).toBeNull();

    for (const invalida of [
      '29/02/2025',
      '31/04/2026',
      '00/01/2026',
      '2026-09-30',
      '30/09/26',
      'abc',
    ]) {
      const data = adaptador.parse(invalida, {});
      expect(data && adaptador.isValid(data), invalida).toBe(false);
    }
  });

  it('exibe_em_ptBR', () => {
    expect(
      adaptador.format(new Date(2026, 8, 5), { year: 'numeric', month: '2-digit', day: '2-digit' }),
    ).toBe('05/09/2026');
  });

  it('data_para_iso_e_hoje', () => {
    expect(dataParaIso(new Date(2026, 0, 3))).toBe('2026-01-03');
    expect(dataParaIso(new Date(2030, 11, 31, 23, 59))).toBe('2030-12-31');

    const agora = new Date();
    const inicioDoDia = hoje();
    expect(inicioDoDia.getHours()).toBe(0);
    expect(dataParaIso(inicioDoDia)).toBe(dataParaIso(agora));
  });
});
