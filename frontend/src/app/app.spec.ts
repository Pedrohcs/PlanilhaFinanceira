import { BreakpointObserver, BreakpointState } from '@angular/cdk/layout';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatSidenav } from '@angular/material/sidenav';
import { By } from '@angular/platform-browser';
import { provideRouter, Router } from '@angular/router';
import { BehaviorSubject, map, Observable } from 'rxjs';
import { App, ITENS_DE_NAVEGACAO } from './app';
import { routes } from './app.routes';

/** `BreakpointObserver` com a largura da janela controlada pelo teste. */
class BreakpointsFalsos {
  readonly largura = new BehaviorSubject(1280);

  observe(consulta: string): Observable<BreakpointState> {
    return this.largura.pipe(
      map((largura) => {
        const atende = this.atende(consulta, largura);
        return { matches: atende, breakpoints: { [consulta]: atende } };
      }),
    );
  }

  isMatched(consulta: string): boolean {
    return this.atende(consulta, this.largura.value);
  }

  private atende(consulta: string, largura: number): boolean {
    const minimo = Number(/min-width:\s*(\d+)px/.exec(consulta)?.[1]);
    return largura >= minimo;
  }
}

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
    return Array.from(elemento.querySelectorAll<HTMLAnchorElement>('mat-nav-list a'));
  }

  beforeEach(() => {
    breakpoints = new BreakpointsFalsos();
    TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter(routes), { provide: BreakpointObserver, useValue: breakpoints }],
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
    expect(links.map((link) => texto(link, '[matListItemTitle]'))).toEqual([
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
    expect(links.map((link) => link.getAttribute('href'))).toEqual([
      '/resumo',
      '/lancamentos',
      '/historico',
      '/categorias',
      '/recorrencias',
    ]);
    const atuais = links.filter((link) => link.getAttribute('aria-current') === 'page');
    expect(atuais.map((link) => link.getAttribute('href'))).toEqual(['/lancamentos']);
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
    expect(TestBed.inject(Router).url).toBe('/lancamentos');
  });
});
