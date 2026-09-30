import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { ConexaoStore } from '../../../core/state/conexao.store';

/**
 * Faixa de falha de conexão, no topo da área das páginas (SPECS/03 §7.2;
 * F-04 §3.5.6). Persistente: sem botão de fechar. Mostra a mensagem do
 * backend sem reescrita, e "Tentar novamente" consulta o health de novo
 * sem reiniciar nada (CA-16.2).
 */
@Component({
  selector: 'app-banner-conexao',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatButtonModule, MatIconModule],
  template: `
    @if (conexao.estado() === 'falha') {
      <div class="banner" role="alert">
        <mat-icon aria-hidden="true">cloud_off</mat-icon>
        <span class="mensagem">{{ conexao.mensagem() }}</span>
        <button
          matButton
          type="button"
          class="tentar"
          [disabled]="conexao.tentando()"
          (click)="conexao.tentarNovamente()"
        >
          {{ conexao.tentando() ? 'Tentando…' : 'Tentar novamente' }}
        </button>
      </div>
    }
  `,
  styles: `
    .banner {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      background: var(--mat-sys-error-container);
      color: var(--mat-sys-on-error-container);
    }
    .mensagem {
      flex: 1 1 auto;
      overflow-wrap: anywhere;
    }
    .tentar {
      flex: 0 0 auto;
      color: inherit;
    }
  `,
})
export class BannerConexao {
  protected readonly conexao = inject(ConexaoStore);
}
