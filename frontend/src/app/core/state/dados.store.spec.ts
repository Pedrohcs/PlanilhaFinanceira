import { TestBed } from '@angular/core/testing';
import { DadosStore } from './dados.store';

describe('DadosStore', () => {
  it('incrementa_versao__CA_F04_22', () => {
    const store = TestBed.inject(DadosStore);
    expect(store.versao()).toBe(0);

    store.incrementar();
    store.incrementar();

    expect(store.versao()).toBe(2);
  });
});
