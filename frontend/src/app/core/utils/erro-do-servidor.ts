import { FormGroup } from '@angular/forms';

/**
 * O erro que o servidor apontou num campo (`servidor`) sai assim que o
 * usuário volta ao campo — digitar, abrir o select ou escolher de novo o
 * mesmo valor (F-14 §3.2.2). Sem isto, escolher a mesma opção não muda o
 * valor, o erro fica e o formulário não envia.
 *
 * Ligado no `(focusin)` do `<form>`: o evento sobe de qualquer campo, inclusive
 * do `mat-select`, que recebe o foco ao abrir.
 */
export function limparErroDoServidorAoFocar(evento: FocusEvent, formulario: FormGroup): void {
  const campo = (evento.target as HTMLElement | null)?.closest('[formcontrolname]');
  const nome = campo?.getAttribute('formcontrolname');
  const controle = nome ? formulario.get(nome) : null;
  if (controle?.hasError('servidor')) {
    controle.updateValueAndValidity(); // revalida sem o `servidor`; as regras locais continuam
  }
}
