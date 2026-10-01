import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ChartConfiguration, ChartData, ChartOptions } from 'chart.js';
import {
  CORES_DO_TEMA,
  CoresDoTema,
  DadosDoGrafico,
  FABRICA_GRAFICO,
  GraficoCriado,
  TipoGrafico,
} from './grafico.config';
import { GraficoDirective } from './grafico.directive';

/** Dublê de `Chart`: o jsdom não tem `<canvas>` funcional (F-04 §10). */
class GraficoFalso implements GraficoCriado {
  data: ChartData;
  options: ChartOptions;
  readonly update = vi.fn();
  readonly destroy = vi.fn();

  constructor(
    readonly canvas: HTMLCanvasElement,
    readonly config: ChartConfiguration,
  ) {
    this.data = config.data;
    this.options = config.options ?? {};
  }
}

/** `MediaQueryList` falso, para simular a troca de tema do sistema. */
class ConsultaDeTemaFalsa {
  readonly ouvintes = new Set<() => void>();
  addEventListener(_evento: string, ouvinte: () => void): void {
    this.ouvintes.add(ouvinte);
  }
  removeEventListener(_evento: string, ouvinte: () => void): void {
    this.ouvintes.delete(ouvinte);
  }
  trocar(): void {
    this.ouvintes.forEach((ouvinte) => ouvinte());
  }
}

@Component({
  imports: [GraficoDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (visivel()) {
      <canvas appGrafico [tipo]="tipo()" [dados]="dados()" [opcoes]="opcoes()"></canvas>
    }
  `,
})
class Hospedeiro {
  readonly visivel = signal(true);
  readonly tipo = signal<TipoGrafico>('bar');
  readonly dados = signal<DadosDoGrafico>({ labels: ['Pix'], datasets: [{ data: [10] }] });
  readonly opcoes = signal<ChartOptions | undefined>(undefined);
}

describe('GraficoDirective', () => {
  let criados: GraficoFalso[];
  let cores: CoresDoTema;
  let consulta: ConsultaDeTemaFalsa;
  let matchMediaOriginal: PropertyDescriptor | undefined;
  let fixture: ComponentFixture<Hospedeiro>;

  beforeEach(() => {
    criados = [];
    cores = {
      texto: 'rgb(0, 0, 0)',
      grade: 'rgb(200, 200, 200)',
      destaque: 'rgb(0, 0, 255)',
      gasto: 'rgb(255, 0, 0)',
      receita: 'rgb(0, 128, 0)',
    };
    consulta = new ConsultaDeTemaFalsa();
    matchMediaOriginal = Object.getOwnPropertyDescriptor(window, 'matchMedia');
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      value: (media: string) => {
        expect(media).toBe('(prefers-color-scheme: dark)');
        return consulta;
      },
    });

    TestBed.configureTestingModule({
      imports: [Hospedeiro],
      providers: [
        {
          provide: FABRICA_GRAFICO,
          useValue: (canvas: HTMLCanvasElement, config: ChartConfiguration) => {
            const grafico = new GraficoFalso(canvas, config);
            criados.push(grafico);
            return grafico;
          },
        },
        { provide: CORES_DO_TEMA, useValue: () => ({ ...cores }) },
      ],
    });
    fixture = TestBed.createComponent(Hospedeiro);
  });

  afterEach(() => {
    if (matchMediaOriginal) {
      Object.defineProperty(window, 'matchMedia', matchMediaOriginal);
    } else {
      delete (window as { matchMedia?: unknown }).matchMedia;
    }
  });

  it('cria_um_grafico_apos_render__CA_F04_8', async () => {
    expect(criados).toHaveLength(0); // nada antes da 1ª renderização

    await fixture.whenStable();

    expect(criados).toHaveLength(1);
    const [grafico] = criados;
    expect(grafico.canvas).toBe(fixture.nativeElement.querySelector('canvas'));
    expect(grafico.config.type).toBe('bar');
    expect(grafico.config.data).toBe(fixture.componentInstance.dados());
    expect(grafico.config.options?.locale).toBe('pt-BR');

    await fixture.whenStable();
    expect(criados).toHaveLength(1);
  });

  it('atualiza_a_mesma_instancia_e_recria_ao_trocar_tipo__CA_F04_9', async () => {
    await fixture.whenStable();
    const [primeiro] = criados;
    const novosDados: ChartData = { labels: ['Pix', 'Boleto'], datasets: [{ data: [10, 20] }] };

    fixture.componentInstance.dados.set(novosDados);
    await fixture.whenStable();

    expect(criados).toHaveLength(1);
    expect(primeiro.data).toBe(novosDados);
    expect(primeiro.update).toHaveBeenCalledTimes(1);

    fixture.componentInstance.opcoes.set({ plugins: { legend: { display: false } } });
    await fixture.whenStable();

    expect(criados).toHaveLength(1);
    expect(primeiro.options.plugins?.legend?.display).toBe(false);
    expect(primeiro.update).toHaveBeenCalledTimes(2);

    fixture.componentInstance.tipo.set('line');
    await fixture.whenStable();

    expect(primeiro.destroy).toHaveBeenCalledTimes(1);
    expect(criados).toHaveLength(2);
    expect(criados[1].config.type).toBe('line');
    expect(criados[1].config.data).toBe(novosDados);
  });

  it('destroi_ao_sair_e_nao_cria_se_destruido_antes__CA_F04_10', async () => {
    await fixture.whenStable();
    const [grafico] = criados;

    fixture.componentInstance.visivel.set(false);
    await fixture.whenStable();

    expect(grafico.destroy).toHaveBeenCalledTimes(1);
    expect(consulta.ouvintes.size).toBe(0);

    // Destruído antes da 1ª renderização (navegação rápida): nenhum gráfico.
    const outro = TestBed.createComponent(Hospedeiro);
    outro.destroy();
    await fixture.whenStable();
    TestBed.tick();
    expect(criados).toHaveLength(1);
  });

  it('acompanha_troca_de_tema__CA_F04_30', async () => {
    await fixture.whenStable();
    const [grafico] = criados;
    expect(grafico.options.color).toBe('rgb(0, 0, 0)');

    cores = {
      texto: 'rgb(230, 230, 230)',
      grade: 'rgb(60, 60, 60)',
      destaque: 'rgb(170, 199, 255)',
      gasto: 'rgb(255, 180, 171)',
      receita: 'rgb(129, 199, 132)',
    };
    consulta.trocar();

    expect(criados).toHaveLength(1); // mesma instância
    expect(grafico.update).toHaveBeenCalledTimes(1);
    expect(grafico.options.color).toBe('rgb(230, 230, 230)');
    const escalas = grafico.options.scales as Record<string, { grid: { color: string } }>;
    expect(escalas['x'].grid.color).toBe('rgb(60, 60, 60)');
    expect(grafico.options.elements?.bar?.backgroundColor).toBe('rgb(170, 199, 255)'); // F-10
  });

  it('dados_em_funcao_das_cores_do_tema__F11', async () => {
    const montar = (tema: CoresDoTema): ChartData => ({
      labels: ['out/25'],
      datasets: [
        { label: 'Gastos', data: [10], backgroundColor: tema.gasto },
        { label: 'Receitas', data: [20], backgroundColor: tema.receita },
      ],
    });
    fixture.componentInstance.dados.set(montar);
    await fixture.whenStable();
    const [grafico] = criados;
    const cor = (indice: number) => grafico.data.datasets[indice].backgroundColor;
    expect(cor(0)).toBe('rgb(255, 0, 0)');
    expect(cor(1)).toBe('rgb(0, 128, 0)');

    cores = { ...cores, gasto: 'rgb(255, 180, 171)', receita: 'rgb(129, 199, 132)' };
    consulta.trocar();

    expect(criados).toHaveLength(1); // mesma instância, dados refeitos com as cores novas
    expect(grafico.update).toHaveBeenCalledTimes(1);
    expect(cor(0)).toBe('rgb(255, 180, 171)');
    expect(cor(1)).toBe('rgb(129, 199, 132)');
  });

  it('opcoes_da_pagina_sobrepoem_os_padroes', async () => {
    fixture.componentInstance.opcoes.set({
      indexAxis: 'y',
      plugins: { legend: { position: 'bottom' } },
    });
    await fixture.whenStable();

    const opcoes = criados[0].config.options as ChartOptions<'bar'>;
    expect(opcoes.indexAxis).toBe('y');
    expect(opcoes.plugins?.legend?.position).toBe('bottom');
    expect(opcoes.plugins?.legend?.labels?.color).toBe('rgb(0, 0, 0)'); // padrão mantido
    expect(opcoes.plugins?.tooltip?.callbacks?.label).toBeTypeOf('function');
    const escalas = opcoes.scales as Record<string, { ticks: { callback?: unknown } }>;
    expect(escalas['x'].ticks.callback).toBeTypeOf('function'); // eixo de valores horizontal
    expect(escalas['y'].ticks.callback).toBeUndefined();
  });
});
