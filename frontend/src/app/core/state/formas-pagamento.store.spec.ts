import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { FormasPagamentoStore } from './formas-pagamento.store';

const FORMAS = [
  { codigo: 'PIX', nome: 'Pix' },
  { codigo: 'CREDITO', nome: 'Cartão de crédito' },
];

describe('FormasPagamentoStore', () => {
  let store: FormasPagamentoStore;
  let controle: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    store = TestBed.inject(FormasPagamentoStore);
    controle = TestBed.inject(HttpTestingController);
  });

  afterEach(() => controle.verify());

  it('carrega_uma_vez__F06_3_6', async () => {
    const primeira = store.garantirCarga();
    const segunda = store.garantirCarga();
    controle.expectOne('/api/formas-pagamento').flush(FORMAS);
    await Promise.all([primeira, segunda]);

    await store.garantirCarga();
    controle.expectNone('/api/formas-pagamento');
    expect(store.formas()).toEqual(FORMAS);
  });

  it('tenta_de_novo_se_falhou', async () => {
    const falha = store.garantirCarga();
    controle.expectOne('/api/formas-pagamento').flush('x', { status: 500, statusText: 'x' });
    await falha;
    expect(store.formas()).toEqual([]);

    const nova = store.garantirCarga();
    controle.expectOne('/api/formas-pagamento').flush(FORMAS);
    await nova;
    expect(store.formas()).toHaveLength(2);
  });
});
