import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import {
  AbstractControl,
  NonNullableFormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  ValidatorFn,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { LancamentosApi } from '../../core/api/lancamentos.api';
import { Avisos } from '../../core/avisos/avisos';
import { FormaPagamento, TipoLancamento } from '../../core/models/enums';
import { ErroApi } from '../../core/models/erro-api';
import {
  DESCRICAO_MAXIMO,
  Lancamento,
  LancamentoEntrada,
  OBSERVACAO_MAXIMO,
} from '../../core/models/lancamento';
import { CategoriasStore } from '../../core/state/categorias.store';
import { FormasPagamentoStore } from '../../core/state/formas-pagamento.store';
import { dataParaIso, hoje } from '../../core/utils/adaptador-de-data';
import { formatarValor, interpretarValor } from '../../core/utils/valor';

export interface DadosFormularioLancamento {
  tipo: TipoLancamento;
}

type Campo = 'data' | 'valor' | 'descricao' | 'categoria_id' | 'forma_pagamento' | 'observacao';
const CAMPOS: readonly Campo[] = [
  'data',
  'valor',
  'descricao',
  'categoria_id',
  'forma_pagamento',
  'observacao',
];

/** Mensagens de F-06 §3.2, por campo e por tipo de erro. */
const MENSAGENS: Record<Campo, Record<string, string>> = {
  data: {
    required: 'Informe uma data válida.',
    matDatepickerParse: 'Informe uma data válida.',
  },
  valor: {
    obrigatorio: 'Informe um valor maior que zero.',
    zero: 'Informe um valor maior que zero.',
    casas: 'Use no máximo 2 casas decimais.',
    invalido: 'Valor inválido. Ex.: 1.234,56',
  },
  descricao: {
    obrigatorio: 'Informe a descrição.',
    longo: `Use no máximo ${DESCRICAO_MAXIMO} caracteres.`,
  },
  categoria_id: { required: 'Escolha uma categoria.' },
  forma_pagamento: { required: 'Escolha a forma de pagamento.' },
  observacao: { longo: `Use no máximo ${OBSERVACAO_MAXIMO} caracteres.` },
};

function valorValido(controle: AbstractControl<string>): ValidationErrors | null {
  const resultado = interpretarValor(controle.value ?? '');
  if ('erro' in resultado) {
    return { [resultado.erro === 'vazio' ? 'obrigatorio' : resultado.erro]: true };
  }
  return resultado.valor > 0 ? null : { zero: true };
}

function textoAparado(maximo: number, obrigatorio: boolean): ValidatorFn {
  return (controle: AbstractControl<string>) => {
    const texto = (controle.value ?? '').trim();
    if (obrigatorio && !texto) {
      return { obrigatorio: true };
    }
    return texto.length > maximo ? { longo: true } : null;
  };
}

/**
 * Registrar gasto/receita (REQ-01, REQ-02; F-06 §3). O tipo vem do botão que
 * abriu o diálogo. O próprio diálogo salva, para continuar aberto com tudo o
 * que foi digitado quando algo falha (CA-01.4).
 */
@Component({
  selector: 'app-lancamento-form-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatDatepickerModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
  ],
  template: `
    <h2 mat-dialog-title>{{ titulo }}</h2>
    <form [formGroup]="formulario" (ngSubmit)="salvar()">
      <mat-dialog-content class="campos">
        <mat-form-field>
          <mat-label>Valor</mat-label>
          <span matTextPrefix>R$&nbsp;</span>
          <input
            matInput
            formControlName="valor"
            inputmode="decimal"
            autocomplete="off"
            cdkFocusInitial
            (blur)="reformatarValor()"
          />
          @if (mensagem('valor'); as texto) {
            <mat-error>{{ texto }}</mat-error>
          }
        </mat-form-field>

        <mat-form-field>
          <mat-label>Data</mat-label>
          <input matInput [matDatepicker]="calendario" formControlName="data" />
          <mat-datepicker-toggle matIconSuffix [for]="calendario" />
          <mat-datepicker #calendario />
          <mat-hint>dd/mm/aaaa</mat-hint>
          @if (mensagem('data'); as texto) {
            <mat-error>{{ texto }}</mat-error>
          }
        </mat-form-field>

        <mat-form-field class="largo">
          <mat-label>Descrição</mat-label>
          <input matInput formControlName="descricao" autocomplete="off" />
          <mat-hint align="end">{{ tamanhoDescricao() }}/{{ descricaoMaximo }}</mat-hint>
          @if (mensagem('descricao'); as texto) {
            <mat-error>{{ texto }}</mat-error>
          }
        </mat-form-field>

        @if (semCategorias()) {
          <p class="sem-categorias largo" role="alert">
            Nenhuma categoria de {{ rotuloDoTipo }} ativa. Crie ou reative uma em
            <a routerLink="/categorias" (click)="fechar()">Categorias</a>.
          </p>
        } @else {
          <mat-form-field class="largo">
            <mat-label>Categoria</mat-label>
            <mat-select formControlName="categoria_id">
              @for (categoria of categorias(); track categoria.id) {
                <mat-option [value]="categoria.id">
                  <span class="cor" [style.background-color]="categoria.cor"></span>
                  {{ categoria.nome }}
                </mat-option>
              }
            </mat-select>
            @if (mensagem('categoria_id'); as texto) {
              <mat-error>{{ texto }}</mat-error>
            }
          </mat-form-field>
        }

        <mat-form-field class="largo">
          <mat-label>Forma de pagamento{{ gasto ? '' : ' (opcional)' }}</mat-label>
          <mat-select formControlName="forma_pagamento">
            @if (!gasto) {
              <mat-option value="">Não informar</mat-option>
            }
            @for (forma of formas(); track forma.codigo) {
              <mat-option [value]="forma.codigo">{{ forma.nome }}</mat-option>
            }
          </mat-select>
          @if (mensagem('forma_pagamento'); as texto) {
            <mat-error>{{ texto }}</mat-error>
          }
        </mat-form-field>

        <mat-form-field class="largo">
          <mat-label>Observação (opcional)</mat-label>
          <textarea matInput formControlName="observacao" rows="2"></textarea>
          <mat-hint align="end">{{ tamanhoObservacao() }}/{{ observacaoMaximo }}</mat-hint>
          @if (mensagem('observacao'); as texto) {
            <mat-error>{{ texto }}</mat-error>
          }
        </mat-form-field>
      </mat-dialog-content>

      <mat-dialog-actions align="end">
        <button matButton type="button" [disabled]="salvando()" (click)="fechar()">Cancelar</button>
        <button matButton="filled" type="submit" [disabled]="salvando() || semCategorias()">
          {{ salvando() ? 'Salvando…' : 'Salvar' }}
        </button>
      </mat-dialog-actions>
    </form>
  `,
  styles: `
    .campos {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
      column-gap: 16px;
    }
    .largo {
      grid-column: 1 / -1;
    }
    .cor {
      display: inline-block;
      width: 12px;
      height: 12px;
      margin-right: 8px;
      border-radius: 50%;
      vertical-align: middle;
    }
    .sem-categorias {
      margin: 0 0 16px;
      color: var(--mat-sys-error);
    }
  `,
})
export class LancamentoFormDialog {
  private readonly dados = inject<DadosFormularioLancamento>(MAT_DIALOG_DATA);
  private readonly referencia =
    inject<MatDialogRef<LancamentoFormDialog, Lancamento>>(MatDialogRef);
  private readonly api = inject(LancamentosApi);
  private readonly avisos = inject(Avisos);
  private readonly categoriasStore = inject(CategoriasStore);
  private readonly formasStore = inject(FormasPagamentoStore);
  private readonly fb = inject(NonNullableFormBuilder);

  protected readonly gasto = this.dados.tipo === 'GASTO';
  protected readonly titulo = this.gasto ? 'Registrar gasto' : 'Registrar receita';
  protected readonly rotuloDoTipo = this.gasto ? 'gasto' : 'receita';
  protected readonly descricaoMaximo = DESCRICAO_MAXIMO;
  protected readonly observacaoMaximo = OBSERVACAO_MAXIMO;
  protected readonly salvando = signal(false);

  protected readonly formulario = this.fb.group({
    data: this.fb.control<Date | null>(hoje(), [Validators.required]),
    valor: ['', [valorValido]],
    descricao: ['', [textoAparado(DESCRICAO_MAXIMO, true)]],
    categoria_id: ['', [Validators.required]],
    // '' = "Não informar" (só na receita — RN-05, CA-02.2). Nunca pré-selecionada (Q4).
    forma_pagamento: ['' as FormaPagamento | '', this.gasto ? [Validators.required] : []],
    observacao: ['', [textoAparado(OBSERVACAO_MAXIMO, false)]],
  });

  /** Só ativas do tipo, na ordem da API (RN-04, CA-02.1). */
  protected readonly categorias = computed(() =>
    this.categoriasStore.ativasPorTipo(this.dados.tipo),
  );
  protected readonly semCategorias = computed(
    () => !this.categoriasStore.carregando() && this.categorias().length === 0,
  );
  protected readonly formas = this.formasStore.formas;

  private readonly descricao = toSignal(this.formulario.controls.descricao.valueChanges, {
    initialValue: '',
  });
  private readonly observacao = toSignal(this.formulario.controls.observacao.valueChanges, {
    initialValue: '',
  });
  protected readonly tamanhoDescricao = computed(() => this.descricao().trim().length);
  protected readonly tamanhoObservacao = computed(() => this.observacao().trim().length);

  constructor() {
    void this.categoriasStore.garantirCarga();
    void this.formasStore.garantirCarga();
  }

  /** Mensagem do primeiro erro do campo, só depois de tocado (ou vinda do backend). */
  protected mensagem(campo: Campo): string | null {
    const controle = this.formulario.controls[campo];
    if (!controle.errors || !(controle.touched || controle.dirty)) {
      return null;
    }
    if (controle.errors['servidor']) {
      return controle.errors['servidor'] as string;
    }
    const chave = Object.keys(controle.errors).find((erro) => MENSAGENS[campo][erro]);
    return chave ? MENSAGENS[campo][chave] : null;
  }

  /** Ao sair do campo, `42,5` vira `42,50` (F-06 §3.2.1). */
  protected reformatarValor(): void {
    const controle = this.formulario.controls.valor;
    const resultado = interpretarValor(controle.value);
    if ('valor' in resultado) {
      controle.setValue(formatarValor(resultado.valor));
    }
  }

  protected fechar(): void {
    this.referencia.close();
  }

  protected async salvar(): Promise<void> {
    this.formulario.markAllAsTouched();
    if (this.salvando() || this.semCategorias() || this.formulario.invalid) {
      return;
    }
    this.salvando.set(true);
    try {
      const salvo = await firstValueFrom(
        this.api.criar(this.montarEntrada(), { tratamentoLocal: true }),
      );
      this.referencia.close(salvo);
    } catch (erro: unknown) {
      this.mostrarErro(erro as ErroApi);
    } finally {
      this.salvando.set(false);
    }
  }

  private montarEntrada(): LancamentoEntrada {
    const valores = this.formulario.getRawValue();
    const valor = interpretarValor(valores.valor) as { valor: number };
    return {
      data: dataParaIso(valores.data as Date),
      tipo: this.dados.tipo,
      descricao: valores.descricao.trim(),
      valor: valor.valor,
      categoria_id: valores.categoria_id,
      forma_pagamento: valores.forma_pagamento || null,
      observacao: valores.observacao.trim() || null,
    };
  }

  /**
   * 422 → no campo de cada `detalhe`; 409 de categoria → no campo categoria,
   * recarregando a lista (a categoria mudou em outro lugar). 503/backend fora
   * já foram para o banner. O diálogo continua aberto com os dados (CA-01.4).
   */
  private mostrarErro(erro: ErroApi): void {
    if (erro.status === 409 && erro.codigo.startsWith('CATEGORIA_')) {
      this.marcar('categoria_id', erro.mensagem);
      void this.categoriasStore.recarregar();
      return;
    }
    if (erro.status === 422) {
      const marcados = (erro.detalhes ?? []).filter((detalhe) =>
        CAMPOS.includes(detalhe.campo as Campo),
      );
      marcados.forEach((detalhe) => this.marcar(detalhe.campo as Campo, detalhe.mensagem));
      if (marcados.length === 0) {
        // 422 sem campo conhecido: sem isto o usuário não veria nada.
        void this.avisos.mostrar(erro.mensagem);
      }
    }
  }

  private marcar(campo: Campo, mensagem: string): void {
    const controle = this.formulario.controls[campo];
    controle.setErrors({ ...(controle.errors ?? {}), servidor: mensagem });
    controle.markAsTouched();
  }
}
