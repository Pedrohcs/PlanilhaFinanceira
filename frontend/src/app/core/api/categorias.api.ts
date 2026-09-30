import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { contextoDeErro, OpcoesDeEscrita } from '../interceptors/erro.interceptor';
import { Categoria, CategoriaAtualizacao, CategoriaEntrada } from '../models/categoria';
import { TipoLancamento } from '../models/enums';

const URL = '/api/categorias';

/** `/api/categorias` (SPECS/03 §6.1). */
@Injectable({ providedIn: 'root' })
export class CategoriasApi {
  private readonly http = inject(HttpClient);

  listar(
    filtro: { tipo?: TipoLancamento; incluirInativas?: boolean } = {},
  ): Observable<Categoria[]> {
    let params = new HttpParams();
    if (filtro.tipo) {
      params = params.set('tipo', filtro.tipo);
    }
    if (filtro.incluirInativas) {
      params = params.set('incluir_inativas', 'true');
    }
    return this.http.get<Categoria[]>(URL, { params });
  }

  criar(entrada: CategoriaEntrada, opcoes: OpcoesDeEscrita = {}): Observable<Categoria> {
    return this.http.post<Categoria>(URL, entrada, {
      context: contextoDeErro(opcoes.tratamentoLocal),
    });
  }

  atualizar(
    id: string,
    dados: CategoriaAtualizacao,
    opcoes: OpcoesDeEscrita = {},
  ): Observable<Categoria> {
    return this.http.put<Categoria>(`${URL}/${encodeURIComponent(id)}`, dados, {
      context: contextoDeErro(opcoes.tratamentoLocal),
    });
  }

  excluir(id: string): Observable<void> {
    return this.http.delete<void>(`${URL}/${encodeURIComponent(id)}`);
  }
}
