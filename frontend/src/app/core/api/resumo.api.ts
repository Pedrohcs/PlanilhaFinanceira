import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { PeriodoHistorico, ResumoHistorico, ResumoMensal } from '../models/resumo';

/** `/api/resumo` (SPECS/03 §6.1; F-09, F-11). */
@Injectable({ providedIn: 'root' })
export class ResumoApi {
  private readonly http = inject(HttpClient);

  mensal(mes: string): Observable<ResumoMensal> {
    return this.http.get<ResumoMensal>('/api/resumo/mensal', {
      params: new HttpParams().set('mes', mes),
    });
  }

  /** Sem período, a API usa o padrão: os 12 meses até o corrente (F-11 §3.2.2). */
  historico(periodo?: PeriodoHistorico): Observable<ResumoHistorico> {
    const params = periodo
      ? new HttpParams().set('inicio', periodo.inicio).set('fim', periodo.fim)
      : new HttpParams();
    return this.http.get<ResumoHistorico>('/api/resumo/historico', { params });
  }
}
