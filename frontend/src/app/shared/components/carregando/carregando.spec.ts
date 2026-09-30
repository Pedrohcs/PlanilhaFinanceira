import { TestBed } from '@angular/core/testing';
import { Carregando } from './carregando';

describe('Carregando', () => {
  it('anuncia_o_carregamento__F04_3_5_5', async () => {
    const fixture = TestBed.createComponent(Carregando);
    await fixture.whenStable();
    const elemento = fixture.nativeElement as HTMLElement;

    expect(elemento.getAttribute('role')).toBe('status');
    expect(elemento.getAttribute('aria-live')).toBe('polite');
    expect(elemento.querySelector('mat-progress-spinner')).not.toBeNull();
    expect(elemento.textContent?.trim()).toBe('Carregando…');

    fixture.componentRef.setInput('texto', 'Buscando lançamentos…');
    await fixture.whenStable();
    expect(elemento.textContent?.trim()).toBe('Buscando lançamentos…');
  });
});
