import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import {
  AbstractControl,
  NonNullableFormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { firstValueFrom } from 'rxjs';
import { CategoriasApi } from '../../core/api/categorias.api';
import { Categoria, NOME_CATEGORIA_MAXIMO } from '../../core/models/categoria';
import { TipoLancamento } from '../../core/models/enums';
import { ErroApi } from '../../core/models/erro-api';
import { PALETA } from './paleta';

export interface DadosFormularioCategoria {
  tipo: TipoLancamento;
  /** Presente na edição; ausente na criação. */
  categoria?: Categoria;
  /** Cor inicial na criação (`corSugerida`, F-05 Q2). */
  corInicial: string;
}

type CampoDoFormulario = 'nome' | 'cor';

/** Mesma normalização do backend (F-05 Q1), para o contador e o limite baterem. */
export function normalizarNome(nome: string): string {
  return nome.replace(/\s+/g, ' ').trim();
}

function nomeValido(controle: AbstractControl<string>): ValidationErrors | null {
  const nome = normalizarNome(controle.value ?? '');
  if (!nome) {
    return { obrigatorio: true };
  }
  return nome.length > NOME_CATEGORIA_MAXIMO ? { longo: true } : null;
}

/**
 * Criar/editar categoria (F-05 §3.8.3). O próprio diálogo salva, para poder
 * continuar aberto com os dados quando o backend recusa (409/422): a
 * mensagem aparece no campo.
 */
@Component({
  selector: 'app-categoria-form-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
  ],
  template: `
    <h2 mat-dialog-title>{{ dados.categoria ? 'Editar categoria' : 'Nova categoria' }}</h2>
    <form [formGroup]="formulario" (ngSubmit)="salvar()">
      <mat-dialog-content>
        <p class="tipo">Tipo: {{ dados.tipo === 'GASTO' ? 'Gasto' : 'Receita' }}</p>

        <mat-form-field class="campo-nome">
          <mat-label>Nome</mat-label>
          <input matInput formControlName="nome" autocomplete="off" cdkFocusInitial />
          <mat-hint align="end">{{ tamanhoDoNome() }}/{{ maximo }}</mat-hint>
          @if (formulario.controls.nome.hasError('obrigatorio')) {
            <mat-error>Informe o nome.</mat-error>
          } @else if (formulario.controls.nome.hasError('longo')) {
            <mat-error>Use no máximo {{ maximo }} caracteres.</mat-error>
          } @else if (formulario.controls.nome.hasError('servidor')) {
            <mat-error>{{ formulario.controls.nome.getError('servidor') }}</mat-error>
          }
        </mat-form-field>

        <fieldset class="paleta">
          <legend>Cor</legend>
          @for (cor of cores(); track cor) {
            <button
              type="button"
              class="amostra"
              [style.background-color]="cor"
              [attr.aria-label]="cor"
              [attr.aria-pressed]="formulario.controls.cor.value === cor"
              (click)="formulario.controls.cor.setValue(cor)"
            ></button>
          }
        </fieldset>
        @if (formulario.controls.cor.hasError('servidor')) {
          <p class="erro-cor" role="alert">{{ formulario.controls.cor.getError('servidor') }}</p>
        }
      </mat-dialog-content>

      <mat-dialog-actions align="end">
        <button matButton type="button" mat-dialog-close [disabled]="salvando()">Cancelar</button>
        <button matButton="filled" type="submit" [disabled]="salvando()">
          {{ salvando() ? 'Salvando…' : 'Salvar' }}
        </button>
      </mat-dialog-actions>
    </form>
  `,
  styles: `
    .tipo {
      margin-top: 0;
      color: var(--mat-sys-on-surface-variant);
    }
    .campo-nome {
      width: 100%;
    }
    .paleta {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(36px, 1fr));
      gap: 8px;
      margin: 0;
      padding: 0;
      border: 0;
    }
    .paleta legend {
      margin-bottom: 8px;
    }
    .amostra {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      border: 2px solid transparent;
      cursor: pointer;
    }
    .amostra[aria-pressed='true'] {
      border-color: var(--mat-sys-on-surface);
      box-shadow: 0 0 0 2px var(--mat-sys-surface) inset;
    }
    .erro-cor {
      color: var(--mat-sys-error);
    }
  `,
})
export class CategoriaFormDialog {
  protected readonly dados = inject<DadosFormularioCategoria>(MAT_DIALOG_DATA);
  private readonly referencia = inject<MatDialogRef<CategoriaFormDialog, Categoria>>(MatDialogRef);
  private readonly api = inject(CategoriasApi);

  protected readonly maximo = NOME_CATEGORIA_MAXIMO;
  protected readonly salvando = signal(false);

  protected readonly formulario = inject(NonNullableFormBuilder).group({
    nome: [this.dados.categoria?.nome ?? '', [nomeValido]],
    cor: [this.dados.categoria?.cor.toUpperCase() ?? this.dados.corInicial, [Validators.required]],
  });

  private readonly nome = toSignal(this.formulario.controls.nome.valueChanges, {
    initialValue: this.formulario.controls.nome.value,
  });
  protected readonly tamanhoDoNome = computed(() => normalizarNome(this.nome()).length);

  /** Paleta; a cor atual, se estiver fora dela (editada à mão), vem como opção extra. */
  protected readonly cores = computed(() => {
    const atual = this.dados.categoria?.cor.toUpperCase();
    return atual && !PALETA.includes(atual) ? [...PALETA, atual] : [...PALETA];
  });

  protected async salvar(): Promise<void> {
    this.formulario.markAllAsTouched();
    if (this.formulario.invalid || this.salvando()) {
      return;
    }
    const { nome, cor } = this.formulario.getRawValue();
    this.salvando.set(true);
    try {
      const categoria = this.dados.categoria;
      const salva = await firstValueFrom(
        categoria
          ? this.api.atualizar(categoria.id, {
              nome: normalizarNome(nome),
              cor,
              ativa: categoria.ativa,
            })
          : this.api.criar({ nome: normalizarNome(nome), tipo: this.dados.tipo, cor }),
      );
      this.referencia.close(salva);
    } catch (erro: unknown) {
      this.mostrarErro(erro as ErroApi);
    } finally {
      this.salvando.set(false);
    }
  }

  /** 409 → no nome; 422 → em cada campo de `detalhes` (F-05 §3.8.3). */
  private mostrarErro(erro: ErroApi): void {
    if (erro.status === 409) {
      this.marcar('nome', erro.mensagem);
      return;
    }
    for (const detalhe of erro.detalhes ?? []) {
      if (detalhe.campo === 'nome' || detalhe.campo === 'cor') {
        this.marcar(detalhe.campo as CampoDoFormulario, detalhe.mensagem);
      }
    }
  }

  private marcar(campo: CampoDoFormulario, mensagem: string): void {
    const controle = this.formulario.controls[campo];
    controle.setErrors({ ...(controle.errors ?? {}), servidor: mensagem });
    controle.markAsTouched();
  }
}
