import { BreakpointObserver } from '@angular/cdk/layout';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
  TestRequest,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { DateAdapter, MAT_DATE_LOCALE, provideNativeDateAdapter } from '@angular/material/core';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { BreakpointsFalsos } from '../../../testing/breakpoints';
import { umaCategoria } from '../../../testing/categorias';
import { provideMaterialParaTestes } from '../../../testing/material';
import { routes } from '../../app.routes';
import { Avisos } from '../../core/avisos/avisos';
import { erroInterceptor } from '../../core/interceptors/erro.interceptor';
import { Lancamento, ListaLancamentos } from '../../core/models/lancamento';
import { DadosStore } from '../../core/state/dados.store';
import { AdaptadorDeDataPtBr } from '../../core/utils/adaptador-de-data';

const CATEGORIAS = [
  umaCategoria({ id: 'mercado', nome: 'Mercado' }),
  umaCategoria({ id: 'lazer', nome: 'Lazer', cor: '#FFB74D', ativa: false }),
  umaCategoria({ id: 'salario', nome: 'Salário', tipo: 'RECEITA', cor: '#66BB6A' }),
];
const FORMAS = [
  { codigo: 'PIX', nome: 'Pix' },
  { codigo: 'CREDITO', nome: 'Cartão de crédito' },
];

function lancamento(parcial: Partial<Lancamento> & Pick<Lancamento, 'id'>): Lancamento {
  return {
    data: '2026-09-30',
    tipo: 'GASTO',
    descricao: `Compra ${parcial.id}`,
    valor: 42.5,
    categoria_id: 'mercado',
    categoria_nome: 'Mercado',
    categoria_cor: '#E57373',
    forma_pagamento: 'PIX',
    observacao: null,
    parcelamento_id: null,
    parcela_numero: null,
    parcela_total: null,
    recorrencia_id: null,
    criado_em: '2026-09-30T10:00:00',
    atualizado_em: '2026-09-30T10:00:00',
    ...parcial,
  };
}

function lista(
  itens: Lancamento[],
  totais = { gastos: 0, receitas: 0, saldo: 0 },
  mes = '2026-09',
) {
  return { mes, itens, totais, linhas_ignoradas: 0 } satisfies ListaLancamentos;
}

const ITENS = [
  lancamento({ id: 'g1', observacao: 'no restaurante' }),
  lancamento({
    id: 'p3',
    data: '2026-09-15',
    descricao: 'Geladeira',
    valor: 333.34,
    forma_pagamento: 'CREDITO',
    parcelamento_id: 'par',
    parcela_numero: 3,
    parcela_total: 10,
  }),
  lancamento({
    id: 'r1',
    data: '2026-09-05',
    tipo: 'RECEITA',
    descricao: 'Salário',
    valor: 5000,
    categoria_id: 'salario',
    categoria_nome: 'Salário',
    categoria_cor: '#66BB6A',
    forma_pagamento: null,
    recorrencia_id: 'rec',
  }),
];

describe('LancamentosPage', () => {
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

  async function estabilizar(): Promise<void> {
    for (let i = 0; i < 3; i++) {
      await new Promise((resolver) => setTimeout(resolver));
      await harness.fixture.whenStable();
    }
  }

  function pedidosDeLista(): TestRequest[] {
    return controle.match((requisicao) => requisicao.url === '/api/lancamentos');
  }

  /** Responde a (única) busca pendente e devolve os parâmetros que ela usou. */
  async function responder(resposta: ListaLancamentos): Promise<Record<string, string | null>> {
    const pedidos = pedidosDeLista();
    expect(pedidos).toHaveLength(1);
    const params = pedidos[0].request.params;
    pedidos[0].flush(resposta);
    await estabilizar();
    return Object.fromEntries(params.keys().map((chave) => [chave, params.get(chave)]));
  }

  async function abrir(url: string, resposta: ListaLancamentos = lista(ITENS)): Promise<void> {
    await harness.navigateByUrl(url);
    await estabilizar();
    for (const pedido of controle.match('/api/categorias?incluir_inativas=true')) {
      pedido.flush(CATEGORIAS);
    }
    for (const pedido of controle.match('/api/formas-pagamento')) {
      pedido.flush(FORMAS);
    }
    await estabilizar();
    await responder(resposta);
  }

  function pagina(): HTMLElement {
    return harness.routeNativeElement!;
  }

  function linhas(): HTMLElement[] {
    return Array.from(pagina().querySelectorAll<HTMLElement>('.lancamento'));
  }

  function url(): string {
    return TestBed.inject(Router).url;
  }

  async function escolher(filtro: string, texto: string): Promise<void> {
    pagina().querySelector<HTMLElement>(`mat-select.${filtro} .mat-mdc-select-trigger`)!.click();
    await estabilizar();
    const opcao = Array.from(document.querySelectorAll<HTMLElement>('mat-option')).find(
      (item) => item.textContent?.trim() === texto,
    );
    if (!opcao) {
      throw new Error(`opção "${texto}" não encontrada em ${filtro}`);
    }
    opcao.click();
    await estabilizar();
  }

  async function opcoes(filtro: string): Promise<string[]> {
    pagina().querySelector<HTMLElement>(`mat-select.${filtro} .mat-mdc-select-trigger`)!.click();
    await estabilizar();
    const textos = Array.from(document.querySelectorAll('mat-option')).map(
      (opcao) => opcao.textContent?.trim() ?? '',
    );
    document.querySelector<HTMLElement>('.cdk-overlay-transparent-backdrop')?.click();
    await estabilizar();
    return textos;
  }

  function totais(): string[] {
    return Array.from(pagina().querySelectorAll('.total .numero')).map(
      (numero) => numero.textContent?.replace(/ /g, ' ').trim() ?? '',
    );
  }

  it('mostra_itens_formatados__CA_03_1', async () => {
    await abrir('/lancamentos?mes=2026-09');

    const [gasto, parcela, receita] = linhas();
    expect(linhas()).toHaveLength(3);
    expect(gasto.textContent).toContain('30/09/2026');
    expect(gasto.querySelector('.categoria')?.textContent).toBe('Mercado');
    expect(gasto.querySelector<HTMLElement>('.cor')?.style.backgroundColor).toBe(
      'rgb(229, 115, 115)',
    );
    expect(gasto.querySelector('.forma')?.textContent).toBe('Pix');
    expect(gasto.querySelector('.observacao')?.textContent).toBe('no restaurante');
    expect(parcela.querySelector('.parcela')?.textContent).toBe('3/10');
    expect(parcela.querySelector('.forma')?.textContent).toBe('Cartão de crédito');
    expect(receita.querySelector('.forma')?.textContent).toBe('—');
    expect(receita.querySelector('.recorrente')?.getAttribute('aria-label')).toBe(
      'Lançamento recorrente',
    );
    expect(receita.querySelector('.categoria')?.textContent).toBe('Salário'); // nome atual (CA-11.2)
  });

  it('valor_com_sinal_e_cor__CA_F07_20', async () => {
    await abrir('/lancamentos?mes=2026-09');

    const valores = linhas().map((linha) => linha.querySelector<HTMLElement>('.valor')!);
    const texto = (el: HTMLElement) => el.textContent?.replace(/ /g, ' ').trim();
    expect(texto(valores[0])).toBe('− R$ 42,50');
    expect(valores[0].classList.contains('receita')).toBe(false);
    expect(valores[0].getAttribute('aria-label')?.replace(/ /g, ' ')).toBe('gasto de R$ 42,50');
    expect(texto(valores[2])).toBe('+ R$ 5.000,00');
    expect(valores[2].classList.contains('receita')).toBe(true);
    expect(valores[2].getAttribute('aria-label')?.replace(/ /g, ' ')).toBe(
      'receita de R$ 5.000,00',
    );
  });

  it('filtros_e_totais_da_api__CA_03_2', async () => {
    await abrir('/lancamentos?mes=2026-09');

    await escolher('filtro-tipo', 'Gastos');
    expect(url()).toBe('/lancamentos?mes=2026-09&tipo=GASTO');
    // Números que não batem com a soma dos itens: prova que a tela mostra os da API.
    const params = await responder(
      lista([ITENS[0]], { gastos: 123.45, receitas: 0, saldo: -123.45 }),
    );
    expect(params).toEqual({ mes: '2026-09', tipo: 'GASTO' });
    expect(totais()).toEqual(['R$ 123,45', 'R$ 0,00', '− R$ 123,45']);
    expect(pagina().textContent).toContain('Totais dos lançamentos filtrados');

    await escolher('filtro-forma', 'Pix');
    expect(await responder(lista([ITENS[0]]))).toEqual({
      mes: '2026-09',
      tipo: 'GASTO',
      forma_pagamento: 'PIX',
    });
  });

  it('saldo_negativo_em_destaque__CA_F07_12', async () => {
    await abrir(
      '/lancamentos?mes=2026-09',
      lista([ITENS[0]], { gastos: 100, receitas: 40, saldo: -60 }),
    );

    const saldo = pagina().querySelector('.total.saldo')!;
    expect(saldo.classList.contains('negativo')).toBe(true);
    expect(totais()[2]).toBe('− R$ 60,00');
  });

  it('vazio_com_e_sem_filtro__CA_03_3', async () => {
    await abrir('/lancamentos?mes=2026-09', lista([]));
    expect(pagina().textContent).toContain('Nenhum lançamento em setembro de 2026.');

    await escolher('filtro-tipo', 'Receitas');
    await responder(lista([]));
    expect(pagina().textContent).toContain('Nenhum lançamento com esses filtros.');

    const limpar = Array.from(pagina().querySelectorAll<HTMLButtonElement>('.vazio button')).find(
      (botao) => botao.textContent?.trim() === 'Limpar filtros',
    )!;
    limpar.click();
    await estabilizar();
    expect(url()).toBe('/lancamentos?mes=2026-09');
    await responder(lista([]));
  });

  it('recarrega_apos_registro__CA_01_5', async () => {
    await abrir('/lancamentos?mes=2026-09', lista([]));

    TestBed.inject(DadosStore).incrementar(); // o diálogo de F-06 salvou
    await estabilizar();
    await responder(lista([ITENS[0]]));

    expect(linhas()).toHaveLength(1);
  });

  it('troca_de_mes_mantem_filtros__CA_F07_15', async () => {
    await abrir('/lancamentos?mes=2026-09&tipo=GASTO');

    pagina().querySelector<HTMLButtonElement>('button[aria-label="Próximo mês"]')!.click();
    await estabilizar();

    // Durante a recarga o conteúdo anterior continua na tela, esmaecido.
    expect(pagina().querySelector('.conteudo.recarregando')).not.toBeNull();
    expect(linhas()).toHaveLength(3);
    expect(await responder(lista([], undefined, '2026-10'))).toEqual({
      mes: '2026-10',
      tipo: 'GASTO',
    });
    expect(url()).toBe('/lancamentos?mes=2026-10&tipo=GASTO');
  });

  it('resposta_antiga_descartada__borda_15', async () => {
    await abrir('/lancamentos?mes=2026-09');

    pagina().querySelector<HTMLButtonElement>('button[aria-label="Próximo mês"]')!.click();
    await estabilizar();
    pagina().querySelector<HTMLButtonElement>('button[aria-label="Próximo mês"]')!.click();
    await estabilizar();
    const [outubro, novembro] = pedidosDeLista();
    novembro.flush(lista([lancamento({ id: 'nov' })], undefined, '2026-11'));
    outubro.flush(lista([lancamento({ id: 'out' })], undefined, '2026-10')); // chega atrasada
    await estabilizar();

    expect(linhas()).toHaveLength(1);
    expect(linhas()[0].textContent).toContain('Compra nov');
  });

  it('categoria_depende_do_tipo__CA_F07_16', async () => {
    await abrir('/lancamentos?mes=2026-09');
    expect(await opcoes('filtro-categoria')).toEqual([
      'Todas',
      'Mercado',
      'Lazer', // inativa também aparece
      'Salário',
    ]);

    await escolher('filtro-categoria', 'Mercado');
    await responder(lista([]));
    await escolher('filtro-tipo', 'Receitas');

    expect(url()).toBe('/lancamentos?mes=2026-09&tipo=RECEITA'); // categoria de gasto limpa
    await responder(lista([]));
    expect(await opcoes('filtro-categoria')).toEqual(['Todas', 'Salário']);
  });

  it('filtros_na_url__CA_F07_19', async () => {
    await harness.navigateByUrl('/lancamentos?mes=2026-09&tipo=OUTRO&forma_pagamento=PIX');
    await estabilizar();
    controle.match('/api/categorias?incluir_inativas=true').forEach((p) => p.flush(CATEGORIAS));
    controle.match('/api/formas-pagamento').forEach((p) => p.flush(FORMAS));
    await estabilizar();

    // `tipo=OUTRO` descartado e a URL corrigida; o filtro válido foi mantido.
    expect(url()).toBe('/lancamentos?mes=2026-09&forma_pagamento=PIX');
    // Uma busca só: corrigir a URL não muda os filtros válidos.
    expect(await responder(lista([]))).toEqual({ mes: '2026-09', forma_pagamento: 'PIX' });
    expect(pagina().querySelector('mat-select.filtro-forma')?.textContent).toContain('Pix');
  });

  it('tabela_ou_cartoes_por_largura__CA_F07_18', async () => {
    await abrir('/lancamentos?mes=2026-09');
    expect(pagina().querySelector('table.tabela')).not.toBeNull();
    expect(pagina().querySelectorAll('th[scope="col"]')).toHaveLength(5);

    breakpoints.largura.next(360);
    await estabilizar();

    expect(pagina().querySelector('table.tabela')).toBeNull();
    expect(pagina().querySelectorAll('ul.cartoes li.cartao')).toHaveLength(3);
    breakpoints.largura.next(600);
    await estabilizar();
    expect(pagina().querySelector('table.tabela')).not.toBeNull(); // limite inclusivo
  });

  it('erro_de_carga__CA_F07_17', async () => {
    await harness.navigateByUrl('/lancamentos?mes=2026-09');
    await estabilizar();
    controle.match('/api/categorias?incluir_inativas=true').forEach((p) => p.flush(CATEGORIAS));
    controle.match('/api/formas-pagamento').forEach((p) => p.flush(FORMAS));
    pedidosDeLista()[0].flush(
      { erro: { codigo: 'PLANILHA_INDISPONIVEL', mensagem: 'Indisponível.', detalhes: [] } },
      { status: 503, statusText: 'x' },
    );
    await estabilizar();

    expect(pagina().textContent).toContain('Não foi possível carregar os lançamentos.');
    expect(pagina().querySelector('.totais')).toBeNull();
  });
});
