import { TestBed } from '@angular/core/testing';
import { ConexaoStore } from './conexao.store';

describe('ConexaoStore', () => {
  it('comeca_verificando_e_guarda_a_ultima_falha', () => {
    const store = TestBed.inject(ConexaoStore);
    expect(store.estado()).toBe('verificando');
    expect(store.mensagem()).toBeNull();

    store.registrarFalha({ status: 503, codigo: 'A', mensagem: 'primeira', detalhes: [] });
    store.registrarFalha({ status: 503, codigo: 'B', mensagem: 'segunda', detalhes: [] });

    expect(store.estado()).toBe('falha');
    expect(store.mensagem()).toBe('segunda'); // borda 14: um banner, a mais recente

    store.registrarOk();
    expect(store.estado()).toBe('ok');
    expect(store.mensagem()).toBeNull();
  });
});
