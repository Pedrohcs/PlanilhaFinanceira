import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDatepicker, MatDatepickerModule } from '@angular/material/datepicker';
import { PeriodoHistorico } from '../../core/models/resumo';
import { dataParaMes, mesParaData, mesPorExtenso } from '../../core/utils/mes';
import { comFim, comInicio } from './periodo';

/**
 * Período do histórico (F-11 §3.2.1, Q1): "De" e "Até", cada um abrindo o
 * datepicker na escolha ano → mês (como o seletor de mês de F-04, Q7), e
 * "Últimos 12 meses" para voltar ao padrão.
 *
 * Emite o período já ajustado (a outra ponta vem junto e o limite de 36 meses
 * é respeitado — Q2), então a página nunca pede um período que a API recusa.
 */
@Component({
  selector: 'app-seletor-intervalo',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatButtonModule, MatDatepickerModule],
  template: `
    <span class="ponta">
      <span class="rotulo" aria-hidden="true">De</span>
      <span class="ancora">
        <button
          matButton="outlined"
          type="button"
          class="inicio"
          [attr.aria-label]="'Mês inicial do período: ' + extenso(periodo().inicio)"
          (click)="calendarioInicio.open()"
        >
          {{ extenso(periodo().inicio) }}
        </button>
        <!-- O datepicker exige um input: invisível, só para ancorar e marcar o mês. -->
        <input
          class="ancora-input"
          tabindex="-1"
          aria-hidden="true"
          [matDatepicker]="calendarioInicio"
          [value]="dataInicio()"
        />
        <mat-datepicker
          #calendarioInicio
          startView="multi-year"
          (monthSelected)="escolherInicio($event, calendarioInicio)"
        />
      </span>
    </span>
    <span class="ponta">
      <span class="rotulo" aria-hidden="true">Até</span>
      <span class="ancora">
        <button
          matButton="outlined"
          type="button"
          class="fim"
          [attr.aria-label]="'Mês final do período: ' + extenso(periodo().fim)"
          (click)="calendarioFim.open()"
        >
          {{ extenso(periodo().fim) }}
        </button>
        <input
          class="ancora-input"
          tabindex="-1"
          aria-hidden="true"
          [matDatepicker]="calendarioFim"
          [value]="dataFim()"
        />
        <mat-datepicker
          #calendarioFim
          startView="multi-year"
          (monthSelected)="escolherFim($event, calendarioFim)"
        />
      </span>
    </span>
    <button matButton type="button" class="padrao" (click)="ultimos12.emit()">
      Últimos 12 meses
    </button>
  `,
  styles: `
    :host {
      display: inline-flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px 12px;
    }
    .ponta {
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .rotulo {
      font: var(--mat-sys-label-large);
      color: var(--mat-sys-on-surface-variant);
    }
    .ancora {
      position: relative;
    }
    .ancora-input {
      position: absolute;
      left: 0;
      bottom: 0;
      width: 0;
      height: 0;
      padding: 0;
      border: 0;
      opacity: 0;
      pointer-events: none;
    }
  `,
})
export class SeletorIntervalo {
  readonly periodo = input.required<PeriodoHistorico>();
  /** Novo período, já ajustado (F-11 Q2). */
  readonly mudou = output<PeriodoHistorico>();
  /** "Últimos 12 meses": a página volta ao padrão da API. */
  readonly ultimos12 = output<void>();

  protected readonly dataInicio = computed(() => mesParaData(this.periodo().inicio));
  protected readonly dataFim = computed(() => mesParaData(this.periodo().fim));

  protected extenso(mes: string): string {
    return mesPorExtenso(mes);
  }

  protected escolherInicio(data: Date, calendario: MatDatepicker<Date>): void {
    this.mudou.emit(comInicio(this.periodo(), dataParaMes(data)));
    calendario.close();
  }

  protected escolherFim(data: Date, calendario: MatDatepicker<Date>): void {
    this.mudou.emit(comFim(this.periodo(), dataParaMes(data)));
    calendario.close();
  }
}
