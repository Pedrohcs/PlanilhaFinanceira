import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { contextoDeErro, OpcoesDeEscrita } from '../interceptors/erro.interceptor';
import { Parcelamento, ParcelamentoEntrada } from '../models/parcelamento';

const URL = '/api/parcelamentos';

/** `/api/parcelamentos` (SPECS/03 §6.1; F-12). */
@Injectable({ providedIn: 'root' })
export class ParcelamentosApi {
  private readonly http = inject(HttpClient);

  /** Uma parcela por mês (RN-07), gravadas pelo backend numa única escrita. */
  criar(entrada: ParcelamentoEntrada, opcoes: OpcoesDeEscrita = {}): Observable<Parcelamento> {
    return this.http.post<Parcelamento>(URL, entrada, {
      context: contextoDeErro(opcoes.tratamentoLocal),
    });
  }

  /** Todas as parcelas restantes, em qualquer mês (CA-08.2). */
  excluir(parcelamentoId: string): Observable<void> {
    return this.http.delete<void>(`${URL}/${encodeURIComponent(parcelamentoId)}`);
  }
}
