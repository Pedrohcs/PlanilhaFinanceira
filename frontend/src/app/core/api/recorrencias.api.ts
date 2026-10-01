import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { contextoDeErro, OpcoesDeEscrita } from '../interceptors/erro.interceptor';
import { StatusRecorrencia } from '../models/enums';
import { Recorrencia, RecorrenciaEntrada, Sincronizacao } from '../models/recorrencia';

const URL = '/api/recorrencias';

/** `/api/recorrencias` (SPECS/03 §6.1; F-13). */
@Injectable({ providedIn: 'root' })
export class RecorrenciasApi {
  private readonly http = inject(HttpClient);

  /** Ativas, pausadas e encerradas, com o próximo mês a gerar (CA-09.1). */
  listar(): Observable<Recorrencia[]> {
    return this.http.get<Recorrencia[]>(URL);
  }

  criar(entrada: RecorrenciaEntrada, opcoes: OpcoesDeEscrita = {}): Observable<Recorrencia> {
    return this.http.post<Recorrencia>(URL, entrada, {
      context: contextoDeErro(opcoes.tratamentoLocal),
    });
  }

  /** Vale só para o que for gerado depois (CA-09.2). */
  atualizar(
    id: string,
    entrada: RecorrenciaEntrada,
    opcoes: OpcoesDeEscrita = {},
  ): Observable<Recorrencia> {
    return this.http.put<Recorrencia>(`${URL}/${encodeURIComponent(id)}`, entrada, {
      context: contextoDeErro(opcoes.tratamentoLocal),
    });
  }

  /** Pausar, reativar (sem retroativos — RN-11) ou encerrar (definitivo — F-13 Q3). */
  mudarStatus(id: string, status: StatusRecorrencia): Observable<Recorrencia> {
    return this.http.patch<Recorrencia>(`${URL}/${encodeURIComponent(id)}/status`, { status });
  }

  /** Gera os lançamentos devidos até o mês corrente (REQ-10); repetir não duplica. */
  sincronizar(): Observable<Sincronizacao> {
    return this.http.post<Sincronizacao>(`${URL}/sincronizar`, null);
  }
}
