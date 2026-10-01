import { inject, Injectable } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { RecorrenciasApi } from '../api/recorrencias.api';

/**
 * Sincronização das recorrências (REQ-10; SPECS/03 §7.2, F-13 §3.4): na
 * abertura, no "Tentar novamente" que reconecta e depois de salvar ou
 * reativar uma recorrência (F-13 Q5).
 *
 * Só chama a API e conta: quem chamou monta o aviso (um só por ação) e decide
 * a recarga das telas.
 */
@Injectable({ providedIn: 'root' })
export class SincronizacaoRecorrencias {
  private readonly api = inject(RecorrenciasApi);

  /**
   * Lançamentos gerados, ou `null` se a sincronização falhou — a causa já foi
   * para o banner (503, backend fora) ou para um aviso, pelo interceptor
   * (F-13 §3.4.3).
   */
  async executar(): Promise<number | null> {
    try {
      return (await firstValueFrom(this.api.sincronizar())).lancamentos_gerados;
    } catch {
      return null;
    }
  }
}

/** `1 lançamento recorrente gerado.` / `3 lançamentos recorrentes gerados.` (F-13 §3.4.2). */
export function textoDosGerados(quantidade: number): string {
  return quantidade === 1
    ? '1 lançamento recorrente gerado.'
    : `${quantidade} lançamentos recorrentes gerados.`;
}
