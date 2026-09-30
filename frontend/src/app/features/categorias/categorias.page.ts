import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { firstValueFrom } from 'rxjs';
import { CategoriasApi } from '../../core/api/categorias.api';
import { Avisos } from '../../core/avisos/avisos';
import { Categoria } from '../../core/models/categoria';
import { TipoLancamento } from '../../core/models/enums';
import { CategoriasStore } from '../../core/state/categorias.store';
import { DadosStore } from '../../core/state/dados.store';
import { Carregando } from '../../shared/components/carregando/carregando';
import { confirmar } from '../../shared/components/confirmacao-dialog/confirmacao.dialog';
import { EstadoVazio } from '../../shared/components/estado-vazio/estado-vazio';
import { CategoriaFormDialog, DadosFormularioCategoria } from './categoria-form.dialog';
import { corSugerida } from './paleta';

interface Secao {
  tipo: TipoLancamento;
  titulo: string;
  vazio: string;
}

const SECOES: readonly Secao[] = [
  { tipo: 'GASTO', titulo: 'Gastos', vazio: 'Nenhuma categoria de gasto.' },
  { tipo: 'RECEITA', titulo: 'Receitas', vazio: 'Nenhuma categoria de receita.' },
];

export const MENSAGEM_EM_USO =
  'Esta categoria está em uso em lançamentos ou recorrências e não pode ser excluída. Deseja desativá-la?';
export const MENSAGEM_RESEED =
  'Como é a última categoria, as 15 categorias padrão serão criadas de novo no próximo início do aplicativo.';

/** Gestão de categorias (REQ-11; F-05 §3.8). */
@Component({
  selector: 'app-categorias-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatButtonModule, MatIconModule, MatMenuModule, Carregando, EstadoVazio],
  template: `
    <h1>Categorias</h1>

    @if (store.carregando() && store.todas().length === 0) {
      <app-carregando texto="Carregando categorias…" />
    } @else if (store.erro() && store.todas().length === 0) {
      <app-estado-vazio icone="cloud_off" mensagem="Não foi possível carregar as categorias." />
    } @else {
      @for (secao of secoes; track secao.tipo) {
        <section class="secao" [attr.aria-labelledby]="'titulo-' + secao.tipo">
          <header class="cabecalho">
            <h2 [id]="'titulo-' + secao.tipo">{{ secao.titulo }}</h2>
            <button matButton="tonal" type="button" (click)="nova(secao.tipo)">
              <mat-icon>add</mat-icon>
              Nova categoria
            </button>
          </header>

          @let categorias = store.porTipo(secao.tipo);
          @if (categorias.length === 0) {
            <app-estado-vazio [mensagem]="secao.vazio" />
          } @else {
            <ul class="lista">
              @for (categoria of categorias; track categoria.id) {
                <li class="item" [class.inativa]="!categoria.ativa">
                  <span
                    class="cor"
                    [style.background-color]="categoria.cor"
                    aria-hidden="true"
                  ></span>
                  <span class="nome">{{ categoria.nome }}</span>
                  @if (!categoria.ativa) {
                    <span class="selo">Inativa</span>
                  }
                  <button
                    matIconButton
                    type="button"
                    [matMenuTriggerFor]="menu"
                    [attr.aria-label]="'Ações de ' + categoria.nome"
                  >
                    <mat-icon>more_vert</mat-icon>
                  </button>
                  <mat-menu #menu="matMenu">
                    <button mat-menu-item type="button" (click)="editar(categoria)">
                      <mat-icon>edit</mat-icon>
                      Editar
                    </button>
                    <button mat-menu-item type="button" (click)="alternarAtiva(categoria)">
                      <mat-icon>{{ categoria.ativa ? 'visibility_off' : 'visibility' }}</mat-icon>
                      {{ categoria.ativa ? 'Desativar' : 'Reativar' }}
                    </button>
                    <button
                      mat-menu-item
                      type="button"
                      [disabled]="categoria.em_uso && !categoria.ativa"
                      (click)="excluir(categoria)"
                    >
                      <mat-icon>delete</mat-icon>
                      {{ categoria.em_uso && !categoria.ativa ? 'Excluir (em uso)' : 'Excluir' }}
                    </button>
                  </mat-menu>
                </li>
              }
            </ul>
          }
        </section>
      }
    }
  `,
  styles: `
    .secao {
      margin-bottom: 24px;
    }
    .cabecalho {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    .lista {
      list-style: none;
      margin: 0;
      padding: 0;
    }
    .item {
      display: flex;
      align-items: center;
      gap: 12px;
      min-height: 48px;
      border-bottom: 1px solid var(--mat-sys-outline-variant);
    }
    .item.inativa .nome {
      color: var(--mat-sys-on-surface-variant);
    }
    .cor {
      flex: 0 0 auto;
      width: 16px;
      height: 16px;
      border-radius: 50%;
    }
    .nome {
      flex: 1 1 auto;
      min-width: 0;
      overflow-wrap: anywhere;
    }
    .selo {
      flex: 0 0 auto;
      padding: 2px 8px;
      border-radius: 12px;
      font: var(--mat-sys-label-small);
      background: var(--mat-sys-surface-container-highest);
      color: var(--mat-sys-on-surface-variant);
    }
  `,
})
export class CategoriasPage {
  protected readonly store = inject(CategoriasStore);
  private readonly api = inject(CategoriasApi);
  private readonly dialog = inject(MatDialog);
  private readonly avisos = inject(Avisos);
  private readonly dados = inject(DadosStore);

  protected readonly secoes = SECOES;

  constructor() {
    void this.store.garantirCarga();
  }

  protected async nova(tipo: TipoLancamento): Promise<void> {
    const criada = await this.abrirFormulario({
      tipo,
      corInicial: corSugerida(tipo, this.store.todas()),
    });
    if (criada) {
      this.concluir('Categoria criada.');
    }
  }

  protected async editar(categoria: Categoria): Promise<void> {
    const salva = await this.abrirFormulario({
      tipo: categoria.tipo,
      categoria,
      corInicial: categoria.cor,
    });
    if (salva) {
      this.concluir('Categoria atualizada.');
    }
  }

  protected async alternarAtiva(categoria: Categoria): Promise<void> {
    await this.salvarAtiva(categoria, !categoria.ativa);
  }

  /** CA-11.3 / F-05 §3.6.3: em uso → oferece desativar, sem chamar o `DELETE`. */
  protected async excluir(categoria: Categoria): Promise<void> {
    if (categoria.em_uso) {
      const desativar = await firstValueFrom(
        confirmar(this.dialog, {
          titulo: 'Categoria em uso',
          mensagem: MENSAGEM_EM_USO,
          textoConfirmar: 'Desativar',
        }),
      );
      if (desativar) {
        await this.salvarAtiva(categoria, false);
      }
      return;
    }

    const ultima = this.store.todas().length === 1;
    const confirmado = await firstValueFrom(
      confirmar(this.dialog, {
        titulo: 'Excluir categoria?',
        mensagem: `A categoria "${categoria.nome}" será excluída.${ultima ? ` ${MENSAGEM_RESEED}` : ''}`,
        textoConfirmar: 'Excluir',
      }),
    );
    if (!confirmado) {
      return;
    }
    try {
      await firstValueFrom(this.api.excluir(categoria.id));
      this.concluir('Categoria excluída.');
    } catch {
      // O interceptor já mostrou a mensagem (ex.: 409 se ganhou uso no meio tempo).
    }
  }

  private async salvarAtiva(categoria: Categoria, ativa: boolean): Promise<void> {
    try {
      await firstValueFrom(
        this.api.atualizar(categoria.id, { nome: categoria.nome, cor: categoria.cor, ativa }),
      );
      this.concluir(ativa ? 'Categoria reativada.' : 'Categoria desativada.');
    } catch {
      // Mensagem já exibida pelo interceptor.
    }
  }

  private abrirFormulario(dados: DadosFormularioCategoria): Promise<Categoria | undefined> {
    return firstValueFrom(
      this.dialog
        .open<CategoriaFormDialog, DadosFormularioCategoria, Categoria>(CategoriaFormDialog, {
          data: dados,
          width: '28rem',
          maxWidth: 'calc(100vw - 32px)',
        })
        .afterClosed(),
    );
  }

  /** Aviso + `versao++`: o store recarrega e as outras telas veem a mudança (`03` §7.1). */
  private concluir(mensagem: string): void {
    void this.avisos.mostrar(mensagem);
    this.dados.incrementar();
  }
}
