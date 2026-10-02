import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDatepicker, MatDatepickerModule } from '@angular/material/datepicker';
import { MatIconModule } from '@angular/material/icon';
import { MesSelecionadoStore } from '../../../core/state/mes-selecionado.store';
import {
  dataParaMes,
  mesAnterior,
  mesParaData,
  mesPorExtenso,
  proximoMes,
} from '../../../core/utils/mes';
import { DATEPICKER_PT_BR } from '../../../core/utils/datepicker-intl';

/**
 * Seletor do mês de referência (REQ-04; F-04 §3.5.2).
 *
 * ‹ e › andam um mês; o nome do mês abre o datepicker direto na escolha de
 * ano → mês, e ele fecha ao escolher o mês (F-04 Q7). Lê e escreve no
 * `MesSelecionadoStore`.
 */
@Component({
  selector: 'app-seletor-mes',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [DATEPICKER_PT_BR],
  imports: [MatButtonModule, MatDatepickerModule, MatIconModule],
  template: `
    <button matIconButton type="button" aria-label="Mês anterior" (click)="anterior()">
      <mat-icon>chevron_left</mat-icon>
    </button>
    <span class="ancora">
      <button
        matButton
        type="button"
        class="nome"
        aria-label="Escolher mês"
        (click)="calendario.open()"
      >
        {{ extenso() }}
      </button>
      <!-- O datepicker exige um input: invisível, só para ancorar e marcar o mês atual. -->
      <input
        class="ancora-input"
        tabindex="-1"
        aria-hidden="true"
        [matDatepicker]="calendario"
        [value]="data()"
      />
      <mat-datepicker
        #calendario
        startView="multi-year"
        (monthSelected)="escolher($event, calendario)"
      />
    </span>
    <button matIconButton type="button" aria-label="Próximo mês" (click)="proximo()">
      <mat-icon>chevron_right</mat-icon>
    </button>
  `,
  styles: `
    :host {
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    .ancora {
      position: relative;
    }
    .nome {
      min-width: 11rem;
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
export class SeletorMes {
  private readonly store = inject(MesSelecionadoStore);

  protected readonly extenso = computed(() => mesPorExtenso(this.store.mes()));
  protected readonly data = computed(() => mesParaData(this.store.mes()));

  protected anterior(): void {
    this.store.definir(mesAnterior(this.store.mes()));
  }

  protected proximo(): void {
    this.store.definir(proximoMes(this.store.mes()));
  }

  protected escolher(data: Date, calendario: MatDatepicker<Date>): void {
    this.store.definir(dataParaMes(data));
    calendario.close();
  }
}
