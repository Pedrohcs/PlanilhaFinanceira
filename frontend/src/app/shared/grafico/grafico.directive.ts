import { DOCUMENT } from '@angular/common';
import {
  afterNextRender,
  DestroyRef,
  Directive,
  effect,
  ElementRef,
  inject,
  input,
  untracked,
} from '@angular/core';
import { ChartData, ChartOptions } from 'chart.js';
import { merge } from 'chart.js/helpers';
import {
  CORES_DO_TEMA,
  CoresDoTema,
  DadosDoGrafico,
  FABRICA_GRAFICO,
  GraficoCriado,
  opcoesPadrao,
  TipoGrafico,
} from './grafico.config';

/**
 * Gráfico Chart.js sobre um `<canvas>` (SPECS/02 §4, ADR-11; F-04 §3.2).
 *
 * `<canvas appGrafico [tipo]="'bar'" [dados]="dados()" [opcoes]="opcoes()"></canvas>`
 *
 * - cria o gráfico **uma vez**, depois da primeira renderização;
 * - `dados`/`opcoes` mudaram → atualiza a mesma instância; `tipo` mudou → recria;
 * - acompanha a troca de tema claro/escuro do sistema (F-04 Q6), inclusive
 *   nos `dados` passados como função das cores do tema (F-11 §3.2.4);
 * - destrói o gráfico e o ouvinte do tema junto com a diretiva.
 *
 * As `opcoes` da página são mescladas por cima dos padrões pt-BR.
 */
@Directive({ selector: 'canvas[appGrafico]' })
export class GraficoDirective {
  readonly tipo = input.required<TipoGrafico>();
  readonly dados = input.required<DadosDoGrafico>();
  readonly opcoes = input<ChartOptions>();

  private readonly canvas = inject<ElementRef<HTMLCanvasElement>>(ElementRef);
  private readonly fabrica = inject(FABRICA_GRAFICO);
  private readonly lerCores = inject(CORES_DO_TEMA);
  private grafico: GraficoCriado | null = null;
  private tipoCriado: TipoGrafico | null = null;

  constructor() {
    afterNextRender(() => this.criar());

    effect(() => {
      const tipo = this.tipo();
      const dados = this.dados();
      const opcoes = this.opcoes();
      // Antes da 1ª renderização não há gráfico: quem cria é o `afterNextRender`.
      untracked(() => this.aplicar(tipo, dados, opcoes));
    });

    const temaEscuro = inject(DOCUMENT).defaultView?.matchMedia?.('(prefers-color-scheme: dark)');
    const aoTrocarTema = () => this.atualizarTema();
    temaEscuro?.addEventListener('change', aoTrocarTema);

    inject(DestroyRef).onDestroy(() => {
      temaEscuro?.removeEventListener('change', aoTrocarTema);
      this.grafico?.destroy();
      this.grafico = null;
    });
  }

  private criar(): void {
    const tipo = this.tipo();
    const cores = this.lerCores();
    this.grafico = this.fabrica(this.canvas.nativeElement, {
      type: tipo,
      data: resolverDados(this.dados(), cores),
      options: montarOpcoes(tipo, this.opcoes(), cores),
    });
    this.tipoCriado = tipo;
  }

  private aplicar(
    tipo: TipoGrafico,
    dados: DadosDoGrafico,
    opcoes: ChartOptions | undefined,
  ): void {
    if (!this.grafico) {
      return;
    }
    if (tipo !== this.tipoCriado) {
      this.grafico.destroy();
      this.criar();
      return;
    }
    const cores = this.lerCores();
    this.grafico.data = resolverDados(dados, cores);
    this.grafico.options = montarOpcoes(tipo, opcoes, cores);
    this.grafico.update();
  }

  private atualizarTema(): void {
    if (!this.grafico || !this.tipoCriado) {
      return;
    }
    const cores = this.lerCores();
    const dados = untracked(this.dados);
    if (typeof dados === 'function') {
      this.grafico.data = dados(cores);
    }
    this.grafico.options = montarOpcoes(this.tipoCriado, untracked(this.opcoes), cores);
    this.grafico.update();
  }
}

function resolverDados(dados: DadosDoGrafico, cores: CoresDoTema): ChartData {
  return typeof dados === 'function' ? dados(cores) : dados;
}

function montarOpcoes(
  tipo: TipoGrafico,
  opcoes: ChartOptions | undefined,
  cores: CoresDoTema,
): ChartOptions {
  const padrao = opcoesPadrao(tipo, cores, opcoes?.indexAxis ?? 'x');
  return merge(padrao, opcoes ?? {}) as ChartOptions;
}
