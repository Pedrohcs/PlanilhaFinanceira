import { Location } from '@angular/common';
import { TestBed } from '@angular/core/testing';
import { MAT_DATE_LOCALE, provideNativeDateAdapter } from '@angular/material/core';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { routes } from '../../app.routes';
import { MesSelecionadoStore } from './mes-selecionado.store';

describe('MesSelecionadoStore', () => {
  let harness: RouterTestingHarness;
  let store: MesSelecionadoStore;

  beforeEach(async () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date(2026, 8, 30, 10, 0)); // "hoje" = setembro de 2026
    TestBed.configureTestingModule({
      providers: [
        provideRouter(routes),
        provideNativeDateAdapter(),
        { provide: MAT_DATE_LOCALE, useValue: 'pt-BR' },
      ],
    });
    store = TestBed.inject(MesSelecionadoStore);
    harness = await RouterTestingHarness.create();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  async function navegar(url: string): Promise<void> {
    await harness.navigateByUrl(url);
    await harness.fixture.whenStable();
  }

  it('mes_corrente_por_padrao__CA_04_1', async () => {
    await navegar('/resumo');
    expect(store.mes()).toBe('2026-09');

    await navegar('/lancamentos');
    expect(store.mes()).toBe('2026-09');
  });

  it('le_o_mes_da_url__REQ_04', async () => {
    await navegar('/lancamentos?mes=2025-03');

    expect(store.mes()).toBe('2025-03');
  });

  it('aceita_mes_antigo__borda_5', async () => {
    await navegar('/resumo?mes=1999-01');

    expect(store.mes()).toBe('1999-01');
  });

  for (const invalido of ['2026-13', 'abc', '']) {
    it(`mes_invalido_na_url_vira_corrente__CA_F04_18 [${invalido || 'vazio'}]`, async () => {
      const router = TestBed.inject(Router);
      const navegarPorUrl = vi.spyOn(router, 'navigateByUrl');

      await navegar(`/lancamentos?mes=${invalido}`);

      expect(store.mes()).toBe('2026-09');
      expect(router.url).toBe('/lancamentos?mes=2026-09');
      // A correção substitui a entrada do histórico (sem "voltar" para o mês inválido).
      const correcao = navegarPorUrl.mock.calls.at(-1);
      expect(correcao?.[1]).toEqual({ replaceUrl: true });
    });
  }

  it('definir_atualiza_a_url_sem_empilhar_historico__F04_3_4', async () => {
    await navegar('/resumo?mes=2026-09');
    const location = TestBed.inject(Location);
    const router = TestBed.inject(Router);
    const navegarPorUrl = vi.spyOn(router, 'navigateByUrl');

    store.definir('2026-10');
    await harness.fixture.whenStable();

    expect(store.mes()).toBe('2026-10');
    expect(location.path()).toBe('/resumo?mes=2026-10');
    expect(navegarPorUrl.mock.calls.at(-1)?.[1]).toEqual({ replaceUrl: true });
    expect(() => store.definir('2026-13')).toThrow();
  });

  it('telas_sem_mes_nao_mexem_no_mes', async () => {
    await navegar('/resumo?mes=2025-03');
    await navegar('/categorias');
    await navegar('/historico?mes=abc');

    expect(store.mes()).toBe('2025-03');
    expect(TestBed.inject(Router).url).toBe('/historico?mes=abc');
  });
});
