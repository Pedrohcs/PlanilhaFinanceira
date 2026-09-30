import {
  HttpContext,
  HttpContextToken,
  HttpErrorResponse,
  HttpInterceptorFn,
} from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { Avisos } from '../avisos/avisos';
import {
  BACKEND_INDISPONIVEL,
  EnvelopeErro,
  ERRO_INTERNO,
  ErroApi,
  MENSAGEM_BACKEND_INDISPONIVEL,
  MENSAGEM_ERRO_INTERNO,
} from '../models/erro-api';
import { ConexaoStore } from '../state/conexao.store';

/** Status que, sem o envelope da API, significam "o backend não respondeu" (F-04 Q3). */
const SEM_BACKEND = new Set([0, 502, 504]);

/**
 * Marcador de requisição: "este 409 eu mostro no campo" (F-06 Q3). Usado por
 * formulários que exibem o erro no próprio campo, para a mesma frase não
 * aparecer também como aviso.
 */
export const TRATAMENTO_LOCAL = new HttpContextToken<boolean>(() => false);

/** Opção das APIs de escrita: `tratamentoLocal` = quem chama mostra o 409 no campo. */
export interface OpcoesDeEscrita {
  tratamentoLocal?: boolean;
}

/** `HttpContext` com `TRATAMENTO_LOCAL` ligado, quando pedido. */
export function contextoDeErro(tratamentoLocal = false): HttpContext {
  return new HttpContext().set(TRATAMENTO_LOCAL, tratamentoLocal);
}

/**
 * Converte toda resposta de erro em `ErroApi` e a repassa a quem chamou
 * (SPECS/03 §8.4; F-04 §3.3):
 *
 * - 503 ou backend fora do ar → `ConexaoStore` (banner), sem snackbar;
 * - 422 → nada global: o formulário marca os campos por `detalhes`;
 * - 409 com `TRATAMENTO_LOCAL` → nada global: o formulário mostra no campo;
 * - demais → snackbar com a mensagem do backend.
 */
export const erroInterceptor: HttpInterceptorFn = (requisicao, proximo) => {
  const conexao = inject(ConexaoStore);
  const avisos = inject(Avisos);

  return proximo(requisicao).pipe(
    catchError((resposta: unknown) => {
      if (!(resposta instanceof HttpErrorResponse)) {
        return throwError(() => resposta);
      }
      const erro = paraErroApi(resposta);
      const mostradoNoCampo = erro.status === 409 && requisicao.context.get(TRATAMENTO_LOCAL);
      if (erro.codigo === BACKEND_INDISPONIVEL || erro.status === 503) {
        conexao.registrarFalha(erro);
      } else if (erro.status !== 422 && !mostradoNoCampo) {
        void avisos.mostrar(erro.mensagem);
      }
      return throwError(() => erro);
    }),
  );
};

export function paraErroApi(resposta: HttpErrorResponse): ErroApi {
  const envelope = lerEnvelope(resposta.error);
  if (envelope) {
    return {
      status: resposta.status,
      codigo: envelope.erro.codigo,
      mensagem: envelope.erro.mensagem,
      detalhes: envelope.erro.detalhes ?? [],
    };
  }
  if (SEM_BACKEND.has(resposta.status)) {
    return {
      status: resposta.status,
      codigo: BACKEND_INDISPONIVEL,
      mensagem: MENSAGEM_BACKEND_INDISPONIVEL,
      detalhes: [],
    };
  }
  return {
    status: resposta.status,
    codigo: ERRO_INTERNO,
    mensagem: MENSAGEM_ERRO_INTERNO,
    detalhes: [],
  };
}

function lerEnvelope(corpo: unknown): EnvelopeErro | null {
  if (typeof corpo !== 'object' || corpo === null || !('erro' in corpo)) {
    return null;
  }
  const erro = (corpo as { erro: unknown }).erro;
  if (
    typeof erro === 'object' &&
    erro !== null &&
    typeof (erro as { codigo?: unknown }).codigo === 'string' &&
    typeof (erro as { mensagem?: unknown }).mensagem === 'string'
  ) {
    return corpo as EnvelopeErro;
  }
  return null;
}
