import { ApplicationRef } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { firstValueFrom } from 'rxjs';
import { provideMaterialParaTestes } from '../../../../testing/material';
import { confirmar, DadosConfirmacao } from './confirmacao.dialog';

const DADOS: DadosConfirmacao = {
  titulo: 'Excluir lançamento?',
  mensagem: 'Almoço — R$ 42,50',
  textoConfirmar: 'Excluir',
};

describe('ConfirmacaoDialog', () => {
  let dialog: MatDialog;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideMaterialParaTestes()],
    });
    dialog = TestBed.inject(MatDialog);
  });

  afterEach(() => dialog.closeAll());

  /** Abre e espera renderizar; a resposta vem embrulhada para o `await` não esperar o fechamento. */
  async function abrir(): Promise<{ resposta: Promise<boolean> }> {
    const resposta = firstValueFrom(confirmar(dialog, DADOS));
    await TestBed.inject(ApplicationRef).whenStable();
    return { resposta };
  }

  function botaoDoDialogo(texto: string): HTMLButtonElement {
    const botoes = Array.from(
      document.querySelectorAll<HTMLButtonElement>('mat-dialog-actions button'),
    );
    const botao = botoes.find((b) => b.textContent?.trim() === texto);
    if (!botao) {
      throw new Error(`botão "${texto}" não encontrado`);
    }
    return botao;
  }

  it('confirma_cancela_e_foca_cancelar__CA_F04_21', async () => {
    const { resposta: primeira } = await abrir();
    expect(document.querySelector('h2')?.textContent).toBe(DADOS.titulo);
    expect(document.querySelector('mat-dialog-content')?.textContent?.trim()).toBe(DADOS.mensagem);
    expect(document.activeElement?.textContent?.trim()).toBe('Cancelar');

    botaoDoDialogo('Excluir').click();
    expect(await primeira).toBe(true);

    const { resposta: segunda } = await abrir();
    botaoDoDialogo('Cancelar').click();
    expect(await segunda).toBe(false);
  });

  it('esc_ou_clique_fora_contam_como_nao__CA_F04_21', async () => {
    const { resposta } = await abrir();

    dialog.openDialogs[0].close(); // Esc/backdrop fecham sem valor

    expect(await resposta).toBe(false);
  });
});
