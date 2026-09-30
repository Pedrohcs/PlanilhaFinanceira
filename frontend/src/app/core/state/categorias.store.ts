import { effect, inject, Injectable, signal, untracked } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { CategoriasApi } from '../api/categorias.api';
import { Categoria } from '../models/categoria';
import { TipoLancamento } from '../models/enums';
import { DadosStore } from './dados.store';

/**
 * Categorias do usuário (SPECS/03 §8.2; F-05 §3.9).
 *
 * Carrega todas (inclusive inativas) na primeira vez que alguém chama
 * `garantirCarga()`, e recarrega sozinho quando `DadosStore.versao` muda —
 * o que toda escrita bem-sucedida faz. Não calcula nem reordena: a ordem é a
 * da API (F-05 Q3).
 */
@Injectable({ providedIn: 'root' })
export class CategoriasStore {
  private readonly api = inject(CategoriasApi);
  private readonly dados = inject(DadosStore);

  private readonly _todas = signal<Categoria[]>([]);
  private readonly _carregando = signal(false);
  private readonly _erro = signal(false);
  private carregou = false;
  /** `DadosStore.versao` da última carga: só uma versão **nova** recarrega. */
  private versaoCarregada = -1;

  readonly todas = this._todas.asReadonly();
  readonly carregando = this._carregando.asReadonly();
  /** A última carga falhou (a causa já foi mostrada pelo interceptor). */
  readonly erro = this._erro.asReadonly();

  constructor() {
    effect(() => {
      const versao = this.dados.versao();
      untracked(() => {
        if (this.carregou && versao !== this.versaoCarregada) {
          void this.recarregar();
        }
      });
    });
  }

  /** Carrega na primeira vez; depois disso, não faz nada (o `versao` cuida das recargas). */
  garantirCarga(): Promise<void> {
    if (this.carregou) {
      return Promise.resolve();
    }
    this.carregou = true;
    return this.recarregar();
  }

  porTipo(tipo: TipoLancamento): Categoria[] {
    return this._todas().filter((categoria) => categoria.tipo === tipo);
  }

  /** Para os formulários de lançamento (F-06): só ativas do tipo (RN-04, CA-11.4). */
  ativasPorTipo(tipo: TipoLancamento): Categoria[] {
    return this.porTipo(tipo).filter((categoria) => categoria.ativa);
  }

  async recarregar(): Promise<void> {
    this.versaoCarregada = untracked(this.dados.versao);
    this._carregando.set(true);
    try {
      this._todas.set(await firstValueFrom(this.api.listar({ incluirInativas: true })));
      this._erro.set(false);
    } catch {
      this._erro.set(true);
    } finally {
      this._carregando.set(false);
    }
  }
}
