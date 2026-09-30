import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';
import { Avisos } from '../avisos/avisos';
import { erroInterceptor, TRATAMENTO_LOCAL } from '../interceptors/erro.interceptor';
import { ParcelamentoEntrada } from '../models/parcelamento';
import { ParcelamentosApi } from './parcelamentos.api';

const ENTRADA: ParcelamentoEntrada = {
  data: '2026-01-15',
  descricao: 'Geladeira',
  valor_total: 1000,
  parcelas: 3,
  categoria_id: 'moradia',
  forma_pagamento: 'CREDITO',
  observacao: null,
};

describe('ParcelamentosApi', () => {
  it('criar_e_excluir__F12', async () => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([erroInterceptor])),
        provideHttpClientTesting(),
        { provide: Avisos, useValue: { mostrar: vi.fn() } },
      ],
    });
    const api = TestBed.inject(ParcelamentosApi);
    const controle = TestBed.inject(HttpTestingController);

    const criado = firstValueFrom(api.criar(ENTRADA, { tratamentoLocal: true }));
    const post = controle.expectOne('/api/parcelamentos');
    expect(post.request.method).toBe('POST');
    expect(post.request.body).toEqual(ENTRADA);
    expect(post.request.context.get(TRATAMENTO_LOCAL)).toBe(true);
    post.flush({ parcelamento_id: 'par', lancamentos: [] });
    expect((await criado).parcelamento_id).toBe('par');

    const excluido = firstValueFrom(api.excluir('a b'), { defaultValue: undefined });
    const del = controle.expectOne('/api/parcelamentos/a%20b');
    expect(del.request.method).toBe('DELETE');
    expect(del.request.context.get(TRATAMENTO_LOCAL)).toBe(false);
    del.flush(null, { status: 204, statusText: 'No Content' });
    await excluido;
    controle.verify();
  });
});
