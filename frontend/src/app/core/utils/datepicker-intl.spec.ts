import { TestBed } from '@angular/core/testing';
import { MatDatepickerIntl } from '@angular/material/datepicker';
import { DATEPICKER_PT_BR, DatepickerIntlPtBr } from './datepicker-intl';

describe('DatepickerIntlPtBr (RNF-03; F-14 §3.1.3)', () => {
  it('textos_do_calendario_em_ptbr__CA_F14_3', () => {
    TestBed.configureTestingModule({ providers: [DATEPICKER_PT_BR] });
    const intl = TestBed.inject(MatDatepickerIntl);

    expect(intl).toBeInstanceOf(DatepickerIntlPtBr);
    expect(intl.openCalendarLabel).toBe('Abrir calendário');
    expect(intl.switchToMultiYearViewLabel).toBe('Escolher mês e ano');
    expect(intl.prevMultiYearLabel).toBe('24 anos anteriores');
    expect(intl.formatYearRange('2016', '2039')).toBe('2016 – 2039');
    expect(intl.formatYearRangeLabel('2016', '2039')).toBe('2016 a 2039');
  });
});
