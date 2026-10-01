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
import { provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { BreakpointsFalsos } from '../../../testing/breakpoints';
import { umaCategoria } from '../../../testing/categorias';
import { provideMaterialParaTestes } from '../../../testing/material';
import { routes } from '../../app.routes';
import { Avisos } from '../../core/avisos/avisos';
import { erroInterceptor } from '../../core/interceptors/erro.interceptor';
import { Recorrencia } from '../../core/models/recorrencia';
import { DadosStore } from '../../core/state/dados.store';
import { AdaptadorDeDataPtBr } from '../../core/utils/adaptador-de-data';
import { MENSAGEM_REATIVADA } from './recorrencias.page';

const URL = '/api/recorrencias';
const URL_SINCRONIZAR = '/api/recorrencias/sincronizar';
const URL_CATEGORIAS = '/api/categorias?incluir_inativas=true';
const CATEGORIAS = [
  umaCategoria({ id: 'assinaturas', nome: 'Assinaturas', cor: '#BA68C8' }),
  umaCategoria({ id: 'velha', nome: 'Velha', ativa: false }),
  umaCategoria({ id: 'salario', nome: 'Salário', tipo: 'RECEITA', cor: '#66BB6A' }),
];

function recorrencia(parcial: Partial<Recorrencia> & Pick<Recorrencia, 'id'>): Recorrencia {
  return {
    tipo: 'GASTO',
    descricao: 'Streaming',
    valor: 39.9,
    categoria_id: 'assinaturas',
    forma_pagamento: 'CREDITO',
    dia_do_mes: 10,
    mes_inicio: '2026-07',
    mes_fim: null,
    status: 'ATIVA',
    ultimo_mes_gerado: '2026-09',
    proximo_mes: '2026-10',
    criado_em: '2026-07-01T09:00:00',
    atualizado_em: '2026-07-01T09:00:00',
    ...parcial,
  };
}

/** Na ordem da API (F-13 §3.1.6): ativas, pausadas, encerradas. */
const LISTA: Recorrencia[] = [
  recorrencia({ id: 'a', descricao: 'Aluguel', valor: 1500, dia_do_mes: 5 }),
  recorrencia({
    id: 'c',
    descricao: 'Curso',
    mes_fim: '2026-08',
    ultimo_mes_gerado: '2026-08',
    proximo_mes: null,
    categoria_id: 'velha',
  }),
  recorrencia({
    id: 's',
    descricao: 'Salário',
    tipo: 'RECEITA',
    valor: 5000,
    categoria_id: 'salario',
    forma_pagamento: null,
    dia_do_mes: 31,
    mes_fim: '2026-12',
  }),
  recorrencia({
    id: 'p',
    descricao: 'Academia',
    status: 'PAUSADA',
    proximo_mes: null,
    categoria_id: 'sumiu',
  }),
  recorrencia({ id: 'e', descricao: 'Jornal', status: 'ENCERRADA', proximo_mes: null }),
];

describe('RecorrenciasPage', () => {
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
    controle.verify();
  });

  async function estabilizar(): Promise<void> {
    for (let i = 0; i < 3; i++) {
      await new Promise((resolver) => setTimeout(resolver));
      await harness.fixture.whenStable();
    }
  }

  function listas(): TestRequest[] {
    return controle.match((requisicao) => requisicao.url === URL && requisicao.method === 'GET');
  }

  /** `versao++` recarrega também as categorias (F-05): responde se houver pedido. */
  function responderCategorias(): void {
    controle.match(URL_CATEGORIAS).forEach((pedido) => pedido.flush(CATEGORIAS));
  }

  async function responderLista(lista: Recorrencia[] = LISTA): Promise<void> {
    responderCategorias();
    const pendentes = listas();
    expect(pendentes).toHaveLength(1);
    pendentes[0].flush(lista);
    await estabilizar();
  }

  async function abrir(lista: Recorrencia[] = LISTA): Promise<void> {
    await harness.navigateByUrl('/recorrencias');
    await estabilizar();
    await responderLista(lista);
  }

  function pagina(): HTMLElement {
    return harness.routeNativeElement!;
  }

  function texto(el: Element | null | undefined): string {
    return (el?.textContent ?? '').replace(/ /g, ' ').replace(/\s+/g, ' ').trim();
  }

  function linhas(): string[][] {
    return Array.from(pagina().querySelectorAll('tbody tr')).map((linha) =>
      Array.from(linha.querySelectorAll('td')).map(texto),
    );
  }

  /** Abre o menu ⋮ da recorrência e devolve os itens. */
  async function menu(descricao: string): Promise<HTMLElement[]> {
    pagina()
      .querySelector<HTMLButtonElement>(`button[aria-label="Ações de ${descricao}"]`)!
      .click();
    await estabilizar();
    return Array.from(document.querySelectorAll<HTMLElement>('.mat-mdc-menu-panel button'));
  }

  async function acao(descricao: string, rotulo: string): Promise<void> {
    const itens = await menu(descricao);
    itens.find((item) => texto(item).endsWith(rotulo))!.click();
    await estabilizar();
  }

  async function responderStatus(id: string, status: string): Promise<void> {
    const pedido = controle.expectOne(`${URL}/${id}/status`);
    expect(pedido.request.method).toBe('PATCH');
    expect(pedido.request.body).toEqual({ status });
    pedido.flush(recorrencia({ id, status: status as Recorrencia['status'] }));
    await estabilizar();
  }

  async function responderSincronizacao(gerados: number): Promise<void> {
    controle.expectOne(URL_SINCRONIZAR).flush({ lancamentos_gerados: gerados, detalhes: [] });
    await estabilizar();
  }

  it('lista_com_estado_e_proximo_mes__CA_09_1', async () => {
    await abrir();

    expect(texto(pagina().querySelector('h1'))).toBe('Recorrências');
    expect(linhas().map((linha) => linha.slice(0, 7))).toEqual([
      ['Aluguel', 'Assinaturas', '− R$ 1.500,00', 'dia 5', 'desde julho de 2026', 'Ativa', 'outubro de 2026'],
      ['Curso', 'Velha (inativa)', '− R$ 39,90', 'dia 10', 'de julho de 2026 a agosto de 2026', 'Ativa', 'Vigência terminou em agosto de 2026'],
      ['Salário', 'Salário', '+ R$ 5.000,00', 'dia 31', 'de julho de 2026 a dezembro de 2026', 'Ativa', 'outubro de 2026'],
      ['Academia', 'Categoria não encontrada', '− R$ 39,90', 'dia 10', 'desde julho de 2026', 'Pausada', '—'],
      ['Jornal', 'Assinaturas', '− R$ 39,90', 'dia 10', 'desde julho de 2026', 'Encerrada', '—'],
    ]); // prettier-ignore
    const cores = Array.from(pagina().querySelectorAll<HTMLElement>('tbody .cor'));
    expect(cores[0].style.backgroundColor).toBe('rgb(186, 104, 200)');
    expect(cores[3].style.backgroundColor).toBe('rgb(158, 158, 158)'); // apagada → cinza
    const valores = Array.from(pagina().querySelectorAll('tbody .valor'));
    expect(valores[2].classList.contains('receita')).toBe(true);
    expect(valores[0].getAttribute('aria-label')).toBe('gasto de R$ 1.500,00');
    expect(pagina().querySelectorAll('th[scope="col"]')).toHaveLength(8);
  });

  it('cartoes_abaixo_de_600px__CA_F13_20', async () => {
    breakpoints.largura.next(360);
    await abrir();

    expect(pagina().querySelector('table')).toBeNull();
    const cartoes = Array.from(pagina().querySelectorAll('.cartao'));
    expect(cartoes).toHaveLength(5);
    expect(texto(cartoes[1])).toContain('Vigência terminou em agosto de 2026');
    expect(texto(cartoes[0].querySelector('.estado'))).toBe('Ativa');
  });

  it('acoes_por_estado__CA_F13_21', async () => {
    await abrir();

    expect((await menu('Aluguel')).map(texto)).toEqual([
      'edit Editar',
      'pause Pausar',
      'stop Encerrar',
    ]);
    document.querySelector<HTMLElement>('.cdk-overlay-backdrop')?.click();
    await estabilizar();
    expect((await menu('Academia')).map(texto)).toEqual([
      'edit Editar',
      'play_arrow Reativar',
      'stop Encerrar',
    ]);
    document.querySelector<HTMLElement>('.cdk-overlay-backdrop')?.click();
    await estabilizar();
    // Encerrada é definitiva (Q3): sem menu.
    expect(pagina().querySelector('button[aria-label="Ações de Jornal"]')).toBeNull();
  });

  it('pausar_reativar_e_encerrar__CA_F13_21', async () => {
    await abrir();

    await acao('Aluguel', 'Pausar');
    await responderStatus('a', 'PAUSADA');
    expect(avisos.mostrar).toHaveBeenLastCalledWith('Recorrência pausada.');
    await responderLista();

    // Reativar sincroniza na hora (Q5): um aviso só, e as telas recarregam.
    const versao = TestBed.inject(DadosStore).versao();
    await acao('Academia', 'Reativar');
    await responderStatus('p', 'ATIVA');
    await responderSincronizacao(1);
    expect(avisos.mostrar).toHaveBeenLastCalledWith(
      `${MENSAGEM_REATIVADA} 1 lançamento recorrente gerado.`,
    );
    expect(TestBed.inject(DadosStore).versao()).toBe(versao + 1);
    await responderLista();

    // Encerrar pede confirmação; "Cancelar" não envia nada.
    await acao('Aluguel', 'Encerrar');
    const confirmacao = document.querySelector('app-confirmacao-dialog')!;
    expect(texto(confirmacao)).toContain(
      '"Aluguel" deixa de gerar lançamentos. Os lançamentos já gerados continuam. Não é possível reativar depois.',
    );
    Array.from(confirmacao.querySelectorAll<HTMLElement>('button'))
      .find((botao) => texto(botao) === 'Cancelar')!
      .click();
    await estabilizar();
    controle.expectNone(`${URL}/a/status`);

    await acao('Aluguel', 'Encerrar');
    Array.from(document.querySelectorAll<HTMLElement>('app-confirmacao-dialog button'))
      .find((botao) => texto(botao) === 'Encerrar')!
      .click();
    await estabilizar();
    await responderStatus('a', 'ENCERRADA');
    expect(avisos.mostrar).toHaveBeenLastCalledWith('Recorrência encerrada.');
    await responderLista();
  });

  it('status_recusado_avisa_e_recarrega__F13', async () => {
    await abrir();

    await acao('Aluguel', 'Pausar');
    controle.expectOne(`${URL}/a/status`).flush(
      {
        erro: {
          codigo: 'VALIDACAO',
          mensagem: 'Não é possível mudar de Encerrada para Pausada.',
          detalhes: [
            { campo: 'status', mensagem: 'Não é possível mudar de Encerrada para Pausada.' },
          ],
        },
      },
      { status: 422, statusText: 'x' },
    );
    await estabilizar();

    expect(avisos.mostrar).toHaveBeenCalledWith('Não é possível mudar de Encerrada para Pausada.');
    await responderLista(); // outra aba mudou o estado: a lista volta a bater
  });

  it.each([
    [0, 'Recorrência criada.', 0],
    [3, 'Recorrência criada. 3 lançamentos recorrentes gerados.', 1],
  ])('salvar_sincroniza_e_avisa_uma_vez__CA_F13_24 (%i)', async (gerados, mensagem, recargas) => {
    await abrir();
    const versao = TestBed.inject(DadosStore).versao();

    pagina().querySelector<HTMLButtonElement>('button.nova')!.click();
    await estabilizar();
    controle.match('/api/formas-pagamento').forEach((pedido) => pedido.flush([]));
    // O diálogo salva sozinho (coberto no spec dele); aqui ele fecha com a recorrência salva.
    TestBed.inject(MatDialog).openDialogs[0].close(recorrencia({ id: 'nova' }));
    await estabilizar();
    await responderSincronizacao(gerados);

    expect(avisos.mostrar).toHaveBeenCalledExactlyOnceWith(mensagem);
    expect(TestBed.inject(DadosStore).versao()).toBe(versao + recargas);
    await responderLista();
  });

  it('vazio_erro_e_recarga__CA_F13_26', async () => {
    await abrir([]);
    expect(texto(pagina().querySelector('app-estado-vazio'))).toContain(
      'Nenhuma recorrência cadastrada.',
    );

    TestBed.inject(DadosStore).incrementar();
    await estabilizar();
    responderCategorias();
    expect(pagina().querySelector('.conteudo.recarregando')).not.toBeNull(); // esmaecido
    listas()[0].flush(
      { erro: { codigo: 'PLANILHA_INDISPONIVEL', mensagem: 'Fora.', detalhes: [] } },
      { status: 503, statusText: 'x' },
    );
    await estabilizar();

    expect(texto(pagina())).toContain('Não foi possível carregar as recorrências.');
    expect(pagina().querySelector('table')).toBeNull();
  });
});
