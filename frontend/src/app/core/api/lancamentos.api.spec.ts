import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';
import { Avisos } from '../avisos/avisos';
import { erroInterceptor, TRATAMENTO_LOCAL } from '../interceptors/erro.interceptor';
import { LancamentoEntrada } from '../models/lancamento';
import { LancamentosApi } from './lancamentos.api';

const ENTRADA: LancamentoEntrada = {
  data: '2026-09-29',
  tipo: 'GASTO',
  descricao: 'Almoço',
  valor: 42.5,
  categoria_id: 'alimentacao',
  forma_pagamento: 'PIX',
  observacao: null,
};

describe('LancamentosApi', () => {
  it('criar_com_e_sem_tratamento_local', async () => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([erroInterceptor])),
        provideHttpClientTesting(),
        { provide: Avisos, useValue: { mostrar: vi.fn() } },
      ],
    });
    const api = TestBed.inject(LancamentosApi);
    const controle = TestBed.inject(HttpTestingController);

    const padrao = firstValueFrom(api.criar(ENTRADA));
    const post = controle.expectOne('/api/lancamentos');
    expect(post.request.method).toBe('POST');
    expect(post.request.body).toEqual(ENTRADA);
    expect(post.request.context.get(TRATAMENTO_LOCAL)).toBe(false);
    post.flush({ ...ENTRADA, id: 'x' });
    await padrao;

    const local = firstValueFrom(api.criar(ENTRADA, { tratamentoLocal: true }));
    const segunda = controle.expectOne('/api/lancamentos');
    expect(segunda.request.context.get(TRATAMENTO_LOCAL)).toBe(true);
    segunda.flush({ ...ENTRADA, id: 'y' });
    await local;
    controle.verify();
  });
});
