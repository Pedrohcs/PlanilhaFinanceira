import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { contextoDeErro, OpcoesDeEscrita } from '../interceptors/erro.interceptor';
import {
  FiltrosLancamentos,
  Lancamento,
  LancamentoEntrada,
  ListaLancamentos,
  SEM_FILTROS,
} from '../models/lancamento';

const URL = '/api/lancamentos';

/** `/api/lancamentos` (SPECS/03 §6.1). */
@Injectable({ providedIn: 'root' })
export class LancamentosApi {
  private readonly http = inject(HttpClient);

  /** Lançamentos do mês com os filtros que estiverem preenchidos (F-07). */
  listar(mes: string, filtros: FiltrosLancamentos = SEM_FILTROS): Observable<ListaLancamentos> {
    let params = new HttpParams().set('mes', mes);
    for (const [chave, valor] of Object.entries(filtros)) {
      if (valor) {
        params = params.set(chave, valor);
      }
    }
    return this.http.get<ListaLancamentos>(URL, { params });
  }

  criar(entrada: LancamentoEntrada, opcoes: OpcoesDeEscrita = {}): Observable<Lancamento> {
    return this.http.post<Lancamento>(URL, entrada, {
      context: contextoDeErro(opcoes.tratamentoLocal),
    });
  }

  /** Qualquer campo (REQ-05); o backend preserva parcela, recorrência e criação. */
  atualizar(
    id: string,
    entrada: LancamentoEntrada,
    opcoes: OpcoesDeEscrita = {},
  ): Observable<Lancamento> {
    return this.http.put<Lancamento>(`${URL}/${encodeURIComponent(id)}`, entrada, {
      context: contextoDeErro(opcoes.tratamentoLocal),
    });
  }

  excluir(id: string): Observable<void> {
    return this.http.delete<void>(`${URL}/${encodeURIComponent(id)}`);
  }
}
