import {
  EnvironmentProviders,
  inject,
  Injectable,
  provideAppInitializer,
  signal,
} from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { HealthApi } from '../api/health.api';
import { Avisos } from '../avisos/avisos';
import { ErroApi } from '../models/erro-api';
import { RespostaHealth } from '../models/health';
import { DadosStore } from './dados.store';
import { SincronizacaoRecorrencias, textoDosGerados } from './sincronizacao';

export type EstadoConexao = 'verificando' | 'ok' | 'falha';

export const MENSAGEM_CONEXAO_RESTABELECIDA = 'Conexão com a planilha restabelecida.';
export const DURACAO_AVISO_RECONEXAO_MS = 4000;

/** Só por garantia: o backend sempre manda `erro` quando está degradado (`03` §6.3). */
const MENSAGEM_DEGRADADO_SEM_DETALHE = 'Google Sheets indisponível no momento. Tente novamente.';

/**
 * Estado da conexão com o backend e a planilha (SPECS/03 §7.2, §8.2) — a
 * única fonte do banner de conexão.
 *
 * `'verificando'` é só interno: não há indicador na tela (F-04 Q4).
 */
@Injectable({ providedIn: 'root' })
export class ConexaoStore {
  private readonly health = inject(HealthApi);
  private readonly avisos = inject(Avisos);
  private readonly dados = inject(DadosStore);
  private readonly sincronizacao = inject(SincronizacaoRecorrencias);

  private readonly _estado = signal<EstadoConexao>('verificando');
  private readonly _mensagem = signal<string | null>(null);
  private readonly _tentando = signal(false);

  readonly estado = this._estado.asReadonly();
  /** Mensagem da última falha, exibida sem reescrita (F-04 §3.3). */
  readonly mensagem = this._mensagem.asReadonly();
  /** Há um `GET /api/health` em curso: o botão fica desabilitado (CA-F04.26). */
  readonly tentando = this._tentando.asReadonly();

  /** 503 ou backend fora do ar: o banner aparece com a mensagem mais recente. */
  registrarFalha(erro: ErroApi): void {
    this._mensagem.set(erro.mensagem);
    this._estado.set('falha');
  }

  registrarOk(): void {
    this._mensagem.set(null);
    this._estado.set('ok');
  }

  /**
   * Consulta o health e atualiza o estado; devolve `true` se a planilha
   * respondeu. Uma chamada por vez: pedidos durante outra são ignorados.
   */
  async verificar(): Promise<boolean> {
    if (this._tentando()) {
      return false;
    }
    this._tentando.set(true);
    try {
      return this.aplicar(await firstValueFrom(this.health.verificar()));
    } catch (erro: unknown) {
      // Backend fora do ar: o interceptor já pôs o banner. Qualquer outra
      // falha do próprio health também não pode passar em silêncio.
      if (this._estado() !== 'falha' && eErroApi(erro)) {
        this.registrarFalha(erro);
      }
      return false;
    } finally {
      this._tentando.set(false);
    }
  }

  /**
   * Abertura do app (SPECS/03 §7.2): health e, se a planilha respondeu, a
   * sincronização das recorrências, uma vez (F-13 §3.4.1). Gerou algo → aviso
   * e as telas recarregam; nada → silêncio.
   */
  async abrir(): Promise<void> {
    if (!(await this.verificar())) {
      return;
    }
    const gerados = await this.sincronizacao.executar();
    if (gerados) {
      void this.avisos.mostrar(textoDosGerados(gerados));
      this.dados.incrementar();
    }
  }

  /**
   * "Tentar novamente" do banner (CA-16.2): se voltou, sincroniza as
   * recorrências (o app pode ter aberto sem planilha — F-13 §3.4.4), avisa
   * uma vez e recarrega a tela uma vez (F-04 Q5).
   */
  async tentarNovamente(): Promise<void> {
    if (!(await this.verificar())) {
      return;
    }
    const gerados = await this.sincronizacao.executar();
    const mensagem = gerados
      ? `${MENSAGEM_CONEXAO_RESTABELECIDA} ${textoDosGerados(gerados)}`
      : MENSAGEM_CONEXAO_RESTABELECIDA;
    void this.avisos.mostrar(mensagem, DURACAO_AVISO_RECONEXAO_MS);
    this.dados.incrementar();
  }

  private aplicar(resposta: RespostaHealth): boolean {
    if (resposta.status === 'ok') {
      this.registrarOk();
      return true;
    }
    const erro = resposta.planilha.erro;
    this.registrarFalha({
      status: 200,
      codigo: erro?.codigo ?? 'PLANILHA_INDISPONIVEL',
      mensagem: erro?.mensagem ?? MENSAGEM_DEGRADADO_SEM_DETALHE,
      detalhes: [],
    });
    return false;
  }
}

/**
 * Verifica a conexão — e sincroniza as recorrências — na abertura **sem
 * segurar a primeira renderização** (SPECS/03 §7.2; F-04 Q4): o inicializador
 * dispara o health e retorna.
 */
export function provideVerificacaoDeConexao(): EnvironmentProviders {
  return provideAppInitializer(() => {
    void inject(ConexaoStore).abrir();
  });
}

function eErroApi(valor: unknown): valor is ErroApi {
  return (
    typeof valor === 'object' &&
    valor !== null &&
    typeof (valor as ErroApi).codigo === 'string' &&
    typeof (valor as ErroApi).mensagem === 'string'
  );
}
