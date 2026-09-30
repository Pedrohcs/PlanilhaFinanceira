import { TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Avisos, DURACAO_AVISO_MS } from './avisos';

describe('Avisos', () => {
  it('mostra_snackbar_com_fechar_carregado_sob_demanda', async () => {
    const abrir = vi.fn();
    TestBed.configureTestingModule({
      providers: [{ provide: MatSnackBar, useValue: { open: abrir } }],
    });

    await TestBed.inject(Avisos).mostrar('Não foi possível salvar.');

    expect(abrir).toHaveBeenCalledWith('Não foi possível salvar.', 'Fechar', {
      duration: DURACAO_AVISO_MS,
    });
  });
});
