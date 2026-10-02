import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

/**
 * Faixa "N linhas da planilha foram ignoradas…" (CA-16.3; F-14 §3.4). O
 * número vem pronto da API (`linhas_ignoradas`); com 0, nada aparece. Usada
 * por lançamentos, resumo e histórico.
 */
@Component({
  selector: 'app-aviso-linhas-ignoradas',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatIconModule],
  template: `
    @if (quantidade() > 0) {
      <div class="aviso" role="status">
        <mat-icon aria-hidden="true">warning</mat-icon>
        <p>
          {{ frase() }} {{ quantidade() === 1 ? 'Corrija-a' : 'Corrija-as' }} na planilha e use
          <strong>Recarregar dados</strong>.
        </p>
      </div>
    }
  `,
  styles: `
    .aviso {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      margin-bottom: 16px;
      padding: 12px 16px;
      border-radius: 12px;
      background: var(--mat-sys-surface-container-high);
      color: var(--mat-sys-on-surface);
      font: var(--mat-sys-body-medium);
    }
    mat-icon {
      flex: 0 0 auto;
      color: var(--mat-sys-error);
    }
    p {
      margin: 0;
      overflow-wrap: anywhere;
    }
  `,
})
export class AvisoLinhasIgnoradas {
  readonly quantidade = input.required<number>();

  protected readonly frase = computed(() =>
    this.quantidade() === 1
      ? '1 linha da planilha foi ignorada por estar inválida.'
      : `${this.quantidade()} linhas da planilha foram ignoradas por estarem inválidas.`,
  );
}
