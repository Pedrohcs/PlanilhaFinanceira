import { TestBed } from '@angular/core/testing';
import {
  MAT_DATE_LOCALE,
  MATERIAL_ANIMATIONS,
  provideNativeDateAdapter,
} from '@angular/material/core';
import { MatDatepicker } from '@angular/material/datepicker';
import { By } from '@angular/platform-browser';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { routes } from '../../../app.routes';
import { MesSelecionadoStore } from '../../../core/state/mes-selecionado.store';

describe('SeletorMes', () => {
  let harness: RouterTestingHarness;

  beforeEach(async () => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter(routes),
        provideNativeDateAdapter(),
        { provide: MAT_DATE_LOCALE, useValue: 'pt-BR' },
        // O jsdom não dispara fim de animação CSS: sem isto o calendário não conclui o fechar.
        { provide: MATERIAL_ANIMATIONS, useValue: { animationsDisabled: true } },
      ],
    });
    harness = await RouterTestingHarness.create();
  });

  async function abrir(url: string): Promise<void> {
    await harness.navigateByUrl(url);
    await harness.fixture.whenStable();
  }

  function botao(rotulo: string): HTMLButtonElement {
    const encontrado = harness.routeNativeElement?.querySelector<HTMLButtonElement>(
      `app-seletor-mes button[aria-label="${rotulo}"]`,
    );
    if (!encontrado) {
      throw new Error(`botão "${rotulo}" não encontrado`);
    }
    return encontrado;
  }

  async function clicar(rotulo: string): Promise<void> {
    botao(rotulo).click();
    await harness.fixture.whenStable();
  }

  function calendario(): MatDatepicker<Date> {
    return harness.fixture.debugElement.query(By.directive(MatDatepicker))
      .componentInstance as MatDatepicker<Date>;
  }

  it('botoes_trocam_o_mes_e_a_url__CA_F04_19', async () => {
    await abrir('/resumo?mes=2026-12');
    expect(botao('Escolher mês').textContent?.trim()).toBe('dezembro de 2026'); // CA-F04.20

    await clicar('Próximo mês');
    expect(botao('Escolher mês').textContent?.trim()).toBe('janeiro de 2027');
    expect(TestBed.inject(Router).url).toBe('/resumo?mes=2027-01');

    await clicar('Mês anterior');
    expect(botao('Escolher mês').textContent?.trim()).toBe('dezembro de 2026');
    expect(TestBed.inject(Router).url).toBe('/resumo?mes=2026-12');
  });

  it('datepicker_escolhe_mes_e_fecha__CA_F04_31', async () => {
    await abrir('/lancamentos?mes=2026-09');
    const picker = calendario();
    expect(picker.startView).toBe('multi-year'); // anos → meses, sem dias

    await clicar('Escolher mês');
    expect(picker.opened).toBe(true);

    harness.fixture.debugElement
      .query(By.directive(MatDatepicker))
      .triggerEventHandler('monthSelected', new Date(2025, 2, 1));
    await harness.fixture.whenStable();

    expect(picker.opened).toBe(false);
    expect(botao('Escolher mês').textContent?.trim()).toBe('março de 2025');
    expect(TestBed.inject(Router).url).toBe('/lancamentos?mes=2025-03');
    expect(TestBed.inject(MesSelecionadoStore).mes()).toBe('2025-03');
  });

  it('fechar_sem_escolher_nao_muda_o_mes__borda_21', async () => {
    await abrir('/lancamentos?mes=2026-09');
    await clicar('Escolher mês');

    calendario().close(); // o que o Esc faz
    await harness.fixture.whenStable();

    expect(TestBed.inject(MesSelecionadoStore).mes()).toBe('2026-09');
    expect(TestBed.inject(Router).url).toBe('/lancamentos?mes=2026-09');
  });

  it('calendario_abre_no_mes_selecionado', async () => {
    await abrir('/resumo?mes=2025-03');

    expect(calendario().datepickerInput.getStartValue()).toEqual(new Date(2025, 2, 1));
  });
});
