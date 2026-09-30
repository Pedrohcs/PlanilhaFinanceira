import { TipoLancamento } from './enums';

/** Categoria como a API devolve (SPECS/03 §6.3; F-05). */
export interface Categoria {
  id: string;
  nome: string;
  tipo: TipoLancamento;
  cor: string;
  ativa: boolean;
  criado_em: string;
  /** Há lançamento ou recorrência com esta categoria: não pode ser excluída (F-05 Q4). */
  em_uso: boolean;
}

/** `POST /api/categorias`. */
export interface CategoriaEntrada {
  nome: string;
  tipo: TipoLancamento;
  cor: string;
}

/** `PUT /api/categorias/{id}` — sem `tipo`, que não muda (F-05 §3.3). */
export interface CategoriaAtualizacao {
  nome: string;
  cor: string;
  ativa: boolean;
}

/** Limite do nome na entrada da API (F-05 Q1). */
export const NOME_CATEGORIA_MAXIMO = 40;
