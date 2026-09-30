import { DOCUMENT } from '@angular/common';
import { inject, InjectionToken } from '@angular/core';
import {
  ArcElement,
  BarController,
  BarElement,
  CategoryScale,
  Chart,
  ChartConfiguration,
  ChartData,
  ChartOptions,
  DoughnutController,
  Legend,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
  TooltipItem,
} from 'chart.js';

/**
 * Configuração do Chart.js usada pela `GraficoDirective` (SPECS/02 §4, ADR-11).
 *
 * Registra só o que o app desenha — rosca, barra e linha — para o bundle não
 * carregar o Chart.js inteiro (nada de `registerables`).
 */
Chart.register(
  DoughnutController,
  BarController,
  LineController,
  ArcElement,
  BarElement,
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
);

export type TipoGrafico = 'doughnut' | 'bar' | 'line';
export type EixoIndice = 'x' | 'y';

/** Cores de texto e de grade do tema atual, já resolvidas (ex.: `rgb(27, 27, 31)`). */
export interface CoresDoTema {
  texto: string;
  grade: string;
}

/** O que a diretiva usa de um `Chart` — permite trocar por um dublê nos testes. */
export interface GraficoCriado {
  data: ChartData;
  options: ChartOptions;
  update(): void;
  destroy(): void;
}

export type FabricaGrafico = (
  canvas: HTMLCanvasElement,
  config: ChartConfiguration,
) => GraficoCriado;

/**
 * Cria o gráfico. O padrão é o próprio Chart.js; os testes trocam por um dublê,
 * porque o jsdom não tem `<canvas>` funcional (F-04 §10).
 */
export const FABRICA_GRAFICO = new InjectionToken<FabricaGrafico>('FABRICA_GRAFICO', {
  providedIn: 'root',
  factory: () => (canvas, config) => new Chart(canvas, config) as unknown as GraficoCriado,
});

/** Lê as cores do tema Material na hora (F-04 Q6). Trocável nos testes. */
export const CORES_DO_TEMA = new InjectionToken<() => CoresDoTema>('CORES_DO_TEMA', {
  providedIn: 'root',
  factory: () => {
    const documento = inject(DOCUMENT);
    return () => lerCoresDoTema(documento);
  },
});

const REAIS = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

/** `1234.56` → `R$ 1.234,56` (RNF-03). Só formata: os totais vêm prontos do backend. */
export function formatarReais(valor: number): string {
  return REAIS.format(valor);
}

/**
 * Cores do tema em uso, resolvidas pelo navegador.
 *
 * Com `color-scheme: light dark`, o Material define as variáveis como
 * `light-dark(claro, escuro)`, que o Chart.js não entende. Aplicar a variável
 * como `color` de um elemento e ler a cor computada devolve o `rgb(...)` do
 * tema atual.
 */
export function lerCoresDoTema(documento: Document): CoresDoTema {
  const sonda = documento.createElement('span');
  sonda.style.display = 'none';
  documento.body.appendChild(sonda);
  const ler = (variavel: string, reserva: string): string => {
    sonda.style.color = `var(${variavel}, ${reserva})`;
    return documento.defaultView?.getComputedStyle(sonda).color || reserva;
  };
  try {
    return {
      texto: ler('--mat-sys-on-surface', '#1b1b1f'),
      grade: ler('--mat-sys-outline-variant', '#c4c6d0'),
    };
  } finally {
    sonda.remove();
  }
}

/**
 * Opções padrão pt-BR: locale, cores do tema e valores em reais no tooltip e
 * no eixo de valores. A rosca não tem eixos; em barra e linha, o eixo de
 * valores é o oposto de `eixoIndice` (barras horizontais usam `'y'`).
 */
export function opcoesPadrao(
  tipo: TipoGrafico,
  cores: CoresDoTema,
  eixoIndice: EixoIndice = 'x',
): ChartOptions {
  const opcoes: ChartOptions = {
    locale: 'pt-BR',
    color: cores.texto,
    plugins: {
      legend: { labels: { color: cores.texto } },
      tooltip: { callbacks: { label: rotuloEmReais } },
    },
  };
  if (tipo === 'doughnut') {
    return opcoes;
  }
  const eixoValores: EixoIndice = eixoIndice === 'x' ? 'y' : 'x';
  const eixo = (deValores: boolean) => ({
    grid: { color: cores.grade },
    ticks: {
      color: cores.texto,
      ...(deValores ? { callback: (valor: string | number) => formatarReais(Number(valor)) } : {}),
    },
  });
  return {
    ...opcoes,
    scales: {
      [eixoIndice]: eixo(false),
      [eixoValores]: eixo(true),
    },
  } as ChartOptions;
}

/** Tooltip: `Alimentação: R$ 1.234,56` na rosca; `Gastos: R$ …` em barra e linha. */
function rotuloEmReais(item: TooltipItem<TipoGrafico>): string {
  if (typeof item.parsed === 'number') {
    return `${item.label}: ${formatarReais(item.parsed)}`;
  }
  const ponto = item.parsed as { x: number; y: number };
  const horizontal = (item.chart.options as { indexAxis?: EixoIndice }).indexAxis === 'y';
  const nome = item.dataset.label || item.label;
  return `${nome}: ${formatarReais(horizontal ? ponto.x : ponto.y)}`;
}
