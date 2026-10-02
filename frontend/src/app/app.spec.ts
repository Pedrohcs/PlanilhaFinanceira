import { BreakpointObserver } from '@angular/cdk/layout';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { DateAdapter, MAT_DATE_LOCALE, provideNativeDateAdapter } from '@angular/material/core';
import { MatDialog } from '@angular/material/dialog';
import { MatSidenav } from '@angular/material/sidenav';
import { By } from '@angular/platform-browser';
import { provideRouter, Router } from '@angular/router';
import { App, ITENS_DE_NAVEGACAO, MENSAGEM_DADOS_RECARREGADOS } from './app';
import { routes } from './app.routes';
import { Avisos } from './core/avisos/avisos';
import { erroInterceptor } from './core/interceptors/erro.interceptor';
import { MENSAGEM_BACKEND_INDISPONIVEL } from './core/models/erro-api';
import { provideVerificacaoDeConexao } from './core/state/conexao.store';
import { DadosStore } from './core/state/dados.store';
import { AdaptadorDeDataPtBr } from './core/utils/adaptador-de-data';
import { BreakpointsFalsos } from '../testing/breakpoints';
import { provideMaterialParaTestes } from '../testing/material';

describe('App (shell)', () => {
  let breakpoints: BreakpointsFalsos;
  let fixture: ComponentFixture<App>;
  let elemento: HTMLElement;

  async function criar(largura: number): Promise<void> {
    breakpoints.largura.next(largura);
    fixture = TestBed.createComponent(App);
    elemento = fixture.nativeElement as HTMLElement;
    await fixture.whenStable();
  }

  async function mudarLargura(largura: number): Promise<void> {
    breakpoints.largura.next(largura);
    await fixture.whenStable();
  }

  async function navegar(url: string): Promise<void> {
    await TestBed.inject(Router).navigateByUrl(url);
    await fixture.whenStable();
  }

  function botao(rotulo: string): HTMLButtonElement | null {
    return elemento.querySelector<HTMLButtonElement>(`button[aria-label="${rotulo}"]`);
  }

  function menu(): MatSidenav {
    return fixture.debugElement.query(By.directive(MatSidenav)).componentInstance as MatSidenav;
  }

  function linksDaNavegacao(): HTMLAnchorElement[] {
    return Array.from(elemento.querySelectorAll<HTMLAnchorElement>('nav.lista-navegacao a'));
  }

  beforeEach(() => {
    breakpoints = new BreakpointsFalsos();
    TestBed.configureTestingModule({
      imports: [App],
      providers: [
        provideRouter(routes),
        provideNativeDateAdapter(),
        { provide: MAT_DATE_LOCALE, useValue: 'pt-BR' },
        { provide: DateAdapter, useClass: AdaptadorDeDataPtBr },
        provideMaterialParaTestes(),
        { provide: BreakpointObserver, useValue: breakpoints },
        provideHttpClient(withInterceptors([erroInterceptor])),
        provideHttpClientTesting(),
        { provide: Avisos, useValue: { mostrar: vi.fn() } },
      ],
    });
  });

  it('registrar_gasto_visivel_em_todas_as_rotas__CA_01_1', async () => {
    await criar(1280);

    for (const item of ITENS_DE_NAVEGACAO) {
      await navegar(item.rota);

      const gasto = botao('Registrar gasto');
      const receita = botao('Registrar receita');
      expect(gasto?.textContent?.trim()).toBe('Registrar gasto');
      expect(gasto?.getAttribute('matbutton')).toBe('filled'); // primário
      expect(receita?.textContent?.trim()).toBe('Registrar receita');
      expect(receita?.getAttribute('matbutton')).toBe('outlined');
    }
  });

  it('navegacao_com_5_itens_e_rota_ativa__CA_F04_4', async () => {
    await criar(1280);
    await navegar('/lancamentos');

    const links = linksDaNavegacao();
    const texto = (link: HTMLAnchorElement, seletor: string) =>
      link.querySelector(seletor)?.textContent?.trim();
    expect(links.map((link) => texto(link, '.rotulo-navegacao'))).toEqual([
      'Resumo',
      'Lançamentos',
      'Histórico',
      'Categorias',
      'Recorrências',
    ]);
    expect(links.map((link) => texto(link, 'mat-icon'))).toEqual([
      'dashboard',
      'receipt_long',
      'bar_chart',
      'sell',
      'event_repeat',
    ]);
    expect(links.map((link) => link.getAttribute('href')?.split('?')[0])).toEqual([
      '/resumo',
      '/lancamentos',
      '/historico',
      '/categorias',
      '/recorrencias',
    ]);
    const atuais = links.filter((link) => link.getAttribute('aria-current') === 'page');
    expect(atuais.map((link) => link.getAttribute('href')?.split('?')[0])).toEqual([
      '/lancamentos',
    ]);
  });

  it('item_ativo_ignora_o_mes_na_url__CA_F04_4', async () => {
    await criar(1280);
    await navegar('/resumo'); // app recém-aberto: sem ?mes=, link com ?mes=

    const atuais = linksDaNavegacao().filter((l) => l.getAttribute('aria-current') === 'page');
    expect(atuais.map((link) => link.textContent)).toHaveLength(1);
    expect(atuais[0].getAttribute('href')?.startsWith('/resumo?mes=')).toBe(true);
  });

  it('mes_mantido_entre_resumo_e_lancamentos__CA_04_2', async () => {
    await criar(1280);
    await navegar('/resumo?mes=2026-05');
    const router = TestBed.inject(Router);

    // Borda 8: o link de Lançamentos leva o mês selecionado.
    expect(linksDaNavegacao()[1].getAttribute('href')).toBe('/lancamentos?mes=2026-05');
    linksDaNavegacao()[1].click();
    await fixture.whenStable();
    expect(router.url).toBe('/lancamentos?mes=2026-05');

    // Borda 9: passando por uma tela sem mês, o Resumo volta no mesmo mês.
    expect(linksDaNavegacao()[3].getAttribute('href')).toBe('/categorias');
    linksDaNavegacao()[3].click();
    await fixture.whenStable();
    linksDaNavegacao()[0].click();
    await fixture.whenStable();
    expect(router.url).toBe('/resumo?mes=2026-05');
  });

  it('layout_por_largura__CA_F04_7', async () => {
    // ≥ 960 px: navegação fixa, sem ☰, título e rótulos completos.
    await criar(960);
    expect(menu().mode).toBe('side');
    expect(menu().opened).toBe(true);
    expect(botao('Abrir menu')).toBeNull();
    expect(elemento.querySelector('.titulo')?.textContent).toBe('Planilha Financeira');

    // 600–959 px: navegação recolhida, abre por cima pelo ☰; título e rótulos completos.
    await mudarLargura(959);
    expect(menu().mode).toBe('over');
    expect(menu().opened).toBe(false);
    expect(botao('Abrir menu')).not.toBeNull();
    await mudarLargura(600);
    expect(elemento.querySelector('.titulo')).not.toBeNull();
    expect(botao('Registrar gasto')?.textContent?.trim()).toBe('Registrar gasto');

    // < 600 px (360 px): sem título; "+ Gasto" / "+ Receita" com aria-label completo.
    await mudarLargura(360);
    expect(elemento.querySelector('.titulo')).toBeNull();
    expect(botao('Registrar gasto')?.textContent?.replace(/\s+/g, ' ').trim()).toBe('add Gasto');
    expect(botao('Registrar receita')?.textContent?.replace(/\s+/g, ' ').trim()).toBe(
      'add Receita',
    );
    expect(botao('Abrir menu')).not.toBeNull();
  });

  it('menu_sobreposto_fecha_ao_escolher_item__CA_F04_7', async () => {
    await criar(800);

    botao('Abrir menu')?.click();
    await fixture.whenStable();
    expect(menu().opened).toBe(true);

    linksDaNavegacao()[2].click();
    await fixture.whenStable();

    expect(menu().opened).toBe(false);
    expect(TestBed.inject(Router).url).toBe('/historico');
  });

  it('menu_fixo_continua_aberto_ao_escolher_item', async () => {
    await criar(1280);

    linksDaNavegacao()[1].click();
    await fixture.whenStable();

    expect(menu().opened).toBe(true);
    expect(TestBed.inject(Router).url.split('?')[0]).toBe('/lancamentos');
  });

  function banner(): HTMLElement | null {
    return elemento.querySelector<HTMLElement>('app-banner-conexao [role="alert"]');
  }

  it('backend_desligado_nao_trava_o_app__CA_F04_29', async () => {
    TestBed.configureTestingModule({ providers: [provideVerificacaoDeConexao()] });
    await criar(1280);
    await navegar('/resumo');

    // A abertura não esperou o health: shell e página já estão na tela.
    expect(elemento.querySelector('h1')?.textContent).toBe('Resumo');
    expect(botao('Registrar gasto')).not.toBeNull();
    expect(banner()).toBeNull();

    // O proxy do `ng serve` responde 504 sem o envelope (borda 13).
    TestBed.inject(HttpTestingController)
      .expectOne('/api/health')
      .flush('Error occurred while trying to proxy', { status: 504, statusText: 'x' });
    await new Promise((resolver) => setTimeout(resolver));
    await fixture.whenStable();

    expect(banner()?.textContent).toContain(MENSAGEM_BACKEND_INDISPONIVEL);
    expect(banner()?.textContent).toContain('Tentar novamente');
    await navegar('/categorias'); // continua navegável
    expect(elemento.querySelector('h1')?.textContent).toBe('Categorias');
  });

  it('volta_do_banner_apos_503__borda_16', async () => {
    TestBed.configureTestingModule({ providers: [provideVerificacaoDeConexao()] });
    await criar(1280);
    const controle = TestBed.inject(HttpTestingController);
    controle.expectOne('/api/health').flush({
      status: 'ok',
      planilha: { ok: true, titulo: 'Planilha Financeira', erro: null },
    });
    await new Promise((resolver) => setTimeout(resolver));
    await fixture.whenStable();
    expect(banner()).toBeNull(); // CA-F04.24

    // Uma chamada de negócio qualquer recebe 503 depois.
    TestBed.inject(HttpClient)
      .get('/api/lancamentos')
      .subscribe({ error: () => undefined });
    controle.expectOne('/api/lancamentos').flush(
      {
        erro: {
          codigo: 'PLANILHA_INDISPONIVEL',
          mensagem: 'Google Sheets indisponível.',
          detalhes: [],
        },
      },
      { status: 503, statusText: 'x' },
    );
    await fixture.whenStable();

    expect(banner()?.textContent).toContain('Google Sheets indisponível.');
  });

  it('botoes_abrem_o_dialogo_do_tipo__CA_01_1', async () => {
    await criar(1280);

    for (const [rotulo, titulo] of [
      ['Registrar gasto', 'Registrar gasto'],
      ['Registrar receita', 'Registrar receita'],
    ]) {
      botao(rotulo)?.click();
      // O código do diálogo é baixado sob demanda (`import()`): espera ele aparecer.
      await vi.waitFor(() => {
        expect(document.querySelector('mat-dialog-container h2')?.textContent).toBe(titulo);
      });
      TestBed.inject(MatDialog).closeAll();
      await vi.waitFor(() => {
        expect(TestBed.inject(MatDialog).openDialogs).toHaveLength(0);
      });
      await fixture.whenStable();
    }
  });

  it('recarregar_dados__CA_F14_12', async () => {
    await criar(360); // em todas as larguras, inclusive a barra curta (Q1)
    const controle = TestBed.inject(HttpTestingController);
    const dados = TestBed.inject(DadosStore);
    const avisos = TestBed.inject(Avisos);
    const recarregar = botao('Recarregar dados da planilha');
    expect(recarregar?.getAttribute('title')).toBe('Recarregar dados da planilha');
    expect(recarregar?.textContent?.trim()).toBe('refresh');
    const versaoAntes = dados.versao();

    recarregar?.click();
    await fixture.whenStable();
    expect(recarregar?.disabled).toBe(true);
    recarregar?.click(); // borda 6: duplo clique faz um pedido só
    const pedido = controle.expectOne('/api/sistema/recarregar');
    expect(pedido.request.method).toBe('POST');
    expect(dados.versao()).toBe(versaoAntes);

    pedido.flush(null, { status: 204, statusText: 'No Content' });
    await vi.waitFor(() => expect(recarregar?.disabled).toBe(false));
    expect(dados.versao()).toBe(versaoAntes + 1);
    expect(avisos.mostrar).toHaveBeenCalledExactlyOnceWith(MENSAGEM_DADOS_RECARREGADOS);
    controle.verify();
  });

  it('recarregar_com_backend_fora_mostra_banner_sem_aviso__CA_F14_12', async () => {
    await criar(1280);
    const controle = TestBed.inject(HttpTestingController);
    const dados = TestBed.inject(DadosStore);
    const avisos = TestBed.inject(Avisos);
    const versaoAntes = dados.versao();

    botao('Recarregar dados da planilha')?.click();
    controle.expectOne('/api/sistema/recarregar').error(new ProgressEvent('error'));
    await vi.waitFor(() => expect(botao('Recarregar dados da planilha')?.disabled).toBe(false));
    await fixture.whenStable();

    expect(banner()?.textContent).toContain(MENSAGEM_BACKEND_INDISPONIVEL);
    expect(avisos.mostrar).not.toHaveBeenCalled();
    expect(dados.versao()).toBe(versaoAntes);
    // Com o banner aberto, o botão continua disponível (F-14 §3.3.2).
    botao('Recarregar dados da planilha')?.click();
    controle.expectOne('/api/sistema/recarregar').flush(null, { status: 204, statusText: 'x' });
    await vi.waitFor(() =>
      expect(avisos.mostrar).toHaveBeenCalledWith(MENSAGEM_DADOS_RECARREGADOS),
    );
    controle.verify();
  });
});
