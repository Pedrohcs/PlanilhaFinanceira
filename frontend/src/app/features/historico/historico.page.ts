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
import { ActivatedRoute, Router } from '@angular/router';
import { ChartData, ChartOptions, TooltipItem } from 'chart.js';
import { firstValueFrom } from 'rxjs';
import { ResumoApi } from '../../core/api/resumo.api';
import { PeriodoHistorico, ResumoHistorico } from '../../core/models/resumo';
import { DadosStore } from '../../core/state/dados.store';
import { mesAbreviado, mesPorExtenso } from '../../core/utils/mes';
import { formatarMontante } from '../../core/utils/valor';
import { Carregando } from '../../shared/components/carregando/carregando';
import { EstadoVazio } from '../../shared/components/estado-vazio/estado-vazio';
import { CoresDoTema, DadosDoGrafico } from '../../shared/grafico/grafico.config';
import { GraficoDirective } from '../../shared/grafico/grafico.directive';
import { lerPeriodo } from './periodo';
import { SeletorIntervalo } from './seletor-intervalo';

/** Mesmo período, por valor (a URL ser corrigida não refaz a busca). */
function mesmoPeriodo(a: PeriodoHistorico | null, b: PeriodoHistorico | null): boolean {
  return a?.inicio === b?.inicio && a?.fim === b?.fim;
}

/**
 * Histórico (REQ-14; F-11 §3.2): período na URL (`?inicio=&fim=`), total e
 * média do período, gastos × receitas com a linha do saldo, gastos por
 * categoria empilhados e a tabela mês a mês — tudo pronto da API; o frontend
 * não soma nem divide (`03` §4.2). Recarrega quando o período ou `versao`
 * mudam (CA-14.2, CA-01.5).
 */
@Component({
  selector: 'app-historico-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SeletorIntervalo, Carregando, EstadoVazio, GraficoDirective],
  templateUrl: './historico.page.html',
  styleUrl: './historico.page.scss',
})
export class HistoricoPage {
  private readonly api = inject(ResumoApi);
  private readonly rota = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly dados = inject(DadosStore);

  private readonly parametros = toSignal(this.rota.queryParams, { initialValue: {} });
  private readonly leitura = computed(() => lerPeriodo(this.parametros()));
  /** Período pedido pela URL; `null` = padrão da API (12 meses até o corrente). */
  private readonly pedido = computed(() => this.leitura().periodo, { equal: mesmoPeriodo });

  protected readonly historico = signal<ResumoHistorico | null>(null);
  protected readonly carregando = signal(false);
  protected readonly erro = signal(false);
  private sequencia = 0;

  /** O da URL ou, sem ela, o que a API escolheu (o padrão fica só no backend). */
  protected readonly periodo = computed<PeriodoHistorico | null>(() => {
    const historico = this.historico();
    return this.pedido() ?? (historico && { inicio: historico.inicio, fim: historico.fim });
  });

  protected readonly semLancamentos = computed(() => {
    const historico = this.historico();
    return (
      !!historico &&
      historico.por_categoria.length === 0 &&
      historico.meses.every((mes) => mes.total_receitas === 0)
    );
  });

  /** "De outubro de 2025 a setembro de 2026" — período da resposta exibida. */
  protected readonly periodoPorExtenso = computed(() => {
    const historico = this.historico();
    return historico
      ? `de ${mesPorExtenso(historico.inicio)} a ${mesPorExtenso(historico.fim)}`
      : '';
  });

  protected readonly legendaDoPeriodo = computed(() => {
    const quantidade = this.historico()?.meses.length ?? 0;
    const meses = quantidade === 1 ? '1 mês' : `${quantidade} meses`;
    const extenso = this.periodoPorExtenso();
    return `${extenso.charAt(0).toUpperCase()}${extenso.slice(1)} (${meses}).`;
  });

  private readonly rotulos = computed(() =>
    (this.historico()?.meses ?? []).map((item) => mesAbreviado(item.mes)),
  );

  /**
   * Barras Gastos e Receitas com as cores do tema e a linha do Saldo (cor de
   * destaque dos padrões). Função das cores: a diretiva a refaz na troca de
   * tema (F-11 §3.2.4).
   */
  protected readonly dadosMesAMes = computed<DadosDoGrafico>(() => {
    const meses = this.historico()?.meses ?? [];
    const labels = this.rotulos();
    return (cores: CoresDoTema): ChartData => ({
      labels,
      datasets: [
        {
          type: 'bar',
          label: 'Gastos',
          data: meses.map((item) => item.total_gastos),
          backgroundColor: cores.gasto,
          order: 1,
        },
        {
          type: 'bar',
          label: 'Receitas',
          data: meses.map((item) => item.total_receitas),
          backgroundColor: cores.receita,
          order: 1,
        },
        // `order` menor: a linha é desenhada por cima das barras.
        { type: 'line', label: 'Saldo', data: meses.map((item) => item.saldo), order: 0 },
      ],
    });
  });

  /** Um conjunto por categoria, na cor dela (CA-13.1), na ordem da API. */
  protected readonly dadosPorCategoria = computed<ChartData>(() => ({
    labels: this.rotulos(),
    datasets: (this.historico()?.por_categoria ?? []).map((item) => ({
      label: item.nome,
      data: item.valores,
      backgroundColor: item.cor,
    })),
  }));

  /** Tooltip com o mês por extenso no título ("outubro de 2025"). */
  private readonly tituloDoTooltip = computed(() => {
    const meses = this.historico()?.meses ?? [];
    return (itens: TooltipItem<'bar'>[]) => {
      const mes = meses[itens[0]?.dataIndex ?? -1]?.mes;
      return mes ? mesPorExtenso(mes) : '';
    };
  });

  protected readonly opcoesMesAMes = computed<ChartOptions>(
    () =>
      ({
        responsive: true,
        maintainAspectRatio: false,
        plugins: { tooltip: { callbacks: { title: this.tituloDoTooltip() } } },
      }) as ChartOptions,
  );

  protected readonly opcoesPorCategoria = computed<ChartOptions>(
    () =>
      ({
        responsive: true,
        maintainAspectRatio: false,
        scales: { x: { stacked: true }, y: { stacked: true } },
        plugins: { tooltip: { callbacks: { title: this.tituloDoTooltip() } } },
      }) as ChartOptions,
  );

  constructor() {
    // Período inválido na URL: limpa sem nova entrada no histórico e vale o padrão (§3.2.2).
    effect(() => {
      if (this.leitura().descartar) {
        untracked(() => this.navegar(null));
      }
    });

    effect(() => {
      const periodo = this.pedido();
      this.dados.versao();
      untracked(() => void this.carregar(periodo));
    });
  }

  protected escolher(periodo: PeriodoHistorico): void {
    this.navegar(periodo);
  }

  protected ultimos12(): void {
    this.navegar(null);
  }

  protected montante(valor: number): string {
    return formatarMontante(valor);
  }

  protected mesPorExtenso(mes: string): string {
    return mesPorExtenso(mes);
  }

  /** Período na URL (`null` tira os dois parâmetros), sem empilhar histórico. */
  private navegar(periodo: PeriodoHistorico | null): void {
    void this.router.navigate([], {
      relativeTo: this.rota,
      queryParams: { inicio: periodo?.inicio ?? null, fim: periodo?.fim ?? null },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
  }

  /** Uma busca por vez vale: resposta de busca anterior é descartada (F-07 borda 15). */
  private async carregar(periodo: PeriodoHistorico | null): Promise<void> {
    const minha = ++this.sequencia;
    this.carregando.set(true);
    try {
      const historico = await firstValueFrom(this.api.historico(periodo ?? undefined));
      if (minha === this.sequencia) {
        this.historico.set(historico);
        this.erro.set(false);
      }
    } catch {
      if (minha === this.sequencia) {
        this.historico.set(null);
        this.erro.set(true); // a causa já foi mostrada pelo interceptor/banner
      }
    } finally {
      if (minha === this.sequencia) {
        this.carregando.set(false);
      }
    }
  }
}
