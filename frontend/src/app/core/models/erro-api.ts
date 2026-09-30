/**
 * Erro da API já interpretado (SPECS/03 §6.2, §8.4).
 *
 * O `erro.interceptor` converte toda resposta de erro neste formato; quem fez
 * a chamada recebe um `ErroApi`, nunca um `HttpErrorResponse`.
 */
export interface ErroApi {
  /** Status HTTP; 0 quando não houve resposta. */
  status: number;
  /** Código de `03` §6.2, ou o local `BACKEND_INDISPONIVEL`. */
  codigo: string;
  /** Mensagem em pt-BR, pronta para exibir — a do backend, sem reescrita. */
  mensagem: string;
  detalhes: DetalheErro[];
}

export interface DetalheErro {
  campo: string;
  mensagem: string;
}

/** Corpo de erro da API (`03` §6.2). */
export interface EnvelopeErro {
  erro: { codigo: string; mensagem: string; detalhes?: DetalheErro[] };
}

/**
 * Código que **só existe no frontend**: o backend não respondeu (F-04 Q3,
 * `03` §8.4). Não faz parte do contrato da API.
 */
export const BACKEND_INDISPONIVEL = 'BACKEND_INDISPONIVEL';
export const MENSAGEM_BACKEND_INDISPONIVEL =
  'O servidor do aplicativo não está respondendo. Verifique se o backend está rodando e tente novamente.';

/** Mesma mensagem genérica do backend para `ERRO_INTERNO` (`03` §6.2). */
export const ERRO_INTERNO = 'ERRO_INTERNO';
export const MENSAGEM_ERRO_INTERNO = 'Erro interno. Consulte o log do servidor.';
