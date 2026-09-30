import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';
import { RespostaHealth } from '../models/health';
import { HealthApi } from './health.api';

describe('HealthApi', () => {
  it('consulta_o_health', async () => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    const controle = TestBed.inject(HttpTestingController);
    const corpo: RespostaHealth = {
      status: 'ok',
      planilha: { ok: true, titulo: 'Planilha Financeira', erro: null },
    };

    const resposta = firstValueFrom(TestBed.inject(HealthApi).verificar());
    const requisicao = controle.expectOne('/api/health');
    requisicao.flush(corpo);

    expect(requisicao.request.method).toBe('GET');
    expect(await resposta).toEqual(corpo);
    controle.verify();
  });
});
