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

describe('LancamentosApi.listar', () => {
  it('listar_com_filtros__F07_6', async () => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    const api = TestBed.inject(LancamentosApi);
    const controle = TestBed.inject(HttpTestingController);
    const vazia = {
      mes: '2026-09',
      itens: [],
      totais: { gastos: 0, receitas: 0, saldo: 0 },
      linhas_ignoradas: 0,
    };

    const sem = firstValueFrom(api.listar('2026-09'));
    controle.expectOne('/api/lancamentos?mes=2026-09').flush(vazia);
    await sem;

    const com = firstValueFrom(
      api.listar('2026-09', { tipo: 'GASTO', categoria_id: 'mercado', forma_pagamento: null }),
    );
    controle.expectOne('/api/lancamentos?mes=2026-09&tipo=GASTO&categoria_id=mercado').flush(vazia);
    await com;
    controle.verify();
  });
});

describe('LancamentosApi.atualizar e excluir', () => {
  it('atualizar_e_excluir__F08', async () => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([erroInterceptor])),
        provideHttpClientTesting(),
        { provide: Avisos, useValue: { mostrar: vi.fn() } },
      ],
    });
    const api = TestBed.inject(LancamentosApi);
    const controle = TestBed.inject(HttpTestingController);

    const atualizado = firstValueFrom(api.atualizar('g 1', ENTRADA, { tratamentoLocal: true }));
    const put = controle.expectOne('/api/lancamentos/g%201');
    expect(put.request.method).toBe('PUT');
    expect(put.request.body).toEqual(ENTRADA);
    expect(put.request.context.get(TRATAMENTO_LOCAL)).toBe(true);
    put.flush({ ...ENTRADA, id: 'g 1' });
    expect((await atualizado).id).toBe('g 1');

    const excluido = firstValueFrom(api.excluir('g1'), { defaultValue: undefined });
    const del = controle.expectOne('/api/lancamentos/g1');
    expect(del.request.method).toBe('DELETE');
    expect(del.request.context.get(TRATAMENTO_LOCAL)).toBe(false);
    del.flush(null, { status: 204, statusText: 'No Content' });
    await excluido;
    controle.verify();
  });
});
