import { InteractivityChecker } from '@angular/cdk/a11y';
import { Provider } from '@angular/core';
import { MATERIAL_ANIMATIONS } from '@angular/material/core';

/**
 * Ajustes do Angular Material para rodar no jsdom (sugestão de T-011):
 *
 * - o jsdom não dispara fim de animação CSS: sem desligar as animações,
 *   diálogos, menus e o datepicker nunca "terminam" de abrir ou fechar;
 * - no jsdom todo elemento tem tamanho zero, e o CDK julgaria qualquer
 *   botão "não focável" (o foco inicial dos diálogos não seria aplicado).
 */
export function provideMaterialParaTestes(): Provider[] {
  return [
    { provide: MATERIAL_ANIMATIONS, useValue: { animationsDisabled: true } },
    {
      provide: InteractivityChecker,
      useValue: { isFocusable: () => true, isTabbable: () => true, isVisible: () => true },
    },
  ];
}
