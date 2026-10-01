import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';
import { TRATAMENTO_LOCAL } from '../interceptors/erro.interceptor';
import { RecorrenciaEntrada } from '../models/recorrencia';
import { RecorrenciasApi } from './recorrencias.api';

const ENTRADA: RecorrenciaEntrada = {
  tipo: 'GASTO',
  descricao: 'Streaming',
  valor: 39.9,
  categoria_id: 'assinaturas',
  forma_pagamento: 'CREDITO',
  dia_do_mes: 10,
  mes_inicio: '2026-07',
  mes_fim: null,
};

describe('RecorrenciasApi (SPECS/03 §6.1; F-13)', () => {
  let controle: HttpTestingController;
  let api: RecorrenciasApi;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    controle = TestBed.inject(HttpTestingController);
    api = TestBed.inject(RecorrenciasApi);
  });

  afterEach(() => controle.verify());

  it('listar_criar_atualizar__F13', async () => {
    const lista = firstValueFrom(api.listar());
    const get = controle.expectOne('/api/recorrencias');
    expect(get.request.method).toBe('GET');
    get.flush([]);
    expect(await lista).toEqual([]);

    void firstValueFrom(api.criar(ENTRADA, { tratamentoLocal: true }));
    const post = controle.expectOne('/api/recorrencias');
    expect(post.request.method).toBe('POST');
    expect(post.request.body).toEqual(ENTRADA);
    expect(post.request.context.get(TRATAMENTO_LOCAL)).toBe(true); // 409 no campo (F-06 Q3)
    post.flush({});

    void firstValueFrom(api.atualizar('a b', ENTRADA, { tratamentoLocal: true }));
    const put = controle.expectOne('/api/recorrencias/a%20b');
    expect(put.request.method).toBe('PUT');
    expect(put.request.context.get(TRATAMENTO_LOCAL)).toBe(true);
    put.flush({});
  });

  it('status_e_sincronizar__F13', async () => {
    void firstValueFrom(api.mudarStatus('r1', 'PAUSADA'));
    const patch = controle.expectOne('/api/recorrencias/r1/status');
    expect(patch.request.method).toBe('PATCH');
    expect(patch.request.body).toEqual({ status: 'PAUSADA' });
    expect(patch.request.context.get(TRATAMENTO_LOCAL)).toBe(false);
    patch.flush({});

    const resultado = firstValueFrom(api.sincronizar());
    const post = controle.expectOne('/api/recorrencias/sincronizar');
    expect(post.request.method).toBe('POST');
    post.flush({ lancamentos_gerados: 2, detalhes: [] });
    expect((await resultado).lancamentos_gerados).toBe(2);
  });
});
