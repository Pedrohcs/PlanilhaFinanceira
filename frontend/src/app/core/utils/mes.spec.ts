import {
  dataParaMes,
  mesAnterior,
  mesCorrente,
  mesParaData,
  mesPorExtenso,
  mesValido,
  proximoMes,
} from './mes';

describe('utils/mes', () => {
  it('proximo_e_anterior_cruzam_o_ano__CA_F04_19', () => {
    expect(proximoMes('2026-12')).toBe('2027-01');
    expect(proximoMes('2026-09')).toBe('2026-10');
    expect(mesAnterior('2027-01')).toBe('2026-12');
    expect(mesAnterior('2026-10')).toBe('2026-09');
  });

  it('mes_por_extenso_ptBR__CA_F04_20', () => {
    expect(mesPorExtenso('2026-09')).toBe('setembro de 2026');
    expect(mesPorExtenso('2027-01')).toBe('janeiro de 2027');
    expect(mesPorExtenso('2025-03')).toBe('março de 2025');
  });

  it('mes_valido', () => {
    for (const valido of ['2026-09', '1999-01', '2026-12']) {
      expect(mesValido(valido)).toBe(true);
    }
    for (const invalido of [
      '2026-13',
      '2026-00',
      'abc',
      '',
      '2026-9',
      '2026-09-01',
      null,
      undefined,
    ]) {
      expect(mesValido(invalido)).toBe(false);
    }
  });

  it('mes_corrente_e_conversoes_com_date', () => {
    expect(mesCorrente(new Date(2026, 8, 30, 23, 59))).toBe('2026-09');
    expect(mesCorrente(new Date(2027, 0, 1, 0, 0))).toBe('2027-01');
    expect(mesParaData('2025-03')).toEqual(new Date(2025, 2, 1));
    expect(dataParaMes(new Date(2025, 2, 17))).toBe('2025-03');
    expect(() => proximoMes('2026-13')).toThrow();
  });
});
