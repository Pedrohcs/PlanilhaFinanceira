import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';
import { umaCategoria } from '../../../testing/categorias';
import { CategoriasApi } from './categorias.api';

describe('CategoriasApi (SPECS/03 §6.1)', () => {
  let api: CategoriasApi;
  let controle: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    api = TestBed.inject(CategoriasApi);
    controle = TestBed.inject(HttpTestingController);
  });

  afterEach(() => controle.verify());

  it('listar_com_e_sem_filtros', async () => {
    const todas = firstValueFrom(api.listar({ incluirInativas: true }));
    const requisicao = controle.expectOne('/api/categorias?incluir_inativas=true');
    expect(requisicao.request.method).toBe('GET');
    requisicao.flush([umaCategoria({ id: 'pet', nome: 'Pet' })]);
    expect((await todas)[0].id).toBe('pet');

    const receitas = firstValueFrom(api.listar({ tipo: 'RECEITA' }));
    controle.expectOne('/api/categorias?tipo=RECEITA').flush([]);
    expect(await receitas).toEqual([]);

    const padrao = firstValueFrom(api.listar());
    controle.expectOne('/api/categorias').flush([]);
    await padrao;
  });

  it('criar_atualizar_excluir', async () => {
    const criada = firstValueFrom(api.criar({ nome: 'Pet', tipo: 'GASTO', cor: '#A1887F' }));
    const post = controle.expectOne('/api/categorias');
    expect(post.request.method).toBe('POST');
    expect(post.request.body).toEqual({ nome: 'Pet', tipo: 'GASTO', cor: '#A1887F' });
    post.flush(umaCategoria({ id: 'pet', nome: 'Pet' }));
    await criada;

    const atualizada = firstValueFrom(
      api.atualizar('contas-da-casa', { nome: 'Casa', cor: '#4FC3F7', ativa: false }),
    );
    const put = controle.expectOne('/api/categorias/contas-da-casa');
    expect(put.request.method).toBe('PUT');
    expect(put.request.body).toEqual({ nome: 'Casa', cor: '#4FC3F7', ativa: false });
    put.flush(umaCategoria({ id: 'contas-da-casa', nome: 'Casa' }));
    await atualizada;

    const excluida = firstValueFrom(api.excluir('pet'));
    const del = controle.expectOne('/api/categorias/pet');
    expect(del.request.method).toBe('DELETE');
    del.flush(null, { status: 204, statusText: 'No Content' });
    await excluida;
  });
});
