import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { contextoDeErro, OpcoesDeEscrita } from '../interceptors/erro.interceptor';
import { Lancamento, LancamentoEntrada } from '../models/lancamento';

const URL = '/api/lancamentos';

/** `/api/lancamentos` (SPECS/03 §6.1). Listar/editar/excluir chegam em F-07 e F-08. */
@Injectable({ providedIn: 'root' })
export class LancamentosApi {
  private readonly http = inject(HttpClient);

  criar(entrada: LancamentoEntrada, opcoes: OpcoesDeEscrita = {}): Observable<Lancamento> {
    return this.http.post<Lancamento>(URL, entrada, {
      context: contextoDeErro(opcoes.tratamentoLocal),
    });
  }
}
