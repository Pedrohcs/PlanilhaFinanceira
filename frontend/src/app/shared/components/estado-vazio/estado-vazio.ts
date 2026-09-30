import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

/** Mensagem para lista ou gráfico sem dados (ex.: CA-03.3; F-04 §3.5.4). */
@Component({
  selector: 'app-estado-vazio',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatIconModule],
  template: `
    <mat-icon aria-hidden="true">{{ icone() }}</mat-icon>
    <p>{{ mensagem() }}</p>
  `,
  styles: `
    :host {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      padding: 32px 16px;
      color: var(--mat-sys-on-surface-variant);
      text-align: center;
    }
    p {
      margin: 0;
    }
  `,
})
export class EstadoVazio {
  readonly mensagem = input.required<string>();
  readonly icone = input('inbox');
}
