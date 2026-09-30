import { Injectable, signal } from '@angular/core';
import { ErroApi } from '../models/erro-api';

export type EstadoConexao = 'verificando' | 'ok' | 'falha';

/**
 * Estado da conexão com o backend e a planilha (SPECS/03 §8.2) — a única
 * fonte do banner de conexão.
 *
 * `'verificando'` é só interno: não há indicador na tela (F-04 Q4). A
 * verificação na abertura e o "Tentar novamente" chegam em T-012.
 */
@Injectable({ providedIn: 'root' })
export class ConexaoStore {
  private readonly _estado = signal<EstadoConexao>('verificando');
  private readonly _mensagem = signal<string | null>(null);

  readonly estado = this._estado.asReadonly();
  /** Mensagem da última falha, exibida sem reescrita (F-04 §3.3). */
  readonly mensagem = this._mensagem.asReadonly();

  /** 503 ou backend fora do ar: o banner aparece com a mensagem mais recente. */
  registrarFalha(erro: ErroApi): void {
    this._mensagem.set(erro.mensagem);
    this._estado.set('falha');
  }

  registrarOk(): void {
    this._mensagem.set(null);
    this._estado.set('ok');
  }
}
