import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

/** Indicador de carregamento, anunciado a leitores de tela (F-04 §3.5.5). */
@Component({
  selector: 'app-carregando',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatProgressSpinnerModule],
  host: { role: 'status', 'aria-live': 'polite' },
  template: `
    <mat-progress-spinner mode="indeterminate" diameter="32" aria-hidden="true" />
    <span>{{ texto() }}</span>
  `,
  styles: `
    :host {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 12px;
      padding: 24px 16px;
    }
  `,
})
export class Carregando {
  readonly texto = input('Carregando…');
}
