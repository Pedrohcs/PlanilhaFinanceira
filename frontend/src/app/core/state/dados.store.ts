import { Injectable, signal } from '@angular/core';

/**
 * Versão dos dados de negócio (SPECS/03 §8.2).
 *
 * Toda escrita bem-sucedida chama `incrementar()`; as páginas leem `versao()`
 * dentro dos seus efeitos de carga e, assim, recarregam sozinhas (`03` §7.1).
 */
@Injectable({ providedIn: 'root' })
export class DadosStore {
  private readonly _versao = signal(0);
  readonly versao = this._versao.asReadonly();

  incrementar(): void {
    this._versao.update((versao) => versao + 1);
  }
}
