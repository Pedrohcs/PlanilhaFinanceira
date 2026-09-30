import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule } from '@angular/material/dialog';
import { map, Observable } from 'rxjs';

export interface DadosConfirmacao {
  titulo: string;
  mensagem: string;
  /** Rótulo do botão que confirma, ex.: "Excluir". */
  textoConfirmar: string;
}

/**
 * Pergunta de confirmação (F-04 §3.5.3; usada por CA-06.1 em T-020).
 *
 * O foco começa em "Cancelar", para Enter não excluir nada por engano.
 * Abra com `confirmar()`, que já devolve `true`/`false`.
 */
@Component({
  selector: 'app-confirmacao-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatButtonModule, MatDialogModule],
  template: `
    <h2 mat-dialog-title>{{ dados.titulo }}</h2>
    <mat-dialog-content>{{ dados.mensagem }}</mat-dialog-content>
    <mat-dialog-actions align="end">
      <button matButton type="button" [mat-dialog-close]="false" cdkFocusInitial>Cancelar</button>
      <button matButton="filled" type="button" [mat-dialog-close]="true">
        {{ dados.textoConfirmar }}
      </button>
    </mat-dialog-actions>
  `,
})
export class ConfirmacaoDialog {
  protected readonly dados = inject<DadosConfirmacao>(MAT_DIALOG_DATA);
}

/** Abre a confirmação; Esc e clique fora contam como "não" (`false`). */
export function confirmar(dialog: MatDialog, dados: DadosConfirmacao): Observable<boolean> {
  return dialog
    .open<ConfirmacaoDialog, DadosConfirmacao, boolean>(ConfirmacaoDialog, { data: dados })
    .afterClosed()
    .pipe(map((resposta) => resposta === true));
}
