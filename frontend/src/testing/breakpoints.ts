import { BreakpointState } from '@angular/cdk/layout';
import { BehaviorSubject, map, Observable } from 'rxjs';

/**
 * `BreakpointObserver` com a largura da janela controlada pelo teste. Entende
 * consultas `(min-width: Npx)`, as únicas que o app usa (F-04 Q1, F-07 Q3).
 */
export class BreakpointsFalsos {
  readonly largura = new BehaviorSubject(1280);

  observe(consulta: string): Observable<BreakpointState> {
    return this.largura.pipe(
      map((largura) => {
        const atende = this.atende(consulta, largura);
        return { matches: atende, breakpoints: { [consulta]: atende } };
      }),
    );
  }

  isMatched(consulta: string): boolean {
    return this.atende(consulta, this.largura.value);
  }

  private atende(consulta: string, largura: number): boolean {
    const minimo = Number(/min-width:\s*(\d+)px/.exec(consulta)?.[1]);
    return largura >= minimo;
  }
}
