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
});
