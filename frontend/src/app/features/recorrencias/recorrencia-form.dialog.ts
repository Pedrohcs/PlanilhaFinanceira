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
import { MatDatepicker, MatDatepickerModule } from '@angular/material/datepicker';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { RecorrenciasApi } from '../../core/api/recorrencias.api';
import { Avisos } from '../../core/avisos/avisos';
import { FormaPagamento, TipoLancamento } from '../../core/models/enums';
import { ErroApi } from '../../core/models/erro-api';
import { DESCRICAO_MAXIMO } from '../../core/models/lancamento';
import { Recorrencia, RecorrenciaEntrada } from '../../core/models/recorrencia';
import { CategoriasStore } from '../../core/state/categorias.store';
import { DadosStore } from '../../core/state/dados.store';
import { FormasPagamentoStore } from '../../core/state/formas-pagamento.store';
import { hoje } from '../../core/utils/adaptador-de-data';
import {
  dataParaMes,
  mesCorrente,
  mesesNoPeriodo,
  mesParaData,
  mesPorExtenso,
} from '../../core/utils/mes';
import { textoAparado, valorValido } from '../../core/utils/validadores';
import { formatarValor, interpretarValor } from '../../core/utils/valor';

export interface DadosFormularioRecorrencia {
  /** Presente no modo edição. */
  recorrencia?: Recorrencia;
}

type Campo =
  | 'tipo'
  | 'valor'
  | 'descricao'
  | 'categoria_id'
  | 'forma_pagamento'
  | 'dia_do_mes'
  | 'mes_inicio'
  | 'mes_fim';
const CAMPOS: readonly Campo[] = [
  'tipo',
  'valor',
  'descricao',
  'categoria_id',
  'forma_pagamento',
  'dia_do_mes',
  'mes_inicio',
  'mes_fim',
];
const MENSAGEM_DIA = 'Informe um dia de 1 a 31.';
const MENSAGEM_FIM_ANTES = 'O mês de fim deve ser igual ou posterior ao mês de início.';

/** Mensagens por campo e tipo de erro (as de F-06 §3.2 onde o campo é o mesmo). */
const MENSAGENS: Record<Campo, Record<string, string>> = {
  tipo: {},
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
  dia_do_mes: {
    required: MENSAGEM_DIA,
    min: MENSAGEM_DIA,
    max: MENSAGEM_DIA,
    pattern: MENSAGEM_DIA,
  },
  mes_inicio: {},
  mes_fim: { antesDoInicio: MENSAGEM_FIM_ANTES },
};

/** `mes_fim` (se houver) ≥ `mes_inicio` (F-13 §3.1.2). O erro fica no campo `mes_fim`. */
function vigenciaValida(grupo: AbstractControl): ValidationErrors | null {
  const inicio = grupo.get('mes_inicio')?.value as string;
  const fimControle = grupo.get('mes_fim');
  const fim = fimControle?.value as string | null;
  const invalida = !!fim && fim < inicio;
  const erros = { ...(fimControle?.errors ?? {}) };
  delete erros['antesDoInicio'];
  if (invalida) {
    erros['antesDoInicio'] = true;
  }
  fimControle?.setErrors(Object.keys(erros).length ? erros : null, { emitEvent: false });
  return null;
}

/**
 * Nova recorrência / editar recorrência (REQ-09; F-13 §3.3.4). Salva sozinho e
 * fica aberto com os dados quando algo falha (CA-01.4, CA-F13.23); quem abriu
 * sincroniza depois de salvar (F-13 Q5).
 */
@Component({
  selector: 'app-recorrencia-form-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatDatepickerModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
  ],
  template: `
    <h2 mat-dialog-title>{{ edicao ? 'Editar recorrência' : 'Nova recorrência' }}</h2>
    <form [formGroup]="formulario" (ngSubmit)="salvar()">
      <mat-dialog-content class="campos">
        <mat-form-field>
          <mat-label>Tipo</mat-label>
          <mat-select formControlName="tipo">
            <mat-option value="GASTO">Gasto</mat-option>
            <mat-option value="RECEITA">Receita</mat-option>
          </mat-select>
        </mat-form-field>

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
            Nenhuma categoria de {{ gasto() ? 'gasto' : 'receita' }} ativa. Crie ou reative uma em
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
          <mat-label>Dia do mês</mat-label>
          <input
            matInput
            type="number"
            inputmode="numeric"
            formControlName="dia_do_mes"
            min="1"
            max="31"
          />
          <mat-hint>Nos meses sem esse dia, usa o último dia do mês.</mat-hint>
          @if (mensagem('dia_do_mes'); as texto) {
            <mat-error>{{ texto }}</mat-error>
          }
        </mat-form-field>

        <div class="mes">
          <span class="rotulo" id="rotulo-inicio">Mês de início</span>
          <span class="ancora">
            <button
              matButton="outlined"
              type="button"
              class="inicio"
              aria-describedby="rotulo-inicio"
              (click)="calendarioInicio.open()"
            >
              {{ extenso(mesInicio()) }}
            </button>
            <input
              class="ancora-input"
              tabindex="-1"
              aria-hidden="true"
              [matDatepicker]="calendarioInicio"
              [value]="dataDoMes(mesInicio())"
            />
            <mat-datepicker
              #calendarioInicio
              startView="multi-year"
              (monthSelected)="escolherMes('mes_inicio', $event, calendarioInicio)"
            />
          </span>
          @if (mensagem('mes_inicio'); as texto) {
            <span class="erro" role="alert">{{ texto }}</span>
          }
        </div>

        <div class="mes">
          <span class="rotulo" id="rotulo-fim">Mês de fim</span>
          <span class="ancora">
            <button
              matButton="outlined"
              type="button"
              class="fim"
              aria-describedby="rotulo-fim"
              (click)="calendarioFim.open()"
            >
              {{ mesFim() ? extenso(mesFim()!) : 'Sem fim' }}
            </button>
            <input
              class="ancora-input"
              tabindex="-1"
              aria-hidden="true"
              [matDatepicker]="calendarioFim"
              [value]="dataDoMes(mesFim() ?? mesInicio())"
            />
            <mat-datepicker
              #calendarioFim
              startView="multi-year"
              (monthSelected)="escolherMes('mes_fim', $event, calendarioFim)"
            />
          </span>
          @if (mesFim()) {
            <button
              matIconButton
              type="button"
              class="sem-fim"
              aria-label="Remover mês de fim"
              (click)="removerFim()"
            >
              <mat-icon>close</mat-icon>
            </button>
          }
          @if (mensagem('mes_fim'); as texto) {
            <span class="erro" role="alert">{{ texto }}</span>
          }
        </div>

        @if (avisoRetroativo(); as aviso) {
          <p class="retroativo largo" aria-live="polite">{{ aviso }}</p>
        }
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
    .mes {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 4px 8px;
      margin: 8px 0 16px;
    }
    .mes .rotulo {
      flex-basis: 100%;
      font: var(--mat-sys-body-small);
      color: var(--mat-sys-on-surface-variant);
    }
    .ancora {
      position: relative;
    }
    .ancora-input {
      position: absolute;
      left: 0;
      bottom: 0;
      width: 0;
      height: 0;
      padding: 0;
      border: 0;
      opacity: 0;
      pointer-events: none;
    }
    .erro {
      flex-basis: 100%;
      font: var(--mat-sys-body-small);
      color: var(--mat-sys-error);
    }
    .retroativo {
      margin: 0 0 8px;
      color: var(--mat-sys-on-surface-variant);
    }
    .sem-categorias {
      margin: 0 0 16px;
      color: var(--mat-sys-error);
    }
  `,
})
export class RecorrenciaFormDialog {
  private readonly dados = inject<DadosFormularioRecorrencia>(MAT_DIALOG_DATA);
  private readonly referencia =
    inject<MatDialogRef<RecorrenciaFormDialog, Recorrencia>>(MatDialogRef);
  private readonly api = inject(RecorrenciasApi);
  private readonly avisos = inject(Avisos);
  private readonly categoriasStore = inject(CategoriasStore);
  private readonly formasStore = inject(FormasPagamentoStore);
  private readonly dadosStore = inject(DadosStore);
  private readonly fb = inject(NonNullableFormBuilder);

  /** A recorrência em edição, ou `undefined` na criação. */
  protected readonly edicao = this.dados.recorrencia;
  protected readonly descricaoMaximo = DESCRICAO_MAXIMO;
  protected readonly salvando = signal(false);
  protected readonly formulario = this.construirFormulario();

  private readonly tipo = toSignal(this.formulario.controls.tipo.valueChanges, {
    initialValue: this.formulario.controls.tipo.value,
  });
  protected readonly gasto = computed(() => this.tipo() === 'GASTO');
  protected readonly mesInicio = toSignal(this.formulario.controls.mes_inicio.valueChanges, {
    initialValue: this.formulario.controls.mes_inicio.value,
  });
  protected readonly mesFim = toSignal(this.formulario.controls.mes_fim.valueChanges, {
    initialValue: this.formulario.controls.mes_fim.value,
  });
  private readonly descricao = toSignal(this.formulario.controls.descricao.valueChanges, {
    initialValue: this.formulario.controls.descricao.value,
  });
  protected readonly tamanhoDescricao = computed(() => this.descricao().trim().length);

  /** Ativas do tipo; na edição, mais a categoria atual se estiver inativa e for do tipo (F-08 Q1). */
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

  /**
   * "Os lançamentos de julho de 2026 a setembro de 2026 serão gerados ao
   * salvar." — só enquanto nada foi gerado (criação, ou ativa nunca gerada):
   * depois disso, mudar o início não gera para trás (F-13 §3.3.4, Q6).
   */
  protected readonly avisoRetroativo = computed(() => {
    const nuncaGerou =
      !this.edicao || (this.edicao.status === 'ATIVA' && !this.edicao.ultimo_mes_gerado);
    const inicio = this.mesInicio();
    const corrente = mesCorrente();
    if (!nuncaGerou || inicio >= corrente) {
      return null;
    }
    const fim = this.mesFim();
    const ultimo = fim && fim < corrente ? fim : corrente;
    if (ultimo < inicio) {
      return null;
    }
    return mesesNoPeriodo(inicio, ultimo) === 1
      ? `O lançamento de ${mesPorExtenso(inicio)} será gerado ao salvar.`
      : `Os lançamentos de ${mesPorExtenso(inicio)} a ${mesPorExtenso(ultimo)} serão gerados ao salvar.`;
  });

  constructor() {
    void this.categoriasStore.garantirCarga();
    void this.formasStore.garantirCarga();
    this.formulario.controls.tipo.valueChanges
      .pipe(takeUntilDestroyed())
      .subscribe((tipo) => this.aoTrocarTipo(tipo));
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

  protected extenso(mes: string): string {
    return mesPorExtenso(mes);
  }

  protected dataDoMes(mes: string): Date {
    return mesParaData(mes);
  }

  protected escolherMes(
    campo: 'mes_inicio' | 'mes_fim',
    data: Date,
    calendario: MatDatepicker<Date>,
  ): void {
    const controle = this.formulario.controls[campo];
    controle.setValue(dataParaMes(data));
    controle.markAsDirty();
    this.formulario.controls.mes_fim.markAsDirty(); // a regra de vigência depende dos dois
    calendario.close();
  }

  protected removerFim(): void {
    this.formulario.controls.mes_fim.setValue(null);
  }

  /** Ao sair do campo, `39,9` vira `39,90` (F-06 §3.2.1). */
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
      const opcoes = { tratamentoLocal: true };
      const salva = await firstValueFrom(
        this.edicao
          ? this.api.atualizar(this.edicao.id, this.montarEntrada(), opcoes)
          : this.api.criar(this.montarEntrada(), opcoes),
      );
      this.referencia.close(salva);
    } catch (erro: unknown) {
      this.mostrarErro(erro as ErroApi);
    } finally {
      this.salvando.set(false);
    }
  }

  private montarEntrada(): RecorrenciaEntrada {
    const valores = this.formulario.getRawValue();
    const valor = interpretarValor(valores.valor) as { valor: number };
    return {
      tipo: valores.tipo,
      descricao: valores.descricao.trim(),
      valor: valor.valor,
      categoria_id: valores.categoria_id,
      forma_pagamento: valores.forma_pagamento || null,
      dia_do_mes: Number(valores.dia_do_mes),
      mes_inicio: valores.mes_inicio,
      mes_fim: valores.mes_fim,
    };
  }

  /**
   * 422 → no campo de cada `detalhe` (campo `status`: a recorrência foi
   * encerrada em outro lugar — avisa, fecha e recarrega); 409 de categoria → no
   * campo categoria; 404 → fecha e recarrega. 503 e backend fora já foram
   * para o banner. Fora esses casos, o diálogo continua aberto com os dados.
   */
  private mostrarErro(erro: ErroApi): void {
    if (erro.status === 404) {
      this.dadosStore.incrementar();
      this.referencia.close();
      return;
    }
    if (erro.status === 409 && erro.codigo.startsWith('CATEGORIA_')) {
      this.marcar('categoria_id', erro.mensagem);
      void this.categoriasStore.recarregar();
      return;
    }
    if (erro.status !== 422) {
      return;
    }
    const detalhes = erro.detalhes ?? [];
    const status = detalhes.find((detalhe) => detalhe.campo === 'status');
    if (status) {
      void this.avisos.mostrar(status.mensagem);
      this.dadosStore.incrementar();
      this.referencia.close();
      return;
    }
    const marcados = detalhes.filter((detalhe) => CAMPOS.includes(detalhe.campo as Campo));
    marcados.forEach((detalhe) => this.marcar(detalhe.campo as Campo, detalhe.mensagem));
    if (marcados.length === 0) {
      void this.avisos.mostrar(erro.mensagem); // sem isto o usuário não veria nada
    }
  }

  private marcar(campo: Campo, mensagem: string): void {
    const controle = this.formulario.controls[campo];
    controle.setErrors({ ...(controle.errors ?? {}), servidor: mensagem });
    controle.markAsTouched();
  }

  private construirFormulario() {
    const original = this.edicao;
    const tipo: TipoLancamento = original?.tipo ?? 'GASTO';
    return this.fb.group(
      {
        tipo: [tipo],
        valor: [original ? formatarValor(original.valor) : '', [valorValido]],
        descricao: [original?.descricao ?? '', [textoAparado(DESCRICAO_MAXIMO, true)]],
        categoria_id: [original?.categoria_id ?? '', [Validators.required]],
        // '' = "Não informar" (só na receita — RN-05).
        forma_pagamento: [
          (original?.forma_pagamento ?? '') as FormaPagamento | '',
          tipo === 'GASTO' ? [Validators.required] : [],
        ],
        dia_do_mes: this.fb.control<number | null>(original?.dia_do_mes ?? hoje().getDate(), [
          Validators.required,
          Validators.min(1),
          Validators.max(31),
          Validators.pattern(/^\d+$/),
        ]),
        mes_inicio: [original?.mes_inicio ?? mesCorrente()],
        mes_fim: this.fb.control<string | null>(original?.mes_fim ?? null),
      },
      { validators: [vigenciaValida] },
    );
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
