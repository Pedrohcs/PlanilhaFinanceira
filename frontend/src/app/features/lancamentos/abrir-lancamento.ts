import { Injector } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { firstValueFrom } from 'rxjs';
import { Avisos } from '../../core/avisos/avisos';
import { TipoLancamento } from '../../core/models/enums';
import { Lancamento } from '../../core/models/lancamento';
import { DadosStore } from '../../core/state/dados.store';
import { DadosFormularioLancamento, LancamentoFormDialog } from './lancamento-form.dialog';

/**
 * Abre "Registrar gasto/receita" e, se salvou, avisa e faz as telas
 * recarregarem (CA-01.2, CA-01.5; `03` §7.1).
 *
 * Carregado **sob demanda** pelo shell: o `MatDialog` vem do `injetor` aqui
 * dentro, para diálogo, formulário, datepicker e select não irem para o
 * pacote inicial (CA-F06.15).
 */
export async function abrirLancamento(injetor: Injector, tipo: TipoLancamento): Promise<void> {
  const referencia = injetor
    .get(MatDialog)
    .open<LancamentoFormDialog, DadosFormularioLancamento, Lancamento>(LancamentoFormDialog, {
      data: { tipo },
      width: '36rem',
      maxWidth: 'calc(100vw - 32px)',
    });
  const salvo = await firstValueFrom(referencia.afterClosed());
  if (salvo) {
    void injetor
      .get(Avisos)
      .mostrar(tipo === 'GASTO' ? 'Gasto registrado.' : 'Receita registrada.');
    injetor.get(DadosStore).incrementar();
  }
}
