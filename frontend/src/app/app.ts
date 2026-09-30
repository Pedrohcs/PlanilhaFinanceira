import { BreakpointObserver } from '@angular/cdk/layout';
import { ChangeDetectionStrategy, Component, inject, Signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatSidenav, MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { map } from 'rxjs';

/** A partir desta largura, a navegação lateral fica fixa e aberta (F-04 Q1). */
export const LARGURA_NAVEGACAO_FIXA = 960;
/** A partir desta largura, a barra mostra o título e os rótulos completos (F-04 Q1). */
export const LARGURA_BARRA_COMPLETA = 600;

export interface ItemDeNavegacao {
  rotulo: string;
  rota: string;
  icone: string;
}

/** Ordem e ícones de F-04 §3.1. */
export const ITENS_DE_NAVEGACAO: readonly ItemDeNavegacao[] = [
  { rotulo: 'Resumo', rota: '/resumo', icone: 'dashboard' },
  { rotulo: 'Lançamentos', rota: '/lancamentos', icone: 'receipt_long' },
  { rotulo: 'Histórico', rota: '/historico', icone: 'bar_chart' },
  { rotulo: 'Categorias', rota: '/categorias', icone: 'sell' },
  { rotulo: 'Recorrências', rota: '/recorrencias', icone: 'event_repeat' },
];

/**
 * Shell do app (SPECS/03 §8.1): barra superior com as ações de registro,
 * navegação lateral e a área das páginas. Os botões de registro ganham ação
 * em T-016; o banner de conexão entra em T-011/T-012.
 */
@Component({
  selector: 'app-root',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatToolbarModule,
    MatButtonModule,
    MatIconModule,
    MatSidenavModule,
    MatListModule,
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  private readonly breakpoints = inject(BreakpointObserver);

  protected readonly itensDeNavegacao = ITENS_DE_NAVEGACAO;
  protected readonly navegacaoFixa = this.aPartirDe(LARGURA_NAVEGACAO_FIXA);
  protected readonly barraCompleta = this.aPartirDe(LARGURA_BARRA_COMPLETA);

  /** Na navegação sobreposta, escolher um item fecha o menu. */
  protected aoEscolherItem(menu: MatSidenav): void {
    if (!this.navegacaoFixa()) {
      void menu.close();
    }
  }

  private aPartirDe(largura: number): Signal<boolean> {
    const consulta = `(min-width: ${largura}px)`;
    return toSignal(this.breakpoints.observe(consulta).pipe(map((estado) => estado.matches)), {
      // Valor certo já na 1ª renderização: sem o menu "piscar" ao abrir.
      initialValue: this.breakpoints.isMatched(consulta),
    });
  }
}
