import { ChangeDetectionStrategy, Component } from '@angular/core';
import { SeletorMes } from '../../shared/components/seletor-mes/seletor-mes';

/** Página provisória de F-04; o conteúdo real chega na feature da tela. */
@Component({
  selector: 'app-lancamentos-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SeletorMes],
  template: `
    <h1>Lançamentos</h1>
    <app-seletor-mes />
    <p>Esta tela ainda está em construção.</p>
  `,
})
export class LancamentosPage {}
