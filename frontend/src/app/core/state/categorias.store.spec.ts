import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { umaCategoria } from '../../../testing/categorias';
import { CategoriasStore } from './categorias.store';
import { DadosStore } from './dados.store';

const LISTA = [
  umaCategoria({ id: 'mercado', nome: 'Mercado' }),
  umaCategoria({ id: 'velha', nome: 'Velha', ativa: false }),
  umaCategoria({ id: 'salario', nome: 'Salário', tipo: 'RECEITA' }),
];
const URL = '/api/categorias?incluir_inativas=true';

describe('CategoriasStore', () => {
  let store: CategoriasStore;
  let controle: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    store = TestBed.inject(CategoriasStore);
    controle = TestBed.inject(HttpTestingController);
  });

  afterEach(() => controle.verify());

  async function responder(lista = LISTA): Promise<void> {
    controle.expectOne(URL).flush(lista);
    await new Promise((resolver) => setTimeout(resolver));
  }

  it('carrega_uma_vez_e_recarrega_apos_escrita__CA_F05_19', async () => {
    TestBed.tick();
    controle.expectNone(URL); // ninguém pediu ainda: não carrega

    const primeira = store.garantirCarga();
    expect(store.carregando()).toBe(true);
    TestBed.tick(); // 1ª execução do efeito depois da carga: não pode duplicar
    await responder();
    await primeira;
    expect(store.todas().map((c) => c.id)).toEqual(['mercado', 'velha', 'salario']);

    await store.garantirCarga(); // já carregado: nenhuma requisição
    controle.expectNone(URL);

    TestBed.inject(DadosStore).incrementar(); // uma escrita aconteceu
    TestBed.tick();
    await responder([...LISTA, umaCategoria({ id: 'pet', nome: 'Pet' })]);
    expect(store.todas()).toHaveLength(4);
  });

  it('ativas_por_tipo__CA_11_4', async () => {
    const carga = store.garantirCarga();
    await responder();
    await carga;

    expect(store.porTipo('GASTO').map((c) => c.id)).toEqual(['mercado', 'velha']);
    expect(store.ativasPorTipo('GASTO').map((c) => c.id)).toEqual(['mercado']);
    expect(store.ativasPorTipo('RECEITA').map((c) => c.id)).toEqual(['salario']);
  });

  it('falha_na_carga_marca_erro', async () => {
    const carga = store.garantirCarga();
    controle.expectOne(URL).flush('falhou', { status: 500, statusText: 'x' });
    await carga;

    expect(store.erro()).toBe(true);
    expect(store.carregando()).toBe(false);
    expect(store.todas()).toEqual([]);
  });
});
