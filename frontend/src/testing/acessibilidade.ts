/**
 * Conferências de acessibilidade básica para os specs (F-14 §3.1.4).
 *
 * Devolvem o que está **faltando**, para o `expect(...).toEqual([])` mostrar
 * na falha exatamente qual campo ou botão ficou sem rótulo.
 */

/** Campos do Material sem `mat-label`. */
export function camposSemRotulo(raiz: ParentNode): string[] {
  return Array.from(raiz.querySelectorAll('mat-form-field'))
    .filter((campo) => !campo.querySelector('mat-label')?.textContent?.trim())
    .map((campo) => campo.outerHTML.slice(0, 80));
}

/** Botões sem nome acessível: só ícone (o texto do `mat-icon` é a ligadura) e sem `aria-label`. */
export function botoesSemNome(raiz: ParentNode): string[] {
  return Array.from(raiz.querySelectorAll('button'))
    .filter((botao) => {
      const copia = botao.cloneNode(true) as HTMLElement;
      copia.querySelectorAll('mat-icon').forEach((icone) => icone.remove());
      const texto = copia.textContent?.trim();
      const rotulo = botao.getAttribute('aria-label') ?? botao.getAttribute('aria-labelledby');
      return !texto && !rotulo;
    })
    .map((botao) => botao.outerHTML.slice(0, 80));
}
