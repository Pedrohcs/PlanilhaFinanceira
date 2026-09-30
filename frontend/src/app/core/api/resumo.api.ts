import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ResumoMensal } from '../models/resumo';

/** `/api/resumo` (SPECS/03 §6.1; F-09). */
@Injectable({ providedIn: 'root' })
export class ResumoApi {
  private readonly http = inject(HttpClient);

  mensal(mes: string): Observable<ResumoMensal> {
    return this.http.get<ResumoMensal>('/api/resumo/mensal', {
      params: new HttpParams().set('mes', mes),
    });
  }
}
