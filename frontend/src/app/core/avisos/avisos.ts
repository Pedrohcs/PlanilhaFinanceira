import { inject, Injectable, Injector } from '@angular/core';

/** Duração padrão dos avisos (F-04 §3.3). */
export const DURACAO_AVISO_MS = 5000;

/**
 * Avisos curtos ao usuário (snackbar do Material com "Fechar").
 *
 * O `MatSnackBar` é carregado **sob demanda**: ele arrasta o overlay do CDK
 * (~70 kB) e só é preciso quando algo dá errado ou precisa ser confirmado.
 * Assim o pacote inicial fica abaixo do limite de 500 kB do `angular.json`.
 */
@Injectable({ providedIn: 'root' })
export class Avisos {
  private readonly injetor = inject(Injector);

  async mostrar(mensagem: string, duracaoMs = DURACAO_AVISO_MS): Promise<void> {
    const { MatSnackBar } = await import('@angular/material/snack-bar');
    this.injetor.get(MatSnackBar).open(mensagem, 'Fechar', { duration: duracaoMs });
  }
}
