import { TestBed } from '@angular/core/testing';
import { AvisoLinhasIgnoradas } from './aviso-linhas-ignoradas';

describe('AvisoLinhasIgnoradas', () => {
  it('singular_plural_e_zero__CA_16_3', async () => {
    const fixture = TestBed.createComponent(AvisoLinhasIgnoradas);
    const elemento = fixture.nativeElement as HTMLElement;
    const texto = () =>
      elemento.querySelector('[role="status"] p')?.textContent?.replace(/\s+/g, ' ').trim();

    fixture.componentRef.setInput('quantidade', 1);
    await fixture.whenStable();
    expect(texto()).toBe(
      '1 linha da planilha foi ignorada por estar inválida. Corrija-a na planilha e use Recarregar dados.',
    );
    expect(elemento.querySelector('[role="status"] strong')?.textContent).toBe('Recarregar dados');

    fixture.componentRef.setInput('quantidade', 3);
    await fixture.whenStable();
    expect(texto()).toBe(
      '3 linhas da planilha foram ignoradas por estarem inválidas. Corrija-as na planilha e use Recarregar dados.',
    );

    fixture.componentRef.setInput('quantidade', 0);
    await fixture.whenStable();
    expect(elemento.querySelector('[role="status"]')).toBeNull();
    expect(elemento.textContent?.trim()).toBe('');
  });
});
