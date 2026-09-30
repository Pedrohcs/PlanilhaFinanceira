import { inject, Injectable, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { FormasPagamentoApi } from '../api/formas-pagamento.api';
import { FormaPagamentoOpcao } from '../models/lancamento';

/**
 * Formas de pagamento (RN-05). A lista é fixa (P-01): carrega uma vez e só
 * tenta de novo se a carga anterior falhou.
 */
@Injectable({ providedIn: 'root' })
export class FormasPagamentoStore {
  private readonly api = inject(FormasPagamentoApi);
  private readonly _formas = signal<FormaPagamentoOpcao[]>([]);
  private carga: Promise<void> | null = null;

  readonly formas = this._formas.asReadonly();

  garantirCarga(): Promise<void> {
    this.carga ??= firstValueFrom(this.api.listar()).then(
      (formas) => this._formas.set(formas),
      () => {
        this.carga = null; // falhou: a próxima abertura tenta de novo
      },
    );
    return this.carga;
  }
}
