import { ChangeDetectionStrategy, Component } from '@angular/core';

/** Página provisória de F-04; o conteúdo real chega na feature da tela. */
@Component({
  selector: 'app-lancamentos-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <h1>Lançamentos</h1>
    <p>Esta tela ainda está em construção.</p>
  `,
})
export class LancamentosPage {}
