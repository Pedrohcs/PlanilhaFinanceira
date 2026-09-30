import { Injector } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { of } from 'rxjs';
import { Avisos } from '../../core/avisos/avisos';
import { DadosStore } from '../../core/state/dados.store';
import { abrirLancamento } from './abrir-lancamento';
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
});
