import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import {
  AbstractControl,
  NonNullableFormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { LancamentosApi } from '../../core/api/lancamentos.api';
import { ParcelamentosApi } from '../../core/api/parcelamentos.api';
import { Avisos } from '../../core/avisos/avisos';
import { FormaPagamento, TipoLancamento } from '../../core/models/enums';
import { ErroApi } from '../../core/models/erro-api';
import {
  DESCRICAO_MAXIMO,
  Lancamento,
  LancamentoEntrada,
  OBSERVACAO_MAXIMO,
} from '../../core/models/lancamento';
import { Parcelamento, ParcelamentoEntrada } from '../../core/models/parcelamento';
import { CategoriasStore } from '../../core/state/categorias.store';
import { DadosStore } from '../../core/state/dados.store';
import { FormasPagamentoStore } from '../../core/state/formas-pagamento.store';
import { dataParaIso, hoje, isoParaData } from '../../core/utils/adaptador-de-data';
import {
  mensagemDoMinimo,
  PARCELAS_MAX,
  PARCELAS_MIN,
  previaDasParcelas,
  textoDaPrevia,
} from '../../core/utils/parcelas';
import { formatarValor, interpretarValor } from '../../core/utils/valor';
import { textoAparado, valorValido } from '../../core/utils/validadores';
import { DATEPICKER_PT_BR } from '../../core/utils/datepicker-intl';
import { limparErroDoServidorAoFocar } from '../../core/utils/erro-do-servidor';

export interface DadosFormularioLancamento {
  tipo: TipoLancamento;
  /** Presente no modo edição (F-08 §3.4). */
  lancamento?: Lancamento;
}

/** O que o diálogo devolve ao fechar salvando: o parcelamento só na compra parcelada. */
export type ResultadoDoFormulario = Lancamento | Parcelamento;

type Campo =
  'data' | 'valor' | 'descricao' | 'categoria_id' | 'forma_pagamento' | 'observacao' | 'parcelas';
const CAMPOS: readonly Campo[] = [
  'data',
  'valor',
  'descricao',
  'categoria_id',
  'forma_pagamento',
  'observacao',
  'parcelas',
];
/** Campos da API com outro nome no formulário (F-12 §3.3.4). */
const CAMPO_DA_API: Record<string, Campo> = { valor_total: 'valor' };
const MENSAGEM_PARCELAS = `Informe de ${PARCELAS_MIN} a ${PARCELAS_MAX} parcelas.`;

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
  parcelas: {
    required: MENSAGEM_PARCELAS,
    min: MENSAGEM_PARCELAS,
    max: MENSAGEM_PARCELAS,
    pattern: MENSAGEM_PARCELAS,
  },
};

/**
 * Na compra parcelada, o total tem de dar R$ 0,01 por parcela (RN-07). A
 * mensagem já vem pronta no erro, com N e o mínimo (F-12 §3.3.2).
 */
function minimoDasParcelas(controle: AbstractControl<string>): ValidationErrors | null {
  const parcelada = controle.parent?.get('parcelada')?.value as boolean | undefined;
  const parcelas = controle.parent?.get('parcelas');
  if (!parcelada || !parcelas?.valid || !parcelas.value) {
    return null;
  }
  const resultado = interpretarValor(controle.value ?? '');
  if (!('valor' in resultado) || resultado.valor <= 0) {
    return null;
  }
  const previa = previaDasParcelas(resultado.valor, parcelas.value as number);
  return 'minimo' in previa
    ? { minimoParcelas: mensagemDoMinimo(parcelas.value as number, previa.minimo) }
    : null;
}

/**
 * Registrar gasto/receita (REQ-01, REQ-02; F-06 §3) e editar lançamento
 * (REQ-05; F-08 §3.4). No registro o tipo vem do botão que abriu o diálogo;
 * na edição ele é um campo (REQ-05: "qualquer campo"). No gasto novo, a
 * "Compra parcelada" envia para `/api/parcelamentos` (F-12 §3.3). O próprio diálogo
 * salva, para continuar aberto com tudo o que foi digitado quando algo falha
 * (CA-01.4).
 */
@Component({
  selector: 'app-lancamento-form-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [DATEPICKER_PT_BR],
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatCheckboxModule,
    MatDatepickerModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
  ],
  template: `
    <h2 mat-dialog-title>{{ titulo() }}</h2>
    <form [formGroup]="formulario" (ngSubmit)="salvar()" (focusin)="aoFocar($event)">
      <mat-dialog-content class="campos">
        @if (edicao; as original) {
          @if (original.parcela_numero) {
            <p class="vinculo largo">
              Parcela {{ original.parcela_numero }}/{{ original.parcela_total }}
            </p>
          }
          @if (original.recorrencia_id) {
            <p class="vinculo largo">Gerado por recorrência</p>
          }
          <mat-form-field class="largo">
            <mat-label>Tipo</mat-label>
            <mat-select formControlName="tipo">
              <mat-option value="GASTO">Gasto</mat-option>
              <mat-option value="RECEITA">Receita</mat-option>
            </mat-select>
          </mat-form-field>
        }

        <mat-form-field>
          <mat-label>{{ parcelada() ? 'Valor total' : 'Valor' }}</mat-label>
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
          <mat-label>{{ parcelada() ? 'Data da compra' : 'Data' }}</mat-label>
          <input matInput [matDatepicker]="calendario" formControlName="data" />
          <mat-datepicker-toggle matIconSuffix [for]="calendario" />
          <mat-datepicker #calendario />
          <mat-hint>dd/mm/aaaa</mat-hint>
          @if (mensagem('data'); as texto) {
            <mat-error>{{ texto }}</mat-error>
          }
        </mat-form-field>

        @if (podeParcelar) {
          <mat-checkbox class="largo parcelada" formControlName="parcelada">
            Compra parcelada
          </mat-checkbox>
          @if (parcelada()) {
            <mat-form-field>
              <mat-label>Nº de parcelas</mat-label>
              <input
                matInput
                type="number"
                inputmode="numeric"
                formControlName="parcelas"
                [min]="parcelasMin"
                [max]="parcelasMax"
              />
              @if (mensagem('parcelas'); as texto) {
                <mat-error>{{ texto }}</mat-error>
              }
            </mat-form-field>
            <p class="previa" aria-live="polite">{{ previa() }}</p>
          }
        }

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
            Nenhuma categoria de {{ rotuloDoTipo() }} ativa. Crie ou reative uma em
            <a routerLink="/categorias" (click)="fechar()">Categorias</a>.
          </p>
        } @else {
          <mat-form-field class="largo">
            <mat-label>Categoria</mat-label>
            <mat-select formControlName="categoria_id">
              @for (categoria of categorias(); track categoria.id) {
                <mat-option [value]="categoria.id">
                  <span class="cor" [style.background-color]="categoria.cor"></span>
                  {{ categoria.nome }}{{ categoria.ativa ? '' : ' (inativa)' }}
                </mat-option>
              }
            </mat-select>
            @if (mensagem('categoria_id'); as texto) {
              <mat-error>{{ texto }}</mat-error>
            }
          </mat-form-field>
        }

        <mat-form-field class="largo">
          <mat-label>Forma de pagamento{{ gasto() ? '' : ' (opcional)' }}</mat-label>
          <mat-select formControlName="forma_pagamento">
            @if (!gasto()) {
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
    .vinculo {
      margin: 0 0 8px;
      color: var(--mat-sys-on-surface-variant);
    }
    .parcelada {
      margin: 0 0 8px;
    }
    .previa {
      align-self: center;
      margin: 0 0 20px;
      color: var(--mat-sys-on-surface-variant);
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
    inject<MatDialogRef<LancamentoFormDialog, ResultadoDoFormulario>>(MatDialogRef);
  private readonly api = inject(LancamentosApi);
  private readonly parcelamentosApi = inject(ParcelamentosApi);
  private readonly avisos = inject(Avisos);
  private readonly categoriasStore = inject(CategoriasStore);
  private readonly formasStore = inject(FormasPagamentoStore);
  private readonly dadosStore = inject(DadosStore);
  private readonly fb = inject(NonNullableFormBuilder);

  /** O lançamento em edição, ou `undefined` no registro. */
  protected readonly edicao = this.dados.lancamento;
  protected readonly descricaoMaximo = DESCRICAO_MAXIMO;
  protected readonly observacaoMaximo = OBSERVACAO_MAXIMO;
  protected readonly salvando = signal(false);
  /** "Compra parcelada" só em gasto novo (`03` §8.3; F-12 §3.3.1). */
  protected readonly podeParcelar = !this.edicao && this.dados.tipo === 'GASTO';
  protected readonly parcelasMin = PARCELAS_MIN;
  protected readonly parcelasMax = PARCELAS_MAX;

  protected readonly formulario = this.construirFormulario(this.edicao?.tipo ?? this.dados.tipo);

  private readonly tipo = toSignal(this.formulario.controls.tipo.valueChanges, {
    initialValue: this.formulario.controls.tipo.value,
  });
  protected readonly gasto = computed(() => this.tipo() === 'GASTO');
  protected readonly rotuloDoTipo = computed(() => (this.gasto() ? 'gasto' : 'receita'));
  protected readonly titulo = computed(() => {
    const acao = this.edicao ? 'Editar' : 'Registrar';
    return `${acao} ${this.gasto() ? 'gasto' : 'receita'}`;
  });

  /**
   * Ativas do tipo, na ordem da API (RN-04, CA-02.1). Na edição, mais a
   * categoria atual do lançamento se ela estiver inativa e for do tipo (F-08 Q1).
   */
  protected readonly categorias = computed(() => {
    const tipo = this.tipo();
    const ativas = this.categoriasStore.ativasPorTipo(tipo);
    const atual = this.categoriasStore
      .todas()
      .find((categoria) => categoria.id === this.edicao?.categoria_id);
    return atual && !atual.ativa && atual.tipo === tipo ? [...ativas, atual] : ativas;
  });
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

  protected readonly parcelada = toSignal(this.formulario.controls.parcelada.valueChanges, {
    initialValue: false,
  });
  private readonly mudancas = toSignal(this.formulario.valueChanges);
  /** Prévia só para exibir (F-12 Q1); vazia enquanto valor ou parcelas forem inválidos. */
  protected readonly previa = computed(() => {
    this.mudancas();
    const { valor, parcelas } = this.formulario.controls;
    if (!this.parcelada() || !parcelas.valid || !parcelas.value || valor.invalid) {
      return '';
    }
    const resultado = interpretarValor(valor.value);
    if (!('valor' in resultado)) {
      return '';
    }
    const previa = previaDasParcelas(resultado.valor, parcelas.value);
    return 'minimo' in previa ? '' : textoDaPrevia(parcelas.value, previa);
  });

  constructor() {
    void this.categoriasStore.garantirCarga();
    void this.formasStore.garantirCarga();
    // Na edição o tipo muda: forma obrigatória só no gasto (RN-05) e categoria
    // de outro tipo é limpa (RN-04; F-08 §3.4.3).
    this.formulario.controls.tipo.valueChanges
      .pipe(takeUntilDestroyed())
      .subscribe((tipo) => this.aoTrocarTipo(tipo));
    const { parcelada, parcelas, valor } = this.formulario.controls;
    parcelada.valueChanges.pipe(takeUntilDestroyed()).subscribe((marcada) => {
      if (marcada) {
        parcelas.enable();
      } else {
        parcelas.disable(); // sai da validação e do corpo (F-12 §3.3.3)
      }
      valor.updateValueAndValidity();
    });
    parcelas.valueChanges
      .pipe(takeUntilDestroyed())
      .subscribe(() => valor.updateValueAndValidity());
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
    if (controle.errors['minimoParcelas']) {
      return controle.errors['minimoParcelas'] as string;
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

  /** O erro do servidor sai quando o usuário volta ao campo (F-14 §3.2.2). */
  protected aoFocar(evento: FocusEvent): void {
    limparErroDoServidorAoFocar(evento, this.formulario);
  }

  protected async salvar(): Promise<void> {
    this.formulario.markAllAsTouched();
    if (this.salvando() || this.semCategorias() || this.formulario.invalid) {
      return;
    }
    this.salvando.set(true);
    try {
      const opcoes = { tratamentoLocal: true };
      const salvo = await firstValueFrom<ResultadoDoFormulario>(
        this.parcelada()
          ? this.parcelamentosApi.criar(this.montarParcelamento(), opcoes)
          : this.edicao
            ? this.api.atualizar(this.edicao.id, this.montarEntrada(), opcoes)
            : this.api.criar(this.montarEntrada(), opcoes),
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
      tipo: valores.tipo,
      descricao: valores.descricao.trim(),
      valor: valor.valor,
      categoria_id: valores.categoria_id,
      forma_pagamento: valores.forma_pagamento || null,
      observacao: valores.observacao.trim() || null,
    };
  }

  /** Corpo de `POST /api/parcelamentos` (F-12 §3.3.4): sem `tipo`, `valor` vira `valor_total`. */
  private montarParcelamento(): ParcelamentoEntrada {
    const { tipo: _tipo, valor, ...resto } = this.montarEntrada();
    return { ...resto, valor_total: valor, parcelas: this.formulario.controls.parcelas.value! };
  }

  /**
   * 422 → no campo de cada `detalhe`; 409 de categoria → no campo categoria,
   * recarregando a lista (a categoria mudou em outro lugar). 503/backend fora
   * já foram para o banner. O diálogo continua aberto com os dados (CA-01.4).
   */
  private mostrarErro(erro: ErroApi): void {
    if (erro.status === 404) {
      // Sumiu da planilha no meio tempo: nada a salvar. O aviso vem do
      // interceptor; a lista recarrega (F-08 §3.3.4).
      this.dadosStore.incrementar();
      this.referencia.close();
      return;
    }
    if (erro.status === 409 && erro.codigo.startsWith('CATEGORIA_')) {
      this.marcar('categoria_id', erro.mensagem);
      void this.categoriasStore.recarregar();
      return;
    }
    if (erro.status === 422) {
      const marcados = (erro.detalhes ?? [])
        .map((detalhe) => ({ ...detalhe, campo: CAMPO_DA_API[detalhe.campo] ?? detalhe.campo }))
        .filter((detalhe) => CAMPOS.includes(detalhe.campo as Campo));
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

  private construirFormulario(tipo: TipoLancamento) {
    const original = this.edicao;
    return this.fb.group({
      tipo: [tipo],
      data: this.fb.control<Date | null>(original ? isoParaData(original.data) : hoje(), [
        Validators.required,
      ]),
      valor: [original ? formatarValor(original.valor) : '', [valorValido, minimoDasParcelas]],
      descricao: [original?.descricao ?? '', [textoAparado(DESCRICAO_MAXIMO, true)]],
      categoria_id: [original?.categoria_id ?? '', [Validators.required]],
      // '' = "Não informar" (só na receita — RN-05, CA-02.2). Nunca pré-selecionada (F-06 Q4).
      forma_pagamento: [
        (original?.forma_pagamento ?? '') as FormaPagamento | '',
        tipo === 'GASTO' ? [Validators.required] : [],
      ],
      observacao: [original?.observacao ?? '', [textoAparado(OBSERVACAO_MAXIMO, false)]],
      parcelada: [false],
      // Vazio de início; habilitado só com "Compra parcelada" marcada (F-12 §3.3.2).
      parcelas: this.fb.control<number | null>({ value: null, disabled: true }, [
        Validators.required,
        Validators.min(PARCELAS_MIN),
        Validators.max(PARCELAS_MAX),
        Validators.pattern(/^\d+$/),
      ]),
    });
  }

  private aoTrocarTipo(tipo: TipoLancamento): void {
    const { categoria_id: categoria, forma_pagamento: forma } = this.formulario.controls;
    const escolhida = this.categoriasStore.todas().find((c) => c.id === categoria.value);
    if (escolhida && escolhida.tipo !== tipo) {
      categoria.setValue('');
    }
    forma.setValidators(tipo === 'GASTO' ? [Validators.required] : []);
    forma.updateValueAndValidity();
  }
}
