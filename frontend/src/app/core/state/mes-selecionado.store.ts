import { DestroyRef, inject, Injectable, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs';
import { mesCorrente, mesValido } from '../utils/mes';

/** Telas que mostram um mês e leem `?mes=` (REQ-04; SPECS/03 §8.1). */
export const ROTAS_COM_MES: readonly string[] = ['resumo', 'lancamentos'];

/**
 * Mês selecionado (`YYYY-MM`), sincronizado com `?mes=` (SPECS/03 §8.2; F-04 §3.4).
 *
 * - sem `?mes=` → mês corrente (CA-04.1);
 * - `?mes=` válido → é o mês selecionado;
 * - `?mes=` inválido → mês corrente, e a URL é corrigida sem nova entrada no
 *   histórico (CA-F04.18).
 *
 * Os links de Resumo e Lançamentos levam o `?mes=` atual, o que mantém o mês
 * entre as duas telas (CA-04.2).
 */
@Injectable({ providedIn: 'root' })
export class MesSelecionadoStore {
  private readonly router = inject(Router);
  private readonly _mes = signal(mesCorrente());
  readonly mes = this._mes.asReadonly();

  constructor() {
    this.router.events
      .pipe(
        filter((evento) => evento instanceof NavigationEnd),
        takeUntilDestroyed(inject(DestroyRef)),
      )
      .subscribe(() => this.lerDaUrl());
    // Criado depois da 1ª navegação (ex.: só quando uma página o injeta)? Lê agora.
    if (this.router.navigated) {
      this.lerDaUrl();
    }
  }

  /** Troca o mês e atualiza `?mes=` substituindo a entrada do histórico (F-04 §10). */
  definir(mes: string): void {
    if (!mesValido(mes)) {
      throw new Error(`Mês fora do formato YYYY-MM: ${mes}`);
    }
    this._mes.set(mes);
    this.escreverNaUrl(mes);
  }

  private lerDaUrl(): void {
    const arvore = this.router.parseUrl(this.router.url);
    const caminho = arvore.root.children['primary']?.segments.map((s) => s.path).join('/');
    if (!caminho || !ROTAS_COM_MES.includes(caminho)) {
      return;
    }
    const valor: unknown = arvore.queryParams['mes'];
    if (valor === undefined) {
      this._mes.set(mesCorrente());
    } else if (typeof valor === 'string' && mesValido(valor)) {
      this._mes.set(valor);
    } else {
      const corrente = mesCorrente();
      this._mes.set(corrente);
      this.escreverNaUrl(corrente);
    }
  }

  /** Mesma rota, mesmos outros parâmetros; só `mes` muda. */
  private escreverNaUrl(mes: string): void {
    const arvore = this.router.parseUrl(this.router.url);
    arvore.queryParams = { ...arvore.queryParams, mes };
    void this.router.navigateByUrl(arvore, { replaceUrl: true });
  }
}
