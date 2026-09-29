import { CurrencyPipe, DatePipe } from '@angular/common';
import { DEFAULT_CURRENCY_CODE, LOCALE_ID } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { appConfig } from './app.config';

/** O CurrencyPipe em pt-BR separa `R$` do número com espaço não-quebrável. */
function semEspacoFixo(texto: string | null): string {
  return (texto ?? '').replace(/ /g, ' ');
}

describe('appConfig', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...appConfig.providers] });
  });

  it('registra o locale pt-BR e o real como moeda padrão__CA_F01_17', () => {
    expect(TestBed.inject(LOCALE_ID)).toBe('pt-BR');
    expect(TestBed.inject(DEFAULT_CURRENCY_CODE)).toBe('BRL');
  });

  it('formata_moeda_e_data_ptBR__CA_F01_17', () => {
    const locale = TestBed.inject(LOCALE_ID);
    const moeda = TestBed.inject(DEFAULT_CURRENCY_CODE);

    const valor = new CurrencyPipe(locale, moeda).transform(1234.56);
    const data = new DatePipe(locale).transform('2026-09-29', 'dd/MM/yyyy');

    expect(semEspacoFixo(valor)).toBe('R$ 1.234,56');
    expect(data).toBe('29/09/2026');
  });
});
