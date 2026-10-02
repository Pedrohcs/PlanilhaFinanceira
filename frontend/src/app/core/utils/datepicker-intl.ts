import { Injectable, Provider } from '@angular/core';
import { MatDatepickerIntl } from '@angular/material/datepicker';

/**
 * Textos do datepicker do Material em pt-BR (RNF-03; F-14 §3.1.3). Os padrões
 * são em inglês ("Choose month and year", "Open calendar"…) e aparecem em
 * rótulos de leitor de tela e dicas dos botões do calendário.
 */
@Injectable()
export class DatepickerIntlPtBr extends MatDatepickerIntl {
  override calendarLabel = 'Calendário';
  override openCalendarLabel = 'Abrir calendário';
  override closeCalendarLabel = 'Fechar calendário';
  override prevMonthLabel = 'Mês anterior';
  override nextMonthLabel = 'Próximo mês';
  override prevYearLabel = 'Ano anterior';
  override nextYearLabel = 'Próximo ano';
  override prevMultiYearLabel = '24 anos anteriores';
  override nextMultiYearLabel = 'Próximos 24 anos';
  override switchToMonthViewLabel = 'Escolher data';
  override switchToMultiYearViewLabel = 'Escolher mês e ano';
  override startDateLabel = 'Data inicial';
  override endDateLabel = 'Data final';
  override comparisonDateLabel = 'Período de comparação';

  override formatYearRange(inicio: string, fim: string): string {
    return `${inicio} – ${fim}`;
  }

  override formatYearRangeLabel(inicio: string, fim: string): string {
    return `${inicio} a ${fim}`;
  }
}

/**
 * Para os `providers` de cada componente que usa o datepicker. Não vai no
 * `app.config`: importar o datepicker lá o levaria inteiro para o pacote
 * inicial (+265 kB, conferido em T-031). O calendário abre num overlay criado
 * a partir do elemento do datepicker, então o provider do componente vale para ele.
 */
export const DATEPICKER_PT_BR: Provider = {
  provide: MatDatepickerIntl,
  useClass: DatepickerIntlPtBr,
};
