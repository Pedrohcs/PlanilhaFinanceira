import { Injector } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { of } from 'rxjs';
import { Avisos } from '../../core/avisos/avisos';
import { DadosStore } from '../../core/state/dados.store';
import { Lancamento } from '../../core/models/lancamento';
import { abrirLancamento, editarLancamento } from './abrir-lancamento';
import { LancamentoFormDialog } from './lancamento-form.dialog';

describe('abrirLancamento', () => {
  let resultado: unknown;
  let abrir: ReturnType<typeof vi.fn>;
  let avisos: { mostrar: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    abrir = vi.fn(() => ({ afterClosed: () => of(resultado) }));
    avisos = { mostrar: vi.fn() };
    TestBed.configureTestingModule({
      providers: [
        { provide: MatDialog, useValue: { open: abrir } },
        { provide: Avisos, useValue: avisos },
      ],
    });
  });

  it('sucesso_avisa_e_incrementa__CA_01_5', async () => {
    resultado = { id: 'novo' };

    await abrirLancamento(TestBed.inject(Injector), 'GASTO');

    expect(abrir).toHaveBeenCalledWith(
      LancamentoFormDialog,
      expect.objectContaining({ data: { tipo: 'GASTO' } }),
    );
    expect(avisos.mostrar).toHaveBeenCalledWith('Gasto registrado.');
    expect(TestBed.inject(DadosStore).versao()).toBe(1);

    await abrirLancamento(TestBed.inject(Injector), 'RECEITA');
    expect(avisos.mostrar).toHaveBeenCalledWith('Receita registrada.');
    expect(TestBed.inject(DadosStore).versao()).toBe(2);
  });

  it('cancelar_nao_avisa_nem_recarrega', async () => {
    resultado = undefined;

    await abrirLancamento(TestBed.inject(Injector), 'GASTO');

    expect(avisos.mostrar).not.toHaveBeenCalled();
    expect(TestBed.inject(DadosStore).versao()).toBe(0);
  });

  it('edicao_avisa_e_incrementa__CA_F08_17', async () => {
    const original = { id: 'g1', tipo: 'GASTO', data: '2026-09-30' } as Lancamento;
    resultado = { ...original, data: '2026-09-12' };

    await editarLancamento(TestBed.inject(Injector), original);

    expect(abrir).toHaveBeenCalledWith(
      LancamentoFormDialog,
      expect.objectContaining({ data: { tipo: 'GASTO', lancamento: original } }),
    );
    expect(avisos.mostrar).toHaveBeenLastCalledWith('Lançamento atualizado.');
    expect(TestBed.inject(DadosStore).versao()).toBe(1);

    resultado = { ...original, data: '2026-10-01' }; // mudou de mês (Q3)
    await editarLancamento(TestBed.inject(Injector), original);
    expect(avisos.mostrar).toHaveBeenLastCalledWith(
      'Lançamento atualizado. Agora ele está em outubro de 2026.',
    );
    expect(TestBed.inject(DadosStore).versao()).toBe(2);

    resultado = undefined; // cancelou
    await editarLancamento(TestBed.inject(Injector), original);
    expect(avisos.mostrar).toHaveBeenCalledTimes(2);
    expect(TestBed.inject(DadosStore).versao()).toBe(2);
  });

  it('aviso_da_parcelada__CA_F12_13', async () => {
    resultado = {
      parcelamento_id: 'par',
      lancamentos: [{ data: '2026-01-15' }, { data: '2026-02-15' }, { data: '2026-03-15' }],
    };

    await abrirLancamento(TestBed.inject(Injector), 'GASTO');

    expect(avisos.mostrar).toHaveBeenCalledWith(
      'Compra parcelada registrada: 3 parcelas, de janeiro de 2026 a março de 2026.',
    );
    expect(TestBed.inject(DadosStore).versao()).toBe(1);
  });
});
