import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';
import { ResumoApi } from './resumo.api';

describe('ResumoApi (SPECS/03 §6.1)', () => {
  it('mensal__F09', async () => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    const controle = TestBed.inject(HttpTestingController);

    const resumo = firstValueFrom(TestBed.inject(ResumoApi).mensal('2026-09'));
    const pedido = controle.expectOne('/api/resumo/mensal?mes=2026-09');
    expect(pedido.request.method).toBe('GET');
    pedido.flush({ mes: '2026-09' });

    expect((await resumo).mes).toBe('2026-09');
    controle.verify();
  });

  it('historico_com_e_sem_periodo__F11', async () => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    const controle = TestBed.inject(HttpTestingController);
    const api = TestBed.inject(ResumoApi);

    const padrao = firstValueFrom(api.historico());
    const semPeriodo = controle.expectOne('/api/resumo/historico');
    expect(semPeriodo.request.method).toBe('GET');
    expect(semPeriodo.request.params.keys()).toEqual([]);
    semPeriodo.flush({ inicio: '2025-11', fim: '2026-10' });
    expect((await padrao).inicio).toBe('2025-11');

    const escolhido = firstValueFrom(api.historico({ inicio: '2026-01', fim: '2026-06' }));
    controle.expectOne('/api/resumo/historico?inicio=2026-01&fim=2026-06').flush({
      inicio: '2026-01',
      fim: '2026-06',
    });
    expect((await escolhido).fim).toBe('2026-06');
    controle.verify();
  });
});
