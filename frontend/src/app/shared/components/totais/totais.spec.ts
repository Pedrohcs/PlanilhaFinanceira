import { Component, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Totais } from './totais';

@Component({
  imports: [Totais],
  template: `
    <app-totais [gastos]="gastos()" [receitas]="1000" [saldo]="saldo()">
      <p class="legenda">legenda</p>
    </app-totais>
  `,
})
class Hospedeiro {
  readonly gastos = signal(1234.5);
  readonly saldo = signal(-60);
}

describe('Totais', () => {
  it('numeros_saldo_negativo_e_legenda__CA_12_2', async () => {
    const fixture = TestBed.createComponent(Hospedeiro);
    await fixture.whenStable();
    const elemento: HTMLElement = fixture.nativeElement;
    const numeros = () =>
      Array.from(elemento.querySelectorAll('.numero')).map((n) =>
        n.textContent?.replace(/\u00a0/g, ' ').trim(),
      );

    expect(numeros()).toEqual(['R$ 1.234,50', 'R$ 1.000,00', '\u2212 R$ 60,00']);
    expect(elemento.querySelector('.total.saldo')?.classList.contains('negativo')).toBe(true);
    expect(elemento.querySelector('.totais .legenda')?.textContent).toBe('legenda');

    fixture.componentInstance.saldo.set(0);
    await fixture.whenStable();
    expect(elemento.querySelector('.total.saldo')?.classList.contains('negativo')).toBe(false);
  });
});
