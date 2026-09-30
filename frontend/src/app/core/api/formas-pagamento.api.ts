import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { FormaPagamentoOpcao } from '../models/lancamento';

/** `GET /api/formas-pagamento` (SPECS/03 §6.1): códigos e rótulos de RN-05. */
@Injectable({ providedIn: 'root' })
export class FormasPagamentoApi {
  private readonly http = inject(HttpClient);

  listar(): Observable<FormaPagamentoOpcao[]> {
    return this.http.get<FormaPagamentoOpcao[]>('/api/formas-pagamento');
  }
}
