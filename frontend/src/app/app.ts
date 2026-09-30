import { BreakpointObserver } from '@angular/cdk/layout';
import { ChangeDetectionStrategy, Component, inject, Injector, Signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSidenav, MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { map } from 'rxjs';
import { TipoLancamento } from './core/models/enums';
import { MesSelecionadoStore } from './core/state/mes-selecionado.store';
import { BannerConexao } from './shared/components/banner-conexao/banner-conexao';

/** A partir desta largura, a navegação lateral fica fixa e aberta (F-04 Q1). */
export const LARGURA_NAVEGACAO_FIXA = 960;
/** A partir desta largura, a barra mostra o título e os rótulos completos (F-04 Q1). */
export const LARGURA_BARRA_COMPLETA = 600;

export interface ItemDeNavegacao {
  rotulo: string;
  rota: string;
  icone: string;
  /** Tela que mostra um mês: o link leva o `?mes=` selecionado (CA-04.2). */
  comMes: boolean;
}

/** Ordem e ícones de F-04 §3.1. */
export const ITENS_DE_NAVEGACAO: readonly ItemDeNavegacao[] = [
  { rotulo: 'Resumo', rota: '/resumo', icone: 'dashboard', comMes: true },
  { rotulo: 'Lançamentos', rota: '/lancamentos', icone: 'receipt_long', comMes: true },
  { rotulo: 'Histórico', rota: '/historico', icone: 'bar_chart', comMes: false },
  { rotulo: 'Categorias', rota: '/categorias', icone: 'sell', comMes: false },
  { rotulo: 'Recorrências', rota: '/recorrencias', icone: 'event_repeat', comMes: false },
];

/**
 * Shell do app (SPECS/03 §8.1): barra superior com as ações de registro,
 * navegação lateral, banner de conexão e a área das páginas. Os botões de
 * registro abrem o diálogo de lançamento (F-06), carregado sob demanda.
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
    BannerConexao,
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  private readonly breakpoints = inject(BreakpointObserver);
  private readonly injetor = inject(Injector);
  protected readonly mesSelecionado = inject(MesSelecionadoStore);
  /** O item ativo depende só do caminho: `/resumo` e `/resumo?mes=…` são a mesma tela. */
  protected readonly comparacaoDoAtivo = {
    paths: 'subset',
    queryParams: 'ignored',
    matrixParams: 'ignored',
    fragment: 'ignored',
  } as const;

  protected readonly itensDeNavegacao = ITENS_DE_NAVEGACAO;
  protected readonly navegacaoFixa = this.aPartirDe(LARGURA_NAVEGACAO_FIXA);
  protected readonly barraCompleta = this.aPartirDe(LARGURA_BARRA_COMPLETA);

  /**
   * "Registrar gasto/receita" (REQ-01, REQ-02). O código do diálogo só é
   * baixado no primeiro clique: o shell fica leve (CA-F06.15).
   */
  protected async registrar(tipo: TipoLancamento): Promise<void> {
    const { abrirLancamento } = await import('./features/lancamentos/abrir-lancamento');
    await abrirLancamento(this.injetor, tipo);
  }

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
