import { TestBed } from '@angular/core/testing';
import { EstadoVazio } from './estado-vazio';

describe('EstadoVazio', () => {
  it('mostra_icone_e_mensagem__F04_3_5_4', async () => {
    const fixture = TestBed.createComponent(EstadoVazio);
    fixture.componentRef.setInput('mensagem', 'Nenhum lançamento neste mês.');
    await fixture.whenStable();
    const elemento = fixture.nativeElement as HTMLElement;

    expect(elemento.querySelector('p')?.textContent).toBe('Nenhum lançamento neste mês.');
    expect(elemento.querySelector('mat-icon')?.textContent).toBe('inbox');

    fixture.componentRef.setInput('icone', 'event_busy');
    await fixture.whenStable();
    expect(elemento.querySelector('mat-icon')?.textContent).toBe('event_busy');
  });
});
