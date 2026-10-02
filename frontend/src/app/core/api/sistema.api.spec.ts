import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';
import { SistemaApi } from './sistema.api';

describe('SistemaApi (SPECS/03 §6.1)', () => {
  it('recarregar__RN_14', async () => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    const controle = TestBed.inject(HttpTestingController);

    const resposta = firstValueFrom(TestBed.inject(SistemaApi).recarregar(), {
      defaultValue: undefined,
    });
    const pedido = controle.expectOne('/api/sistema/recarregar');
    expect(pedido.request.method).toBe('POST');
    expect(pedido.request.body).toBeNull();
    pedido.flush(null, { status: 204, statusText: 'No Content' });

    await expect(resposta).resolves.toBeNull();
    controle.verify();
  });
});
