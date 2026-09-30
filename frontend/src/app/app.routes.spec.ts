import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { MAT_DATE_LOCALE, provideNativeDateAdapter } from '@angular/material/core';
import { Title } from '@angular/platform-browser';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { routes } from './app.routes';

/** `provisoria`: página ainda placeholder de F-04 (vira `false` quando a tela real chega). */
const PAGINAS = [
  { url: '/resumo', titulo: 'Resumo', provisoria: false },
  { url: '/lancamentos', titulo: 'Lançamentos', provisoria: false },
  { url: '/historico', titulo: 'Histórico', provisoria: true },
  { url: '/categorias', titulo: 'Categorias', provisoria: false },
  { url: '/recorrencias', titulo: 'Recorrências', provisoria: true },
];

describe('rotas (SPECS/03 §8.1)', () => {
  let harness: RouterTestingHarness;

  beforeEach(async () => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter(routes),
        provideHttpClient(),
        provideHttpClientTesting(),
        provideNativeDateAdapter(),
        { provide: MAT_DATE_LOCALE, useValue: 'pt-BR' },
      ],
    });
    harness = await RouterTestingHarness.create();
  });

  function tituloDaPagina(): string | undefined {
    return harness.routeNativeElement?.querySelector('h1')?.textContent?.trim();
  }

  it('redireciona_raiz_para_resumo__CA_F04_1', async () => {
    await harness.navigateByUrl('/');

    expect(TestBed.inject(Router).url).toBe('/resumo');
    expect(tituloDaPagina()).toBe('Resumo');
  });

  it('abre_as_5_paginas_sob_demanda__CA_F04_2', async () => {
    for (const pagina of PAGINAS) {
      await harness.navigateByUrl(pagina.url);

      expect(TestBed.inject(Router).url).toBe(pagina.url);
      expect(tituloDaPagina()).toBe(pagina.titulo);
      expect(
        harness.routeNativeElement?.textContent?.includes('Esta tela ainda está em construção.'),
      ).toBe(pagina.provisoria);
    }

    const paginas = routes.filter((rota) => rota.path && rota.path !== '**');
    expect(paginas.map((rota) => `/${rota.path}`)).toEqual(PAGINAS.map((pagina) => pagina.url));
    for (const rota of paginas) {
      expect(rota.loadComponent).toBeTypeOf('function');
      expect(rota.component).toBeUndefined();
    }
  });

  it('titulo_da_aba_por_rota__CA_F04_5', async () => {
    for (const pagina of PAGINAS) {
      await harness.navigateByUrl(pagina.url);

      expect(TestBed.inject(Title).getTitle()).toBe(`${pagina.titulo} · Planilha Financeira`);
    }
  });

  it('rota_desconhecida_vai_para_resumo__CA_F04_6', async () => {
    await harness.navigateByUrl('/xyz/abc');

    expect(TestBed.inject(Router).url).toBe('/resumo');
    expect(tituloDaPagina()).toBe('Resumo');
  });
});
