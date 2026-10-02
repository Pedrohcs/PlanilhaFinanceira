import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

/** `/api/sistema` (SPECS/03 §6.1): ações sobre o próprio app. */
@Injectable({ providedIn: 'root' })
export class SistemaApi {
  private readonly http = inject(HttpClient);

  /** `POST /api/sistema/recarregar` → 204: esvazia o cache do backend (RN-14). */
  recarregar(): Observable<void> {
    return this.http.post<void>('/api/sistema/recarregar', null);
  }
}
