import { BreakpointObserver } from '@angular/cdk/layout';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  signal,
  untracked,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ChartData, ChartOptions, TooltipItem } from 'chart.js';
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
import { GraficoDirective } from '../../shared/grafico/grafico.directive';

/** A partir desta largura as duas tabelas ficam lado a lado (F-09 §3.2.5). */
export const LARGURA_LADO_A_LADO = 960;

/** Sem legenda: a tabela com a bolinha da cor faz esse papel (F-10 §3.2.3). */
const SEM_LEGENDA = { legend: { display: false } };

const OPCOES_ROSCA: ChartOptions<'doughnut'> = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: SEM_LEGENDA,
};

/** Horizontais: "Cartão de crédito" cabe em 360 px (F-10 §3.3). */
const OPCOES_BARRAS: ChartOptions<'bar'> = {
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: 'y',
  plugins: SEM_LEGENDA,
};

const OPCOES_LINHA: ChartOptions<'line'> = {
  responsive: true,
  maintainAspectRatio: false,
  elements: { point: { radius: 2 }, line: { fill: false, tension: 0 } },
  scales: { y: { beginAtZero: true } },
  plugins: {
    ...SEM_LEGENDA,
    tooltip: {
      callbacks: { title: (itens: TooltipItem<'line'>[]) => `Dia ${itens[0]?.label ?? ''}` },
    },
  },
};

/**
 * Resumo do mês (REQ-12, REQ-13; F-09 §3.2, F-10 §3): cards de totais, gastos
 * por categoria e por forma de pagamento (gráfico acima da tabela) e o gasto
 * acumulado dia a dia — tudo pronto da API; o frontend não soma (`03` §4.2).
 * Recarrega quando o mês ou `versao` mudam (CA-01.5).
 */
@Component({
  selector: 'app-resumo-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SeletorMes, Totais, Carregando, EstadoVazio, GraficoDirective],
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

  protected readonly opcoesRosca = OPCOES_ROSCA as ChartOptions;
  protected readonly opcoesBarras = OPCOES_BARRAS as ChartOptions;
  protected readonly opcoesLinha = OPCOES_LINHA as ChartOptions;

  /** Arcos nas cores das categorias (CA-13.1). */
  protected readonly dadosRosca = computed<ChartData>(() => {
    const itens = this.resumo()?.por_categoria ?? [];
    return {
      labels: itens.map((item) => item.nome),
      datasets: [
        { data: itens.map((item) => item.total), backgroundColor: itens.map((item) => item.cor) },
      ],
    };
  });

  /** Uma série; a cor de destaque do tema vem dos padrões da diretiva (F-10 §3.3). */
  protected readonly dadosBarras = computed<ChartData>(() => {
    const itens = this.resumo()?.por_forma_pagamento ?? [];
    return {
      labels: itens.map((item) => item.nome),
      datasets: [{ data: itens.map((item) => item.total) }],
    };
  });

  protected readonly dadosLinha = computed<ChartData>(() => {
    const dias = this.resumo()?.gasto_acumulado_diario ?? [];
    return {
      labels: dias.map((dia) => String(dia.dia)),
      datasets: [{ label: 'Gasto acumulado', data: dias.map((dia) => dia.total) }],
    };
  });

  /** Descrição do gráfico de linha para leitor de tela (F-10 §3.6). */
  protected readonly rotuloDaLinha = computed(() => {
    const resumo = this.resumo();
    if (!resumo) {
      return '';
    }
    const final = resumo.gasto_acumulado_diario.at(-1)?.total ?? 0;
    return (
      `Gráfico de linha do gasto acumulado dia a dia em ${mesPorExtenso(resumo.mes)}: ` +
      `${formatarMontante(final)} no fim do mês.`
    );
  });

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
