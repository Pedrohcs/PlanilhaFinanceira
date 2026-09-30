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
import { BreakpointsFalsos } from '../../../testing/breakpoints';
import { provideMaterialParaTestes } from '../../../testing/material';
import { routes } from '../../app.routes';
import { Avisos } from '../../core/avisos/avisos';
import { erroInterceptor } from '../../core/interceptors/erro.interceptor';
import { ResumoMensal } from '../../core/models/resumo';
import { DadosStore } from '../../core/state/dados.store';
import { AdaptadorDeDataPtBr } from '../../core/utils/adaptador-de-data';

const URL = '/api/resumo/mensal';

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
    gasto_acumulado_diario: [],
    linhas_ignoradas: 0,
    ...parcial,
  };
}

describe('ResumoPage', () => {
  let harness: RouterTestingHarness;
  let controle: HttpTestingController;
  let breakpoints: BreakpointsFalsos;

  beforeEach(async () => {
    breakpoints = new BreakpointsFalsos();
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
});
