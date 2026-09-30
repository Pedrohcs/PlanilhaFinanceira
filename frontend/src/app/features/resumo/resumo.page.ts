import { BreakpointObserver } from '@angular/cdk/layout';
import {
  ChangeDetectionStrategy,
  Component,
  effect,
  inject,
  signal,
  untracked,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { firstValueFrom, map } from 'rxjs';
import { ResumoApi } from '../../core/api/resumo.api';
import { ResumoMensal } from '../../core/models/resumo';
import { DadosStore } from '../../core/state/dados.store';
import { MesSelecionadoStore } from '../../core/state/mes-selecionado.store';
import { mesPorExtenso } from '../../core/utils/mes';
import { formatarMontante, formatarPercentual } from '../../core/utils/valor';
import { Carregando } from '../../shared/components/carregando/carregando';
import { EstadoVazio } from '../../shared/components/estado-vazio/estado-vazio';
import { SeletorMes } from '../../shared/components/seletor-mes/seletor-mes';
import { Totais } from '../../shared/components/totais/totais';

/** A partir desta largura as duas tabelas ficam lado a lado (F-09 §3.2.5). */
export const LARGURA_LADO_A_LADO = 960;

/**
 * Resumo do mês (REQ-12; F-09 §3.2): cards de totais e gastos por categoria e
 * por forma de pagamento, tudo pronto da API — o frontend não soma (`03` §4.2).
 * Recarrega quando o mês ou `versao` mudam (CA-01.5).
 */
@Component({
  selector: 'app-resumo-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SeletorMes, Totais, Carregando, EstadoVazio],
  templateUrl: './resumo.page.html',
  styleUrl: './resumo.page.scss',
})
export class ResumoPage {
  private readonly api = inject(ResumoApi);
  private readonly mesStore = inject(MesSelecionadoStore);
  private readonly dados = inject(DadosStore);
  private readonly breakpoints = inject(BreakpointObserver);

  protected readonly resumo = signal<ResumoMensal | null>(null);
  protected readonly carregando = signal(false);
  protected readonly erro = signal(false);
  private sequencia = 0;

  protected readonly ladoALado = toSignal(
    this.breakpoints
      .observe(`(min-width: ${LARGURA_LADO_A_LADO}px)`)
      .pipe(map((estado) => estado.matches)),
    { initialValue: this.breakpoints.isMatched(`(min-width: ${LARGURA_LADO_A_LADO}px)`) },
  );

  constructor() {
    effect(() => {
      const mes = this.mesStore.mes();
      this.dados.versao();
      untracked(() => void this.carregar(mes));
    });
  }

  protected montante(valor: number): string {
    return formatarMontante(valor);
  }

  protected percentual(valor: number): string {
    return formatarPercentual(valor);
  }

  protected mesPorExtenso(mes: string): string {
    return mesPorExtenso(mes);
  }

  /** Uma busca por vez vale: resposta de busca anterior é descartada (F-07 borda 15). */
  private async carregar(mes: string): Promise<void> {
    const minha = ++this.sequencia;
    this.carregando.set(true);
    try {
      const resumo = await firstValueFrom(this.api.mensal(mes));
      if (minha === this.sequencia) {
        this.resumo.set(resumo);
        this.erro.set(false);
      }
    } catch {
      if (minha === this.sequencia) {
        this.resumo.set(null);
        this.erro.set(true); // a causa já foi mostrada pelo interceptor/banner
      }
    } finally {
      if (minha === this.sequencia) {
        this.carregando.set(false);
      }
    }
  }
}
