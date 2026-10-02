import { BreakpointObserver } from '@angular/cdk/layout';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
  TestRequest,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { DateAdapter, MAT_DATE_LOCALE, provideNativeDateAdapter } from '@angular/material/core';
import { provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { ChartConfiguration, ChartData, ChartOptions, TooltipItem } from 'chart.js';
import { BreakpointsFalsos } from '../../../testing/breakpoints';
import { provideMaterialParaTestes } from '../../../testing/material';
import { routes } from '../../app.routes';
import { Avisos } from '../../core/avisos/avisos';
import { erroInterceptor } from '../../core/interceptors/erro.interceptor';
import { ResumoMensal } from '../../core/models/resumo';
import { DadosStore } from '../../core/state/dados.store';
import { AdaptadorDeDataPtBr } from '../../core/utils/adaptador-de-data';
import { CORES_DO_TEMA, FABRICA_GRAFICO, GraficoCriado } from '../../shared/grafico/grafico.config';

const URL = '/api/resumo/mensal';
const DESTAQUE = 'rgb(65, 95, 145)';

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

  get tipo(): string {
    return this.config.type;
  }
}

/** Acumulado de `dias` dias; `valores` diz o total a partir de cada dia. */
function acumulado(
  dias: number,
  valores: Record<number, number>,
): ResumoMensal['gasto_acumulado_diario'] {
  let total = 0;
  return Array.from({ length: dias }, (_, i) => {
    total = valores[i + 1] ?? total;
    return { dia: i + 1, total };
  });
}

function resumo(parcial: Partial<ResumoMensal> = {}): ResumoMensal {
  return {
    mes: '2026-09',
    // Números que não batem com as tabelas: prova que os cards são os da API.
    total_gastos: 1500,
    total_receitas: 5000,
    saldo: 3500,
    por_categoria: [
      { categoria_id: 'moradia', nome: 'Moradia', cor: '#4FC3F7', total: 1000, percentual: 66.7 },
      {
        categoria_id: 'alimentacao',
        nome: 'Alimentação',
        cor: '#E57373',
        total: 500,
        percentual: 33.3,
      },
    ],
    por_forma_pagamento: [
      { forma_pagamento: 'CREDITO', nome: 'Cartão de crédito', total: 1234.5, percentual: 45.3 },
      { forma_pagamento: 'PIX', nome: 'Pix', total: 265.5, percentual: 54.7 },
    ],
    gasto_acumulado_diario: acumulado(30, { 1: 1000, 2: 1500 }),
    linhas_ignoradas: 0,
    ...parcial,
  };
}

describe('ResumoPage', () => {
  let harness: RouterTestingHarness;
  let controle: HttpTestingController;
  let breakpoints: BreakpointsFalsos;
  let graficos: GraficoFalso[];

  beforeEach(async () => {
    breakpoints = new BreakpointsFalsos();
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
        { provide: BreakpointObserver, useValue: breakpoints },
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
          useValue: () => ({ texto: 'rgb(0, 0, 0)', grade: 'rgb(1, 1, 1)', destaque: DESTAQUE }),
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

  /** Responde a (única) busca pendente e devolve o mês pedido. */
  async function responder(resposta: ResumoMensal): Promise<string | null> {
    const pendentes = pedidos();
    expect(pendentes).toHaveLength(1);
    const mes = pendentes[0].request.params.get('mes');
    pendentes[0].flush(resposta);
    await estabilizar();
    return mes;
  }

  async function abrir(resposta: ResumoMensal = resumo()): Promise<void> {
    await harness.navigateByUrl('/resumo?mes=2026-09');
    await estabilizar();
    expect(await responder(resposta)).toBe('2026-09');
  }

  function pagina(): HTMLElement {
    return harness.routeNativeElement!;
  }

  function texto(el: Element | null | undefined): string {
    return (el?.textContent ?? '').replace(/ /g, ' ').trim();
  }

  function cards(): string[] {
    return Array.from(pagina().querySelectorAll('.total .numero')).map(texto);
  }

  function grafico(tipo: 'doughnut' | 'bar' | 'line'): GraficoFalso {
    const encontrados = graficos.filter((item) => item.tipo === tipo);
    expect(encontrados).toHaveLength(1);
    return encontrados[0];
  }

  function linhas(tabela: string): string[][] {
    return Array.from(pagina().querySelectorAll(`.${tabela} tbody tr`)).map((linha) =>
      Array.from(linha.querySelectorAll('td')).map(texto),
    );
  }

  it('cards_com_numeros_da_api__CA_12_1', async () => {
    await abrir();

    expect(pagina().querySelector('h1')?.textContent).toBe('Resumo');
    expect(cards()).toEqual(['R$ 1.500,00', 'R$ 5.000,00', 'R$ 3.500,00']);
    expect(pagina().querySelector('.total.saldo')?.classList.contains('negativo')).toBe(false);
  });

  it('saldo_negativo_destacado__CA_12_2', async () => {
    await abrir(resumo({ total_gastos: 100, total_receitas: 40, saldo: -60 }));

    expect(pagina().querySelector('.total.saldo')?.classList.contains('negativo')).toBe(true);
    expect(cards()[2]).toBe('− R$ 60,00');
  });

  it('tabelas_por_categoria_e_forma__CA_F09_12', async () => {
    await abrir();

    expect(texto(pagina().querySelector('.por-categoria h2'))).toBe('Gastos por categoria');
    expect(linhas('por-categoria')).toEqual([
      ['Moradia', 'R$ 1.000,00', '66,7%'],
      ['Alimentação', 'R$ 500,00', '33,3%'],
    ]);
    const cores = Array.from(pagina().querySelectorAll<HTMLElement>('.por-categoria .cor'));
    expect(cores.map((cor) => cor.style.backgroundColor)).toEqual([
      'rgb(79, 195, 247)',
      'rgb(229, 115, 115)',
    ]);
    expect(cores[0].getAttribute('aria-hidden')).toBe('true');
    expect(texto(pagina().querySelector('.por-forma h2'))).toBe('Gastos por forma de pagamento');
    expect(linhas('por-forma')).toEqual([
      ['Cartão de crédito', 'R$ 1.234,50', '45,3%'],
      ['Pix', 'R$ 265,50', '54,7%'],
    ]);
  });

  it('vazio_e_so_receitas__CA_F09_13', async () => {
    const vazio = {
      total_gastos: 0,
      total_receitas: 0,
      saldo: 0,
      por_categoria: [],
      por_forma_pagamento: [],
    };
    await abrir(resumo(vazio));
    expect(cards()).toEqual(['R$ 0,00', 'R$ 0,00', 'R$ 0,00']);
    expect(texto(pagina().querySelector('app-estado-vazio'))).toContain(
      'Nenhum lançamento em setembro de 2026.',
    );
    expect(pagina().querySelector('table')).toBeNull();

    TestBed.inject(DadosStore).incrementar();
    await estabilizar();
    await responder(resumo({ ...vazio, total_receitas: 5000, saldo: 5000 }));

    expect(texto(pagina().querySelector('app-estado-vazio'))).toContain(
      'Nenhum gasto em setembro de 2026.',
    );
    expect(cards()).toEqual(['R$ 0,00', 'R$ 5.000,00', 'R$ 5.000,00']);
  });

  it('recarrega_por_mes_e_versao__CA_F09_14', async () => {
    await abrir();

    // Borda 16: registro pelo botão da barra com o resumo aberto.
    TestBed.inject(DadosStore).incrementar();
    await estabilizar();
    expect(pagina().querySelector('.conteudo.recarregando')).not.toBeNull(); // esmaecido
    expect(await responder(resumo({ total_gastos: 1600 }))).toBe('2026-09');
    expect(cards()[0]).toBe('R$ 1.600,00');

    // Borda 15: a resposta de outubro chega depois da de novembro e é descartada.
    const proximo = () =>
      pagina().querySelector<HTMLButtonElement>('button[aria-label="Próximo mês"]')!.click();
    proximo();
    await estabilizar();
    proximo();
    await estabilizar();
    const [outubro, novembro] = pedidos();
    expect(outubro.request.params.get('mes')).toBe('2026-10');
    expect(novembro.request.params.get('mes')).toBe('2026-11');
    novembro.flush(resumo({ mes: '2026-11', total_gastos: 11 }));
    outubro.flush(resumo({ mes: '2026-10', total_gastos: 10 }));
    await estabilizar();

    expect(cards()[0]).toBe('R$ 11,00');
  });

  it('erro_de_carga__CA_F09_15', async () => {
    await harness.navigateByUrl('/resumo?mes=2026-09');
    await estabilizar();
    pedidos()[0].flush(
      { erro: { codigo: 'PLANILHA_INDISPONIVEL', mensagem: 'Indisponível.', detalhes: [] } },
      { status: 503, statusText: 'x' },
    );
    await estabilizar();

    expect(texto(pagina())).toContain('Não foi possível carregar o resumo.');
    expect(pagina().querySelector('.totais')).toBeNull();
  });

  it('tabelas_lado_a_lado_ou_empilhadas__CA_F09_16', async () => {
    await abrir();
    expect(pagina().querySelector('.tabelas')?.classList.contains('lado-a-lado')).toBe(true);

    breakpoints.largura.next(360);
    await estabilizar();
    expect(pagina().querySelector('.tabelas')?.classList.contains('lado-a-lado')).toBe(false);

    breakpoints.largura.next(960); // limite inclusivo
    await estabilizar();
    expect(pagina().querySelector('.tabelas')?.classList.contains('lado-a-lado')).toBe(true);
  });

  it('rosca_com_cores_das_categorias__CA_13_1', async () => {
    await abrir(
      resumo({
        por_categoria: [
          {
            categoria_id: 'moradia',
            nome: 'Moradia',
            cor: '#4FC3F7',
            total: 1000,
            percentual: 66.7,
          },
          {
            categoria_id: 'sumiu',
            nome: 'Categoria não encontrada',
            cor: '#9E9E9E',
            total: 500,
            percentual: 33.3,
          },
        ],
      }),
    );

    const rosca = grafico('doughnut');
    expect(rosca.data.labels).toEqual(['Moradia', 'Categoria não encontrada']);
    expect(rosca.data.datasets[0].data).toEqual([1000, 500]);
    expect(rosca.data.datasets[0].backgroundColor).toEqual(['#4FC3F7', '#9E9E9E']);
    expect(rosca.options.plugins?.legend?.display).toBe(false);
    // Acima da tabela, na seção de categorias (Q1).
    const secao = pagina().querySelector('.por-categoria')!;
    expect(secao.contains(rosca.canvas)).toBe(true);
    const posicao = rosca.canvas.compareDocumentPosition(secao.querySelector('table')!);
    expect(posicao & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('barras_por_forma__CA_F10_2', async () => {
    await abrir();

    const barras = grafico('bar');
    expect(barras.options.indexAxis).toBe('y');
    expect(barras.data.labels).toEqual(['Cartão de crédito', 'Pix']);
    expect(barras.data.datasets[0].data).toEqual([1234.5, 265.5]);
    expect(barras.options.elements?.bar?.backgroundColor).toBe(DESTAQUE); // padrão do tema
    expect(barras.options.plugins?.legend?.display).toBe(false);
    expect(pagina().querySelector('.por-forma')?.contains(barras.canvas)).toBe(true);
  });

  it('linha_do_acumulado__CA_F10_3', async () => {
    await abrir();

    const linha = grafico('line');
    expect(linha.data.labels).toEqual(Array.from({ length: 30 }, (_, i) => String(i + 1)));
    expect(linha.data.datasets[0].label).toBe('Gasto acumulado');
    const valores = linha.data.datasets[0].data as number[];
    expect([valores[0], valores[1], valores[14], valores[29]]).toEqual([1000, 1500, 1500, 1500]);
    expect(linha.options.elements?.line?.borderColor).toBe(DESTAQUE);
    expect(linha.options.plugins?.legend?.display).toBe(false);
    const titulo = linha.options.plugins?.tooltip?.callbacks?.title as unknown as (
      itens: Partial<TooltipItem<'line'>>[],
    ) => string;
    expect(titulo([{ label: '15' }])).toBe('Dia 15');
    const escalas = linha.options.scales as Record<string, { beginAtZero?: boolean }>;
    expect(escalas['y'].beginAtZero).toBe(true);
    expect(texto(pagina().querySelector('.acumulado h2'))).toBe('Gasto acumulado no mês');
  });

  it('sem_gastos_sem_graficos__CA_13_2', async () => {
    await abrir(
      resumo({
        total_gastos: 0,
        saldo: 5000,
        por_categoria: [],
        por_forma_pagamento: [],
        gasto_acumulado_diario: acumulado(30, {}),
      }),
    );

    expect(pagina().querySelector('canvas')).toBeNull();
    expect(graficos).toHaveLength(0);
    expect(texto(pagina().querySelector('app-estado-vazio'))).toContain('Nenhum gasto em');
  });

  it('recarga_atualiza_os_mesmos_graficos__CA_F10_5', async () => {
    await abrir();
    expect(graficos).toHaveLength(3);

    TestBed.inject(DadosStore).incrementar();
    await estabilizar();
    await responder(
      resumo({
        por_categoria: [
          { categoria_id: 'lazer', nome: 'Lazer', cor: '#FFB74D', total: 80, percentual: 100 },
        ],
        gasto_acumulado_diario: acumulado(30, { 3: 80 }),
      }),
    );

    expect(graficos).toHaveLength(3); // nenhum gráfico novo
    expect(grafico('doughnut').data.labels).toEqual(['Lazer']);
    expect(grafico('doughnut').update).toHaveBeenCalled();
    expect((grafico('line').data.datasets[0].data as number[])[29]).toBe(80);
  });

  it('graficos_acessiveis__CA_F10_6', async () => {
    await abrir();

    const canvases = Array.from(pagina().querySelectorAll('canvas'));
    expect(canvases.map((canvas) => canvas.getAttribute('role'))).toEqual(['img', 'img', 'img']);
    const rotulos = canvases.map((canvas) =>
      (canvas.getAttribute('aria-label') ?? '').replace(/\u00a0/g, ' '),
    );
    expect(rotulos).toEqual([
      'Gráfico de rosca dos gastos por categoria. Os valores estão na tabela abaixo.',
      'Gráfico de barras dos gastos por forma de pagamento. Os valores estão na tabela abaixo.',
      'Gráfico de linha do gasto acumulado dia a dia em setembro de 2026: R$ 1.500,00 no fim do mês.',
    ]);
  });

  function faixa(): string | null {
    const aviso = pagina().querySelector('header + app-aviso-linhas-ignoradas [role="status"] p');
    return aviso ? aviso.textContent!.replace(/\s+/g, ' ').trim() : null;
  }

  it('mostra_linhas_ignoradas__CA_16_3', async () => {
    await abrir(resumo({ linhas_ignoradas: 3 }));
    expect(faixa()).toBe(
      '3 linhas da planilha foram ignoradas por estarem inválidas. Corrija-as na planilha e use Recarregar dados.',
    );

    TestBed.inject(DadosStore).incrementar();
    await estabilizar();
    await responder(resumo());
    expect(faixa()).toBeNull();
  });
});
