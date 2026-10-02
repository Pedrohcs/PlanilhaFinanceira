import { provideHttpClient, withInterceptors } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
  TestRequest,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { DateAdapter, MAT_DATE_LOCALE, provideNativeDateAdapter } from '@angular/material/core';
import { MatDatepicker } from '@angular/material/datepicker';
import { By } from '@angular/platform-browser';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { ChartConfiguration, ChartData, ChartOptions, TooltipItem } from 'chart.js';
import { provideMaterialParaTestes } from '../../../testing/material';
import { routes } from '../../app.routes';
import { Avisos } from '../../core/avisos/avisos';
import { erroInterceptor } from '../../core/interceptors/erro.interceptor';
import { ResumoHistorico } from '../../core/models/resumo';
import { DadosStore } from '../../core/state/dados.store';
import { AdaptadorDeDataPtBr } from '../../core/utils/adaptador-de-data';
import { CORES_DO_TEMA, FABRICA_GRAFICO, GraficoCriado } from '../../shared/grafico/grafico.config';

const URL = '/api/resumo/historico';
const DESTAQUE = 'rgb(65, 95, 145)';
const GASTO = 'rgb(186, 26, 26)';
const RECEITA = 'rgb(46, 125, 50)';

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

/** Exemplo de F-11 §6 (julho a setembro de 2026). */
function historico(parcial: Partial<ResumoHistorico> = {}): ResumoHistorico {
  return {
    inicio: '2026-07',
    fim: '2026-09',
    meses: [
      { mes: '2026-07', total_gastos: 0, total_receitas: 0, saldo: 0 },
      { mes: '2026-08', total_gastos: 1200, total_receitas: 5000, saldo: 3800 },
      { mes: '2026-09', total_gastos: 1500, total_receitas: 1000, saldo: -500 },
    ],
    por_categoria: [
      { categoria_id: 'moradia', nome: 'Moradia', cor: '#4FC3F7', valores: [0, 1000, 1000] },
      { categoria_id: 'alimentacao', nome: 'Alimentação', cor: '#E57373', valores: [0, 200, 500] },
    ],
    // Números que não batem com os meses: prova que os cards são os da API.
    total_gastos_periodo: 2700,
    media_mensal_gastos: 900,
    linhas_ignoradas: 0,
    ...parcial,
  };
}

const VAZIO: Partial<ResumoHistorico> = {
  meses: [
    { mes: '2026-07', total_gastos: 0, total_receitas: 0, saldo: 0 },
    { mes: '2026-08', total_gastos: 0, total_receitas: 0, saldo: 0 },
    { mes: '2026-09', total_gastos: 0, total_receitas: 0, saldo: 0 },
  ],
  por_categoria: [],
  total_gastos_periodo: 0,
  media_mensal_gastos: 0,
};

describe('HistoricoPage', () => {
  let harness: RouterTestingHarness;
  let controle: HttpTestingController;
  let graficos: GraficoFalso[];

  beforeEach(async () => {
    graficos = [];
    TestBed.configureTestingModule({
      providers: [
        provideRouter(routes),
        provideHttpClient(withInterceptors([erroInterceptor])),
        provideHttpClientTesting(),
        provideMaterialParaTestes(),
        provideNativeDateAdapter(),
        { provide: DateAdapter, useClass: AdaptadorDeDataPtBr },
        { provide: MAT_DATE_LOCALE, useValue: 'pt-BR' },
        { provide: Avisos, useValue: { mostrar: vi.fn() } },
        {
          provide: FABRICA_GRAFICO,
          useValue: (canvas: HTMLCanvasElement, config: ChartConfiguration) => {
            const grafico = new GraficoFalso(canvas, config);
            graficos.push(grafico);
            return grafico;
          },
        },
        {
          provide: CORES_DO_TEMA,
          useValue: () => ({
            texto: 'rgb(0, 0, 0)',
            grade: 'rgb(1, 1, 1)',
            destaque: DESTAQUE,
            gasto: GASTO,
            receita: RECEITA,
          }),
        },
      ],
    });
    controle = TestBed.inject(HttpTestingController);
    harness = await RouterTestingHarness.create();
  });

  afterEach(() => controle.verify());

  async function estabilizar(): Promise<void> {
    for (let i = 0; i < 3; i++) {
      await new Promise((resolver) => setTimeout(resolver));
      await harness.fixture.whenStable();
    }
  }

  function pedidos(): TestRequest[] {
    return controle.match((requisicao) => requisicao.url === URL);
  }

  /** Responde a (única) busca pendente e devolve o período pedido (`''` = padrão). */
  async function responder(resposta: ResumoHistorico): Promise<string> {
    const pendentes = pedidos();
    expect(pendentes).toHaveLength(1);
    const params = pendentes[0].request.params;
    const pedido = params.has('inicio') ? `${params.get('inicio')}..${params.get('fim')}` : '';
    pendentes[0].flush(resposta);
    await estabilizar();
    return pedido;
  }

  async function abrir(resposta: ResumoHistorico = historico()): Promise<void> {
    await harness.navigateByUrl('/historico?inicio=2026-07&fim=2026-09');
    await estabilizar();
    expect(await responder(resposta)).toBe('2026-07..2026-09');
  }

  function pagina(): HTMLElement {
    return harness.routeNativeElement!;
  }

  function texto(el: Element | null | undefined): string {
    return (el?.textContent ?? '').replace(/ /g, ' ').replace(/\s+/g, ' ').trim();
  }

  function url(): string {
    return TestBed.inject(Router).url;
  }

  function cards(): string[] {
    return Array.from(pagina().querySelectorAll('.total .numero')).map(texto);
  }

  function seletores(): string[] {
    return ['.inicio', '.fim'].map((classe) =>
      texto(pagina().querySelector(`app-seletor-intervalo ${classe}`)),
    );
  }

  function graficoEm(secao: string): GraficoFalso {
    const encontrados = graficos.filter((item) =>
      pagina().querySelector(`.${secao}`)?.contains(item.canvas),
    );
    expect(encontrados).toHaveLength(1);
    return encontrados[0];
  }

  function tituloDoTooltip(
    grafico: GraficoFalso,
  ): (itens: Partial<TooltipItem<'bar'>>[]) => string {
    return grafico.options.plugins?.tooltip?.callbacks?.title as unknown as (
      itens: Partial<TooltipItem<'bar'>>[],
    ) => string;
  }

  /** Escolhe um mês no datepicker "De" (0) ou "Até" (1), como o usuário. */
  async function escolher(ponta: 0 | 1, data: Date): Promise<void> {
    harness.fixture.debugElement
      .queryAll(By.directive(MatDatepicker))
      [ponta].triggerEventHandler('monthSelected', data);
    await estabilizar();
  }

  it('periodo_da_url_ou_padrao__CA_F11_11', async () => {
    await harness.navigateByUrl('/historico');
    await estabilizar();
    expect(pagina().querySelector('app-seletor-intervalo')).toBeNull(); // período ainda desconhecido
    expect(await responder(historico({ inicio: '2025-11', fim: '2026-10' }))).toBe('');

    expect(texto(pagina().querySelector('h1'))).toBe('Histórico');
    expect(seletores()).toEqual(['novembro de 2025', 'outubro de 2026']);
    expect(url()).toBe('/historico'); // o padrão não vai para a URL

    await harness.navigateByUrl('/historico?inicio=2026-01&fim=2026-06');
    await estabilizar();
    expect(await responder(historico({ inicio: '2026-01', fim: '2026-06' }))).toBe(
      '2026-01..2026-06',
    );
    expect(seletores()).toEqual(['janeiro de 2026', 'junho de 2026']);
  });

  it.each([
    '/historico?inicio=2026-09&fim=2026-01',
    '/historico?inicio=2026-01',
    '/historico?inicio=2024-01&fim=2027-01',
    '/historico?inicio=2026-13&fim=2026-12',
  ])('url_invalida_descartada__CA_F11_12 %s', async (endereco) => {
    await harness.navigateByUrl(endereco);
    await estabilizar();

    expect(url()).toBe('/historico'); // limpa, com replaceUrl
    expect(await responder(historico({ inicio: '2025-11', fim: '2026-10' }))).toBe('');
  });

  it('troca_de_intervalo_recarrega__CA_14_2', async () => {
    await abrir();

    // "De" depois do "Até": o "Até" vem junto (CA-F11.13).
    await escolher(0, new Date(2026, 9, 1));
    expect(url()).toBe('/historico?inicio=2026-10&fim=2026-10');
    expect(pagina().querySelector('.conteudo.recarregando')).not.toBeNull(); // esmaecido
    expect(
      await responder(historico({ inicio: '2026-10', fim: '2026-10', total_gastos_periodo: 10 })),
    ).toBe('2026-10..2026-10');
    expect(cards()[0]).toBe('R$ 10,00');

    // "Até" a 37 meses do "De": o "De" encosta no limite de 36 (Q2).
    await escolher(1, new Date(2029, 10, 1));
    expect(url()).toBe('/historico?inicio=2026-12&fim=2029-11');
    expect(await responder(historico({ inicio: '2026-12', fim: '2029-11' }))).toBe(
      '2026-12..2029-11',
    );

    // "Últimos 12 meses": volta ao padrão da API.
    pagina().querySelector<HTMLButtonElement>('app-seletor-intervalo .padrao')!.click();
    await estabilizar();
    expect(url()).toBe('/historico');
    expect(await responder(historico({ inicio: '2025-11', fim: '2026-10' }))).toBe('');
    expect(seletores()).toEqual(['novembro de 2025', 'outubro de 2026']);
  });

  it('total_e_media_da_api__CA_14_3', async () => {
    await abrir();

    expect(Array.from(pagina().querySelectorAll('.total .rotulo')).map(texto)).toEqual([
      'Total gasto no período',
      'Média mensal de gastos',
    ]);
    expect(cards()).toEqual(['R$ 2.700,00', 'R$ 900,00']);
    expect(texto(pagina().querySelector('.legenda'))).toBe(
      'De julho de 2026 a setembro de 2026 (3 meses).',
    );
  });

  it('grafico_gastos_receitas_saldo__CA_14_1', async () => {
    await abrir();

    const grafico = graficoEm('mes-a-mes');
    expect(grafico.config.type).toBe('bar');
    expect(grafico.data.labels).toEqual(['jul/26', 'ago/26', 'set/26']); // inclusive o mês zerado
    const [gastos, receitas, saldo] = grafico.data.datasets;
    expect([gastos.label, gastos.data, gastos.backgroundColor]).toEqual([
      'Gastos',
      [0, 1200, 1500],
      GASTO,
    ]);
    expect([receitas.label, receitas.data, receitas.backgroundColor]).toEqual([
      'Receitas',
      [0, 5000, 1000],
      RECEITA,
    ]);
    expect([saldo.type, saldo.label, saldo.data]).toEqual(['line', 'Saldo', [0, 3800, -500]]);
    expect(grafico.options.elements?.line?.borderColor).toBe(DESTAQUE); // saldo: destaque
    expect(grafico.options.plugins?.legend?.display).not.toBe(false); // legenda visível
    expect(tituloDoTooltip(grafico)([{ dataIndex: 1 }])).toBe('agosto de 2026');
    expect(texto(pagina().querySelector('.mes-a-mes h2'))).toBe('Gastos e receitas por mês');
  });

  it('barras_empilhadas_por_categoria__CA_F11_16', async () => {
    await abrir();

    const grafico = graficoEm('por-categoria');
    expect(grafico.data.labels).toEqual(['jul/26', 'ago/26', 'set/26']);
    expect(
      grafico.data.datasets.map((item) => [item.label, item.data, item.backgroundColor]),
    ).toEqual([
      ['Moradia', [0, 1000, 1000], '#4FC3F7'],
      ['Alimentação', [0, 200, 500], '#E57373'],
    ]);
    const escalas = grafico.options.scales as Record<string, { stacked?: boolean }>;
    expect([escalas['x'].stacked, escalas['y'].stacked]).toEqual([true, true]);
    expect(grafico.options.plugins?.legend?.display).not.toBe(false);
    expect(tituloDoTooltip(grafico)([{ dataIndex: 2 }])).toBe('setembro de 2026');
    expect(texto(pagina().querySelector('.por-categoria h2'))).toBe(
      'Gastos por categoria ao longo dos meses',
    );
  });

  it('tabela_mes_a_mes__CA_F11_17', async () => {
    await abrir();

    const linhas = Array.from(pagina().querySelectorAll('.tabela-meses tbody tr'));
    expect(linhas.map((linha) => Array.from(linha.querySelectorAll('td')).map(texto))).toEqual([
      ['julho de 2026', 'R$ 0,00', 'R$ 0,00', 'R$ 0,00'],
      ['agosto de 2026', 'R$ 1.200,00', 'R$ 5.000,00', 'R$ 3.800,00'],
      ['setembro de 2026', 'R$ 1.500,00', 'R$ 1.000,00', '− R$ 500,00'],
    ]);
    const saldos = linhas.map((linha) => linha.querySelector('.saldo')!);
    expect(saldos.map((saldo) => saldo.classList.contains('negativo'))).toEqual([
      false,
      false,
      true,
    ]);
    const cabecalho = Array.from(pagina().querySelectorAll('.tabela-meses th'));
    expect(cabecalho.map(texto)).toEqual(['Mês', 'Gastos', 'Receitas', 'Saldo']);
    expect(cabecalho.every((th) => th.getAttribute('scope') === 'col')).toBe(true);
  });

  it('vazio_e_so_receitas__CA_F11_18', async () => {
    await abrir(historico(VAZIO));

    expect(cards()).toEqual(['R$ 0,00', 'R$ 0,00']);
    expect(texto(pagina().querySelector('app-estado-vazio'))).toContain(
      'Nenhum lançamento de julho de 2026 a setembro de 2026.',
    );
    expect(pagina().querySelector('canvas')).toBeNull();
    expect(pagina().querySelector('table')).toBeNull();
    expect(graficos).toHaveLength(0);

    TestBed.inject(DadosStore).incrementar();
    await estabilizar();
    const soReceitas = VAZIO.meses!.map((mes, i) =>
      i === 1 ? { ...mes, total_receitas: 5000, saldo: 5000 } : mes,
    );
    await responder(historico({ ...VAZIO, meses: soReceitas }));

    expect(texto(pagina().querySelector('.por-categoria app-estado-vazio'))).toContain(
      'Nenhum gasto no período.',
    );
    expect(pagina().querySelector('.por-categoria canvas')).toBeNull();
    expect(graficoEm('mes-a-mes').data.datasets[1].data).toEqual([0, 5000, 0]);
    expect(pagina().querySelector('.tabela-meses')).not.toBeNull();
  });

  it('recarrega_por_versao__CA_F11_19', async () => {
    await abrir();
    expect(graficos).toHaveLength(2);

    // Borda 18: registro pela barra com o histórico aberto — mesmo período.
    TestBed.inject(DadosStore).incrementar();
    await estabilizar();
    expect(await responder(historico({ total_gastos_periodo: 2800 }))).toBe('2026-07..2026-09');
    expect(cards()[0]).toBe('R$ 2.800,00');
    expect(graficos).toHaveLength(2); // os mesmos gráficos, atualizados
    expect(graficoEm('mes-a-mes').update).toHaveBeenCalled();

    // Borda 17: a resposta do 1º período chega depois da do 2º e é descartada.
    await harness.navigateByUrl('/historico?inicio=2026-01&fim=2026-03');
    await estabilizar();
    await harness.navigateByUrl('/historico?inicio=2026-04&fim=2026-06');
    await estabilizar();
    const [primeiro, segundo] = pedidos();
    expect(primeiro.request.params.get('inicio')).toBe('2026-01');
    expect(segundo.request.params.get('inicio')).toBe('2026-04');
    segundo.flush(historico({ inicio: '2026-04', fim: '2026-06', total_gastos_periodo: 46 }));
    primeiro.flush(historico({ inicio: '2026-01', fim: '2026-03', total_gastos_periodo: 13 }));
    await estabilizar();

    expect(cards()[0]).toBe('R$ 46,00');
  });

  it('erro_de_carga__CA_F11_20', async () => {
    await abrir();

    TestBed.inject(DadosStore).incrementar();
    await estabilizar();
    pedidos()[0].flush(
      { erro: { codigo: 'PLANILHA_INDISPONIVEL', mensagem: 'Indisponível.', detalhes: [] } },
      { status: 503, statusText: 'x' },
    );
    await estabilizar();

    expect(texto(pagina())).toContain('Não foi possível carregar o histórico.');
    expect(pagina().querySelector('.totais')).toBeNull();
    expect(pagina().querySelector('canvas')).toBeNull();
  });

  it('graficos_acessiveis__CA_F11_21', async () => {
    await abrir();

    const canvases = Array.from(pagina().querySelectorAll('canvas'));
    expect(canvases.map((canvas) => canvas.getAttribute('role'))).toEqual(['img', 'img']);
    expect(canvases.map((canvas) => canvas.getAttribute('aria-label'))).toEqual([
      'Gráfico de barras dos gastos e receitas por mês, com a linha do saldo, de julho de 2026 a setembro de 2026. Os valores estão na tabela abaixo.',
      'Gráfico de barras empilhadas dos gastos por categoria em cada mês, de julho de 2026 a setembro de 2026.',
    ]);
    const rotulos = Array.from(
      pagina().querySelectorAll('app-seletor-intervalo button[aria-label]'),
    ).map((botao) => botao.getAttribute('aria-label'));
    expect(rotulos).toEqual([
      'Mês inicial do período: julho de 2026',
      'Mês final do período: setembro de 2026',
    ]);
  });

  function faixa(): string | null {
    const aviso = pagina().querySelector('header + app-aviso-linhas-ignoradas [role="status"] p');
    return aviso ? aviso.textContent!.replace(/\s+/g, ' ').trim() : null;
  }

  it('mostra_linhas_ignoradas__CA_16_3', async () => {
    await abrir(historico({ linhas_ignoradas: 1 }));
    expect(faixa()).toBe(
      '1 linha da planilha foi ignorada por estar inválida. Corrija-a na planilha e use Recarregar dados.',
    );

    TestBed.inject(DadosStore).incrementar();
    await estabilizar();
    await responder(historico());
    expect(faixa()).toBeNull();
  });
});
