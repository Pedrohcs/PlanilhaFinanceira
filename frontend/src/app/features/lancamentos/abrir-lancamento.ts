import { Injector } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { firstValueFrom } from 'rxjs';
import { Avisos } from '../../core/avisos/avisos';
import { TipoLancamento } from '../../core/models/enums';
import { Lancamento } from '../../core/models/lancamento';
import { DadosStore } from '../../core/state/dados.store';
import { mesPorExtenso } from '../../core/utils/mes';
import { DadosFormularioLancamento, LancamentoFormDialog } from './lancamento-form.dialog';

const TAMANHO_DO_DIALOGO = { width: '36rem', maxWidth: 'calc(100vw - 32px)' };

/**
 * Abre "Registrar gasto/receita" e, se salvou, avisa e faz as telas
 * recarregarem (CA-01.2, CA-01.5; `03` §7.1).
 *
 * Carregado **sob demanda** pelo shell: o `MatDialog` vem do `injetor` aqui
 * dentro, para diálogo, formulário, datepicker e select não irem para o
 * pacote inicial (CA-F06.15).
 */
export async function abrirLancamento(injetor: Injector, tipo: TipoLancamento): Promise<void> {
  const salvo = await abrirDialogo(injetor, { tipo });
  if (salvo) {
    void injetor
      .get(Avisos)
      .mostrar(tipo === 'GASTO' ? 'Gasto registrado.' : 'Receita registrada.');
    injetor.get(DadosStore).incrementar();
  }
}

/**
 * Abre o diálogo em modo edição (REQ-05; F-08 §3.4). Se a data mudou de mês,
 * o aviso diz onde o lançamento foi parar (F-08 Q3).
 */
export async function editarLancamento(injetor: Injector, lancamento: Lancamento): Promise<void> {
  const salvo = await abrirDialogo(injetor, { tipo: lancamento.tipo, lancamento });
  if (!salvo) {
    return;
  }
  const mesAntigo = lancamento.data.slice(0, 7);
  const mesNovo = salvo.data.slice(0, 7);
  const mensagem =
    mesNovo === mesAntigo
      ? 'Lançamento atualizado.'
      : `Lançamento atualizado. Agora ele está em ${mesPorExtenso(mesNovo)}.`;
  void injetor.get(Avisos).mostrar(mensagem);
  injetor.get(DadosStore).incrementar();
}

function abrirDialogo(
  injetor: Injector,
  dados: DadosFormularioLancamento,
): Promise<Lancamento | undefined> {
  const referencia = injetor
    .get(MatDialog)
    .open<LancamentoFormDialog, DadosFormularioLancamento, Lancamento>(LancamentoFormDialog, {
      data: dados,
      ...TAMANHO_DO_DIALOGO,
    });
  return firstValueFrom(referencia.afterClosed());
}
