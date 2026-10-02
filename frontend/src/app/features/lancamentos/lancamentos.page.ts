import { BreakpointObserver } from '@angular/cdk/layout';
import { NgTemplateOutlet } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  Injector,
  signal,
  untracked,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatSelectModule } from '@angular/material/select';
import { ActivatedRoute, Router } from '@angular/router';
import { firstValueFrom, map, Observable } from 'rxjs';
import { LancamentosApi } from '../../core/api/lancamentos.api';
import { ParcelamentosApi } from '../../core/api/parcelamentos.api';
import { Avisos } from '../../core/avisos/avisos';
import { ErroApi } from '../../core/models/erro-api';
import { Categoria } from '../../core/models/categoria';
import { FormaPagamento, TipoLancamento } from '../../core/models/enums';
import { FiltrosLancamentos, Lancamento, ListaLancamentos } from '../../core/models/lancamento';
import { CategoriasStore } from '../../core/state/categorias.store';
import { DadosStore } from '../../core/state/dados.store';
import { FormasPagamentoStore } from '../../core/state/formas-pagamento.store';
import { MesSelecionadoStore } from '../../core/state/mes-selecionado.store';
import { exibirData } from '../../core/utils/adaptador-de-data';
import { mesPorExtenso } from '../../core/utils/mes';
import { formatarValor } from '../../core/utils/valor';
import { Carregando } from '../../shared/components/carregando/carregando';
import { AvisoLinhasIgnoradas } from '../../shared/components/aviso-linhas-ignoradas/aviso-linhas-ignoradas';
import { EstadoVazio } from '../../shared/components/estado-vazio/estado-vazio';
import { confirmar } from '../../shared/components/confirmacao-dialog/confirmacao.dialog';
import { SeletorMes } from '../../shared/components/seletor-mes/seletor-mes';
import { Totais } from '../../shared/components/totais/totais';
import { editarLancamento } from './abrir-lancamento';
import { filtrosParaParams, lerFiltros, temFiltro } from './filtros';

/** Mesma quebra do shell (F-04 Q1): tabela a partir daqui, cartões abaixo (F-07 Q3). */
export const LARGURA_TABELA = 600;
const MENOS = '−';

interface GrupoDeCategorias {
  rotulo: string | null;
  categorias: Categoria[];
}

/**
 * Lançamentos do mês (REQ-03, REQ-04; F-07 §3.2). Filtros na URL (Q1), totais
 * prontos do backend (o frontend não soma — `02` §4), tabela ou cartões
 * conforme a largura (Q3). Recarrega quando mês, filtro ou `versao` mudam.
 * Cada lançamento tem o menu ⋮ com Editar e Excluir (F-08 §3.3); as parcelas, também
 * "Excluir parcelamento inteiro" (F-12 Q2).
 */
@Component({
  selector: 'app-lancamentos-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    NgTemplateOutlet,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatSelectModule,
    SeletorMes,
    Totais,
    Carregando,
    EstadoVazio,
    AvisoLinhasIgnoradas,
  ],
  templateUrl: './lancamentos.page.html',
  styleUrl: './lancamentos.page.scss',
})
export class LancamentosPage {
  private readonly api = inject(LancamentosApi);
  private readonly rota = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly mesStore = inject(MesSelecionadoStore);
  private readonly dados = inject(DadosStore);
  private readonly categoriasStore = inject(CategoriasStore);
  private readonly formasStore = inject(FormasPagamentoStore);
  private readonly breakpoints = inject(BreakpointObserver);
  private readonly parcelamentosApi = inject(ParcelamentosApi);
  private readonly dialog = inject(MatDialog);
  private readonly avisos = inject(Avisos);
  private readonly injetor = inject(Injector);

  private readonly parametros = toSignal(this.rota.queryParams, { initialValue: {} });
  private readonly leitura = computed(() => lerFiltros(this.parametros()));
  /** Comparado por valor: a URL mudar só no `?mes=` (ou ser corrigida) não refaz a busca. */
  protected readonly filtros = computed(() => this.leitura().filtros, {
    equal: (a, b) =>
      a.tipo === b.tipo &&
      a.categoria_id === b.categoria_id &&
      a.forma_pagamento === b.forma_pagamento,
  });
  protected readonly filtrando = computed(() => temFiltro(this.filtros()));
  protected readonly mes = this.mesStore.mes;
  protected readonly formas = this.formasStore.formas;

  protected readonly lista = signal<ListaLancamentos | null>(null);
  protected readonly carregando = signal(false);
  protected readonly erro = signal(false);
  private sequencia = 0;

  protected readonly tabela = toSignal(
    this.breakpoints
      .observe(`(min-width: ${LARGURA_TABELA}px)`)
      .pipe(map((estado) => estado.matches)),
    { initialValue: this.breakpoints.isMatched(`(min-width: ${LARGURA_TABELA}px)`) },
  );

  /** Categorias do filtro: do tipo escolhido; com "Todos", agrupadas (inclui inativas). */
  protected readonly gruposDeCategorias = computed<GrupoDeCategorias[]>(() => {
    const tipo = this.filtros().tipo;
    if (tipo) {
      return [{ rotulo: null, categorias: this.categoriasStore.porTipo(tipo) }];
    }
    return [
      { rotulo: 'Gastos', categorias: this.categoriasStore.porTipo('GASTO') },
      { rotulo: 'Receitas', categorias: this.categoriasStore.porTipo('RECEITA') },
    ];
  });

  private readonly nomesDasFormas = computed(
    () => new Map(this.formas().map((forma) => [forma.codigo, forma.nome])),
  );

  constructor() {
    void this.categoriasStore.garantirCarga();
    void this.formasStore.garantirCarga();

    // Valor inválido na URL (ex.: tipo=OUTRO) é descartado e a URL, corrigida (Q1).
    effect(() => {
      if (this.leitura().descartou) {
        untracked(() => this.gravarFiltros(this.filtros()));
      }
    });

    // Mês, filtros ou `versao` (uma escrita) mudaram: busca de novo (CA-01.5).
    effect(() => {
      const mes = this.mes();
      const filtros = this.filtros();
      this.dados.versao();
      untracked(() => void this.carregar(mes, filtros));
    });
  }

  protected definirTipo(tipo: TipoLancamento | null): void {
    const atual = this.filtros();
    const categoria = this.categoriasStore.todas().find((c) => c.id === atual.categoria_id);
    // Trocar o tipo limpa uma categoria de outro tipo (F-07 §3.2.2).
    const manterCategoria = !tipo || !categoria || categoria.tipo === tipo;
    this.gravarFiltros({
      ...atual,
      tipo,
      categoria_id: manterCategoria ? atual.categoria_id : null,
    });
  }

  protected definirCategoria(categoriaId: string | null): void {
    this.gravarFiltros({ ...this.filtros(), categoria_id: categoriaId });
  }

  protected definirForma(forma: FormaPagamento | null): void {
    this.gravarFiltros({ ...this.filtros(), forma_pagamento: forma });
  }

  protected limparFiltros(): void {
    this.gravarFiltros({ tipo: null, categoria_id: null, forma_pagamento: null });
  }

  protected valor(lancamento: Lancamento): string {
    const sinal = lancamento.tipo === 'GASTO' ? MENOS : '+';
    return `${sinal} R$ ${formatarValor(lancamento.valor)}`;
  }

  protected rotuloDoValor(lancamento: Lancamento): string {
    const tipo = lancamento.tipo === 'GASTO' ? 'gasto' : 'receita';
    return `${tipo} de R$ ${formatarValor(lancamento.valor)}`;
  }

  /** Totais e saldo: o saldo pode ser negativo (RN-13). */
  protected forma(lancamento: Lancamento): string {
    if (!lancamento.forma_pagamento) {
      return '—';
    }
    return this.nomesDasFormas().get(lancamento.forma_pagamento) ?? lancamento.forma_pagamento;
  }

  protected data(iso: string): string {
    return exibirData(iso);
  }

  /** Editar (REQ-05): diálogo de F-06 em modo edição. */
  protected editar(lancamento: Lancamento): void {
    void editarLancamento(this.injetor, lancamento);
  }

  /**
   * Excluir (REQ-06): confirma mostrando descrição, valor e data (CA-06.1),
   * com aviso extra para parcela (RN-08) e recorrência (RN-10).
   */
  protected async excluir(lancamento: Lancamento): Promise<void> {
    const extras = [
      lancamento.parcela_numero
        ? `Só esta parcela (${lancamento.parcela_numero}/${lancamento.parcela_total}) será excluída; as demais continuam.`
        : null,
      lancamento.recorrencia_id ? 'A recorrência não gera este lançamento de novo.' : null,
    ].filter((texto) => texto !== null);
    const confirmado = await firstValueFrom(
      confirmar(this.dialog, {
        titulo: 'Excluir lançamento?',
        mensagem: [
          `"${lancamento.descricao}" — ${this.valor(lancamento)} em ${exibirData(lancamento.data)} será excluído.`,
          ...extras,
        ].join(' '),
        textoConfirmar: 'Excluir',
      }),
    );
    if (confirmado) {
      await this.excluirERecarregar(this.api.excluir(lancamento.id), 'Lançamento excluído.');
    }
  }

  /**
   * "Excluir parcelamento inteiro" (REQ-08, F-12 Q2): todas as parcelas
   * restantes, em qualquer mês (CA-08.2).
   */
  protected async excluirParcelamento(parcela: Lancamento): Promise<void> {
    const confirmado = await firstValueFrom(
      confirmar(this.dialog, {
        titulo: 'Excluir parcelamento inteiro?',
        mensagem: `"${parcela.descricao}" — todas as parcelas restantes deste parcelamento em ${parcela.parcela_total}×, em todos os meses, serão excluídas.`,
        textoConfirmar: 'Excluir parcelas',
      }),
    );
    if (confirmado) {
      await this.excluirERecarregar(
        this.parcelamentosApi.excluir(parcela.parcelamento_id!),
        'Parcelamento excluído.',
      );
    }
  }

  /**
   * Sucesso → aviso e recarga (CA-06.2). A mensagem de erro já veio do
   * interceptor. No 404 já não existe: recarrega (F-08 §3.3.4). Planilha
   * fora: a lista continua (F-08 borda 12).
   */
  private async excluirERecarregar(exclusao: Observable<void>, sucesso: string): Promise<void> {
    try {
      await firstValueFrom(exclusao, { defaultValue: undefined });
      void this.avisos.mostrar(sucesso);
    } catch (erro: unknown) {
      if ((erro as ErroApi).status !== 404) {
        return;
      }
    }
    this.dados.incrementar();
  }

  protected mesPorExtenso(mes: string): string {
    return mesPorExtenso(mes);
  }

  /** Uma busca por vez vale: resposta de busca anterior é descartada (borda 15). */
  private async carregar(mes: string, filtros: FiltrosLancamentos): Promise<void> {
    const minha = ++this.sequencia;
    this.carregando.set(true);
    try {
      const lista = await firstValueFrom(this.api.listar(mes, filtros));
      if (minha === this.sequencia) {
        this.lista.set(lista);
        this.erro.set(false);
      }
    } catch {
      if (minha === this.sequencia) {
        this.lista.set(null);
        this.erro.set(true); // a causa já foi mostrada pelo interceptor/banner
      }
    } finally {
      if (minha === this.sequencia) {
        this.carregando.set(false);
      }
    }
  }

  /** Grava os filtros na URL, mantendo o `?mes=`, sem empilhar histórico (Q1). */
  private gravarFiltros(filtros: FiltrosLancamentos): void {
    void this.router.navigate([], {
      relativeTo: this.rota,
      queryParams: filtrosParaParams(filtros),
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
  }
}
