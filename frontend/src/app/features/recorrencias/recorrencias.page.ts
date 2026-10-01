import { BreakpointObserver } from '@angular/cdk/layout';
import { NgTemplateOutlet } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  signal,
  untracked,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { firstValueFrom, map } from 'rxjs';
import { RecorrenciasApi } from '../../core/api/recorrencias.api';
import { Avisos } from '../../core/avisos/avisos';
import { StatusRecorrencia } from '../../core/models/enums';
import { ErroApi } from '../../core/models/erro-api';
import { Recorrencia } from '../../core/models/recorrencia';
import { CategoriasStore } from '../../core/state/categorias.store';
import { DadosStore } from '../../core/state/dados.store';
import { SincronizacaoRecorrencias, textoDosGerados } from '../../core/state/sincronizacao';
import { mesPorExtenso } from '../../core/utils/mes';
import { formatarValor } from '../../core/utils/valor';
import { Carregando } from '../../shared/components/carregando/carregando';
import { confirmar } from '../../shared/components/confirmacao-dialog/confirmacao.dialog';
import { EstadoVazio } from '../../shared/components/estado-vazio/estado-vazio';
import { DadosFormularioRecorrencia, RecorrenciaFormDialog } from './recorrencia-form.dialog';

/** Mesma quebra da listagem de lançamentos (F-07 Q3): tabela a partir daqui, cartões abaixo. */
export const LARGURA_TABELA = 600;
const MENOS = '−';
const TAMANHO_DO_DIALOGO = { width: '36rem', maxWidth: 'calc(100vw - 32px)' };
/** Categoria apagada à mão na planilha (F-07 §3.1.6). */
const CATEGORIA_AUSENTE = { nome: 'Categoria não encontrada', cor: '#9E9E9E', ativa: true };

const ROTULOS_STATUS: Record<StatusRecorrencia, string> = {
  ATIVA: 'Ativa',
  PAUSADA: 'Pausada',
  ENCERRADA: 'Encerrada',
};

export const MENSAGEM_REATIVADA =
  'Recorrência reativada. Meses do período pausado não são gerados.';

/**
 * Recorrências (REQ-09; F-13 §3.3): lista com estado e próximo mês (CA-09.1),
 * menu ⋮ conforme o estado, diálogo de criar/editar. Depois de salvar ou
 * reativar, sincroniza na hora (F-13 Q5): um aviso só por ação.
 */
@Component({
  selector: 'app-recorrencias-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    NgTemplateOutlet,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    Carregando,
    EstadoVazio,
  ],
  templateUrl: './recorrencias.page.html',
  styleUrl: './recorrencias.page.scss',
})
export class RecorrenciasPage {
  private readonly api = inject(RecorrenciasApi);
  private readonly avisos = inject(Avisos);
  private readonly categoriasStore = inject(CategoriasStore);
  private readonly dados = inject(DadosStore);
  private readonly dialog = inject(MatDialog);
  private readonly sincronizacao = inject(SincronizacaoRecorrencias);
  private readonly breakpoints = inject(BreakpointObserver);

  protected readonly lista = signal<Recorrencia[] | null>(null);
  protected readonly carregando = signal(false);
  protected readonly erro = signal(false);
  private sequencia = 0;

  protected readonly tabela = toSignal(
    this.breakpoints
      .observe(`(min-width: ${LARGURA_TABELA}px)`)
      .pipe(map((estado) => estado.matches)),
    { initialValue: this.breakpoints.isMatched(`(min-width: ${LARGURA_TABELA}px)`) },
  );

  /** Nome, cor e situação **atuais** da categoria (CA-11.2), do store já carregado. */
  private readonly categorias = computed(
    () => new Map(this.categoriasStore.todas().map((categoria) => [categoria.id, categoria])),
  );

  constructor() {
    void this.categoriasStore.garantirCarga();
    effect(() => {
      this.dados.versao();
      untracked(() => void this.carregar());
    });
  }

  protected categoria(recorrencia: Recorrencia): { nome: string; cor: string; ativa: boolean } {
    return this.categorias().get(recorrencia.categoria_id) ?? CATEGORIA_AUSENTE;
  }

  protected valor(recorrencia: Recorrencia): string {
    const sinal = recorrencia.tipo === 'GASTO' ? MENOS : '+';
    return `${sinal} R$ ${formatarValor(recorrencia.valor)}`;
  }

  protected rotuloDoValor(recorrencia: Recorrencia): string {
    const tipo = recorrencia.tipo === 'GASTO' ? 'gasto' : 'receita';
    return `${tipo} de R$ ${formatarValor(recorrencia.valor)}`;
  }

  protected vigencia(recorrencia: Recorrencia): string {
    const inicio = mesPorExtenso(recorrencia.mes_inicio);
    return recorrencia.mes_fim
      ? `de ${inicio} a ${mesPorExtenso(recorrencia.mes_fim)}`
      : `desde ${inicio}`;
  }

  /** Próximo mês a gerar; ativa sem próximo = vigência terminou (F-13 Q4). */
  protected proximo(recorrencia: Recorrencia): string {
    if (recorrencia.proximo_mes) {
      return mesPorExtenso(recorrencia.proximo_mes);
    }
    if (recorrencia.status === 'ATIVA' && recorrencia.mes_fim) {
      return `Vigência terminou em ${mesPorExtenso(recorrencia.mes_fim)}`;
    }
    return '—';
  }

  protected status(recorrencia: Recorrencia): string {
    return ROTULOS_STATUS[recorrencia.status];
  }

  protected async nova(): Promise<void> {
    await this.abrirFormulario({}, 'Recorrência criada.');
  }

  protected async editar(recorrencia: Recorrencia): Promise<void> {
    await this.abrirFormulario({ recorrencia }, 'Recorrência atualizada.');
  }

  protected async pausar(recorrencia: Recorrencia): Promise<void> {
    if (await this.mudarStatus(recorrencia, 'PAUSADA')) {
      void this.avisos.mostrar('Recorrência pausada.');
      void this.carregar();
    }
  }

  /** Reativar não gera o período pausado (RN-11); o mês corrente, se devido, sai na hora (Q5). */
  protected async reativar(recorrencia: Recorrencia): Promise<void> {
    if (await this.mudarStatus(recorrencia, 'ATIVA')) {
      await this.sincronizarEAvisar(MENSAGEM_REATIVADA);
    }
  }

  /** Encerrar é definitivo (F-13 Q3): confirma antes. */
  protected async encerrar(recorrencia: Recorrencia): Promise<void> {
    const confirmado = await firstValueFrom(
      confirmar(this.dialog, {
        titulo: 'Encerrar recorrência?',
        mensagem:
          `"${recorrencia.descricao}" deixa de gerar lançamentos. ` +
          'Os lançamentos já gerados continuam. Não é possível reativar depois.',
        textoConfirmar: 'Encerrar',
      }),
    );
    if (confirmado && (await this.mudarStatus(recorrencia, 'ENCERRADA'))) {
      void this.avisos.mostrar('Recorrência encerrada.');
      void this.carregar();
    }
  }

  private async abrirFormulario(dados: DadosFormularioRecorrencia, sucesso: string): Promise<void> {
    const salva = await firstValueFrom(
      this.dialog
        .open<RecorrenciaFormDialog, DadosFormularioRecorrencia, Recorrencia>(
          RecorrenciaFormDialog,
          { data: dados, ...TAMANHO_DO_DIALOGO },
        )
        .afterClosed(),
    );
    if (salva) {
      await this.sincronizarEAvisar(sucesso);
    }
  }

  /**
   * Sincroniza (Q5), avisa uma vez ("Recorrência criada. 3 lançamentos
   * recorrentes gerados.") e recarrega: gerou algo → todas as telas
   * (`versao`); senão, só esta lista.
   */
  private async sincronizarEAvisar(sucesso: string): Promise<void> {
    const gerados = await this.sincronizacao.executar();
    void this.avisos.mostrar(gerados ? `${sucesso} ${textoDosGerados(gerados)}` : sucesso);
    if (gerados) {
      this.dados.incrementar();
    } else {
      void this.carregar();
    }
  }

  /**
   * `PATCH .../status`; devolve se deu certo. 404 (o aviso vem do
   * interceptor) e 422 (estado mudou em outro lugar) recarregam a lista;
   * planilha fora vai para o banner e a lista fica como está.
   */
  private async mudarStatus(recorrencia: Recorrencia, status: StatusRecorrencia): Promise<boolean> {
    try {
      await firstValueFrom(this.api.mudarStatus(recorrencia.id, status));
      return true;
    } catch (erro: unknown) {
      const { status: http, mensagem } = erro as ErroApi;
      if (http === 422) {
        void this.avisos.mostrar(mensagem); // o interceptor não avisa 422
      }
      if (http === 404 || http === 422) {
        void this.carregar();
      }
      return false;
    }
  }

  /** Uma busca por vez vale: resposta de busca anterior é descartada (F-07 borda 15). */
  private async carregar(): Promise<void> {
    const minha = ++this.sequencia;
    this.carregando.set(true);
    try {
      const lista = await firstValueFrom(this.api.listar());
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
}
