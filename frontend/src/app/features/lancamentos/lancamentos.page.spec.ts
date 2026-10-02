import { BreakpointObserver } from '@angular/cdk/layout';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
  TestRequest,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { DateAdapter, MAT_DATE_LOCALE, provideNativeDateAdapter } from '@angular/material/core';
import { MatDialog } from '@angular/material/dialog';
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
  let avisos: { mostrar: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    breakpoints = new BreakpointsFalsos();
    avisos = { mostrar: vi.fn() };
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
        { provide: Avisos, useValue: avisos },
      ],
    });
    controle = TestBed.inject(HttpTestingController);
    harness = await RouterTestingHarness.create();
  });

  afterEach(() => {
    TestBed.inject(MatDialog).closeAll();
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

  /** Abre o menu ⋮ do lançamento e escolhe a ação. */
  async function acao(
    descricao: string,
    texto: 'Editar' | 'Excluir' | 'Excluir parcelamento inteiro',
  ): Promise<void> {
    pagina()
      .querySelector<HTMLButtonElement>(`button[aria-label="Ações de ${descricao}"]`)!
      .click();
    await estabilizar();
    const item = Array.from(document.querySelectorAll<HTMLElement>('.mat-mdc-menu-item')).find(
      (opcao) => opcao.textContent?.replace(/^\s*\w+\s*/, '').trim() === texto,
    )!;
    item.click();
    await estabilizar();
  }

  function confirmacao(): HTMLElement | null {
    return document.querySelector<HTMLElement>('app-confirmacao-dialog');
  }

  async function responderConfirmacao(
    texto: 'Cancelar' | 'Excluir' | 'Excluir parcelas',
  ): Promise<void> {
    Array.from(confirmacao()!.querySelectorAll<HTMLButtonElement>('button'))
      .find((botao) => botao.textContent?.trim() === texto)!
      .click();
    await estabilizar();
  }

  /** Textos do menu ⋮ do lançamento, sem o nome do ícone; fecha o menu em seguida. */
  async function itensDoMenu(descricao: string): Promise<string[]> {
    pagina()
      .querySelector<HTMLButtonElement>(`button[aria-label="Ações de ${descricao}"]`)!
      .click();
    await estabilizar();
    const itens = Array.from(document.querySelectorAll('.mat-mdc-menu-item')).map(
      (item) => item.textContent?.replace(/^\s*\w+\s*/, '').trim() ?? '',
    );
    document.querySelector<HTMLElement>('.cdk-overlay-backdrop')!.click();
    await estabilizar();
    return itens;
  }

  function semNbsp(texto: string | null | undefined): string {
    return (texto ?? '').replace(/\u00a0/g, ' ').trim();
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
    expect(pagina().querySelectorAll('th[scope="col"]')).toHaveLength(6); // + Ações (F-08)

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

  it('acoes_em_tabela_e_cartoes__CA_F08_16', async () => {
    await abrir('/lancamentos?mes=2026-09');
    expect(pagina().querySelector('th.coluna-acoes')?.textContent?.trim()).toBe('Ações');
    for (const linha of linhas()) {
      expect(linha.querySelector('button.botao-acoes')).not.toBeNull();
    }

    breakpoints.largura.next(360);
    await estabilizar();
    const botoes = pagina().querySelectorAll('li.cartao button.botao-acoes');
    expect(Array.from(botoes).map((b) => b.getAttribute('aria-label'))).toEqual([
      'Ações de Compra g1',
      'Ações de Geladeira',
      'Ações de Salário',
    ]);

    (botoes[0] as HTMLButtonElement).click();
    await estabilizar();
    const itens = Array.from(document.querySelectorAll('.mat-mdc-menu-item')).map((item) =>
      item.textContent?.replace(/edit|delete/, '').trim(),
    );
    expect(itens).toEqual(['Editar', 'Excluir']);
  });

  it('excluir_confirma_e_recarrega__CA_06_1', async () => {
    await abrir('/lancamentos?mes=2026-09');

    await acao('Geladeira', 'Excluir');
    expect(confirmacao()?.querySelector('h2')?.textContent).toBe('Excluir lançamento?');
    expect(semNbsp(confirmacao()?.querySelector('mat-dialog-content')?.textContent)).toBe(
      '"Geladeira" — − R$ 333,34 em 15/09/2026 será excluído. ' +
        'Só esta parcela (3/10) será excluída; as demais continuam.',
    );
    await responderConfirmacao('Cancelar');
    controle.expectNone('/api/lancamentos/p3'); // cancelar não exclui

    await acao('Salário', 'Excluir');
    expect(semNbsp(confirmacao()?.querySelector('mat-dialog-content')?.textContent)).toBe(
      '"Salário" — + R$ 5.000,00 em 05/09/2026 será excluído. ' +
        'A recorrência não gera este lançamento de novo.',
    );
    await responderConfirmacao('Excluir');

    const del = controle.expectOne('/api/lancamentos/r1');
    expect(del.request.method).toBe('DELETE');
    del.flush(null, { status: 204, statusText: 'No Content' });
    await estabilizar();

    expect(avisos.mostrar).toHaveBeenCalledWith('Lançamento excluído.');
    await responder(lista(ITENS.slice(0, 2))); // lista e totais recalculados (CA-06.2)
    expect(linhas()).toHaveLength(2);
  });

  it('404_ao_excluir_recarrega__CA_F08_14', async () => {
    await abrir('/lancamentos?mes=2026-09');

    await acao('Compra g1', 'Excluir');
    await responderConfirmacao('Excluir');
    controle.expectOne('/api/lancamentos/g1').flush(
      {
        erro: { codigo: 'NAO_ENCONTRADO', mensagem: 'Lançamento não encontrado.', detalhes: [] },
      },
      { status: 404, statusText: 'x' },
    );
    await estabilizar();

    expect(avisos.mostrar).toHaveBeenCalledWith('Lançamento não encontrado.');
    expect(avisos.mostrar).not.toHaveBeenCalledWith('Lançamento excluído.');
    await responder(lista(ITENS.slice(1))); // já não estava lá: a lista se atualiza
    expect(linhas()).toHaveLength(2);
  });

  it('planilha_fora_ao_excluir_mantem_a_lista__borda_12', async () => {
    await abrir('/lancamentos?mes=2026-09');

    await acao('Compra g1', 'Excluir');
    await responderConfirmacao('Excluir');
    controle
      .expectOne('/api/lancamentos/g1')
      .flush(
        { erro: { codigo: 'PLANILHA_INDISPONIVEL', mensagem: 'Indisponível.', detalhes: [] } },
        { status: 503, statusText: 'x' },
      );
    await estabilizar();

    expect(pedidosDeLista()).toHaveLength(0); // não recarrega
    expect(linhas()).toHaveLength(3);
    expect(avisos.mostrar).not.toHaveBeenCalledWith('Lançamento excluído.');
  });

  it('editar_abre_o_dialogo_pre_preenchido__CA_05_1', async () => {
    await abrir('/lancamentos?mes=2026-09');

    await acao('Geladeira', 'Editar');

    const dialogo = document.querySelector('mat-dialog-container')!;
    expect(dialogo.querySelector('h2')?.textContent).toBe('Editar gasto');
    expect(dialogo.querySelector<HTMLInputElement>('[formcontrolname="descricao"]')?.value).toBe(
      'Geladeira',
    );
    expect(dialogo.querySelector('.vinculo')?.textContent?.trim()).toBe('Parcela 3/10');
    controle.expectNone('/api/lancamentos/p3'); // nada salvo só por abrir
  });

  it('menu_da_parcela__CA_F12_14', async () => {
    await abrir('/lancamentos?mes=2026-09');

    expect(await itensDoMenu('Geladeira')).toEqual([
      'Editar',
      'Excluir',
      'Excluir parcelamento inteiro',
    ]);
    expect(await itensDoMenu('Compra g1')).toEqual(['Editar', 'Excluir']);
  });

  it('excluir_parcelamento_inteiro__CA_08_2', async () => {
    await abrir('/lancamentos?mes=2026-09');

    await acao('Geladeira', 'Excluir parcelamento inteiro');
    expect(confirmacao()?.querySelector('h2')?.textContent).toBe('Excluir parcelamento inteiro?');
    expect(semNbsp(confirmacao()?.querySelector('mat-dialog-content')?.textContent)).toBe(
      '"Geladeira" — todas as parcelas restantes deste parcelamento em 10×, ' +
        'em todos os meses, serão excluídas.',
    );
    await responderConfirmacao('Cancelar');
    controle.expectNone('/api/parcelamentos/par'); // cancelar não exclui

    await acao('Geladeira', 'Excluir parcelamento inteiro');
    await responderConfirmacao('Excluir parcelas');
    const del = controle.expectOne('/api/parcelamentos/par');
    expect(del.request.method).toBe('DELETE');
    del.flush(null, { status: 204, statusText: 'No Content' });
    await estabilizar();

    expect(avisos.mostrar).toHaveBeenCalledWith('Parcelamento excluído.');
    await responder(lista([ITENS[0], ITENS[2]])); // lista e totais recalculados
    expect(linhas()).toHaveLength(2);
  });

  it('excluir_parcelamento_404_e_503__CA_F12_15', async () => {
    await abrir('/lancamentos?mes=2026-09');

    await acao('Geladeira', 'Excluir parcelamento inteiro');
    await responderConfirmacao('Excluir parcelas');
    controle
      .expectOne('/api/parcelamentos/par')
      .flush(
        { erro: { codigo: 'PLANILHA_INDISPONIVEL', mensagem: 'Indisponível.', detalhes: [] } },
        { status: 503, statusText: 'x' },
      );
    await estabilizar();
    expect(pedidosDeLista()).toHaveLength(0); // planilha fora: a lista continua

    await acao('Geladeira', 'Excluir parcelamento inteiro');
    await responderConfirmacao('Excluir parcelas');
    controle.expectOne('/api/parcelamentos/par').flush(
      {
        erro: { codigo: 'NAO_ENCONTRADO', mensagem: 'Parcelamento não encontrado.', detalhes: [] },
      },
      { status: 404, statusText: 'x' },
    );
    await estabilizar();

    expect(avisos.mostrar).toHaveBeenCalledWith('Parcelamento não encontrado.');
    expect(avisos.mostrar).not.toHaveBeenCalledWith('Parcelamento excluído.');
    await responder(lista([ITENS[0], ITENS[2]])); // já não existia: a lista se atualiza
  });

  function faixa(): string | null {
    const aviso = pagina().querySelector('header + app-aviso-linhas-ignoradas [role="status"] p');
    return aviso ? aviso.textContent!.replace(/\s+/g, ' ').trim() : null;
  }

  it('mostra_linhas_ignoradas__CA_16_3', async () => {
    await abrir('/lancamentos?mes=2026-09', { ...lista(ITENS), linhas_ignoradas: 1 });
    expect(faixa()).toBe(
      '1 linha da planilha foi ignorada por estar inválida. Corrija-a na planilha e use Recarregar dados.',
    );

    // Borda 2: corrigida na planilha e "Recarregar dados" (versao++) → a faixa some.
    TestBed.inject(DadosStore).incrementar();
    await estabilizar();
    await responder(lista(ITENS));
    expect(faixa()).toBeNull();
  });
});
