import { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';
import { interpretarValor } from './valor';

/**
 * Validadores dos formulários de lançamento (F-06 §3.2) e de recorrência
 * (F-13 §3.3.4): as mesmas regras e as mesmas chaves de erro nos dois.
 */

/** Valor em pt-BR, maior que zero, até 2 casas (RN-01). Erros: `obrigatorio`, `zero`, `casas`, `invalido`. */
export function valorValido(controle: AbstractControl<string>): ValidationErrors | null {
  const resultado = interpretarValor(controle.value ?? '');
  if ('erro' in resultado) {
    return { [resultado.erro === 'vazio' ? 'obrigatorio' : resultado.erro]: true };
  }
  return resultado.valor > 0 ? null : { zero: true };
}

/** Texto aparado nas pontas, com limite (RN-06). Erros: `obrigatorio`, `longo`. */
export function textoAparado(maximo: number, obrigatorio: boolean): ValidatorFn {
  return (controle: AbstractControl<string>) => {
    const texto = (controle.value ?? '').trim();
    if (obrigatorio && !texto) {
      return { obrigatorio: true };
    }
    return texto.length > maximo ? { longo: true } : null;
  };
}
