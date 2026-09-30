import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { formatarMontante } from '../../../core/utils/valor';

/**
 * Cards Gastos, Receitas e Saldo, com os números prontos da API (o frontend
 * não soma — `03` §4.2). Saldo negativo destacado (CA-12.2). Usado pelo
 * resumo (F-09) e pela listagem (F-07); o conteúdo projetado vira uma legenda
 * de largura inteira.
 */
@Component({
  selector: 'app-totais',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="totais" aria-label="Totais">
      <div class="total">
        <span class="rotulo">Gastos</span>
        <span class="numero">{{ montante(gastos()) }}</span>
      </div>
      <div class="total">
        <span class="rotulo">Receitas</span>
        <span class="numero">{{ montante(receitas()) }}</span>
      </div>
      <div class="total saldo" [class.negativo]="saldo() < 0">
        <span class="rotulo">Saldo</span>
        <span class="numero">{{ montante(saldo()) }}</span>
      </div>
      <ng-content />
    </section>
  `,
  styles: `
    :host {
      display: block;
    }
    .totais {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }
    .total {
      display: flex;
      flex-direction: column;
      padding: 12px 16px;
      border-radius: 12px;
      background: var(--mat-sys-surface-container);
    }
    .rotulo {
      font: var(--mat-sys-label-medium);
      color: var(--mat-sys-on-surface-variant);
    }
    .numero {
      font: var(--mat-sys-title-medium);
      font-variant-numeric: tabular-nums;
    }
    .saldo.negativo {
      background: var(--mat-sys-error-container);
      color: var(--mat-sys-on-error-container);
    }
    .saldo.negativo .rotulo {
      color: inherit;
    }
  `,
})
export class Totais {
  readonly gastos = input.required<number>();
  readonly receitas = input.required<number>();
  readonly saldo = input.required<number>();

  protected montante(valor: number): string {
    return formatarMontante(valor);
  }
}
