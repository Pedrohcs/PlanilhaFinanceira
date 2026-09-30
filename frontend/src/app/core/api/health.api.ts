import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { RespostaHealth } from '../models/health';

/** `GET /api/health` (SPECS/03 §6.1, §6.3). */
@Injectable({ providedIn: 'root' })
export class HealthApi {
  private readonly http = inject(HttpClient);

  verificar(): Observable<RespostaHealth> {
    return this.http.get<RespostaHealth>('/api/health');
  }
}
