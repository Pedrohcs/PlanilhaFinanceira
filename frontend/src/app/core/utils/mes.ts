/**
 * Mês de referência no formato `YYYY-MM` (SPECS/02 §3, REQ-04).
 *
 * Aritmética de mês no frontend é permitida: não é cálculo de total (RN-16).
 */

const PADRAO_MES = /^(\d{4})-(0[1-9]|1[0-2])$/;

const EXTENSO = new Intl.DateTimeFormat('pt-BR', { month: 'long', year: 'numeric' });

const ABREVIADOS = [
  'jan',
  'fev',
  'mar',
  'abr',
  'mai',
  'jun',
  'jul',
  'ago',
  'set',
  'out',
  'nov',
  'dez',
];

export function mesValido(mes: string | null | undefined): mes is string {
  return typeof mes === 'string' && PADRAO_MES.test(mes);
}

/** Mês da data informada (padrão: agora, no relógio local). */
export function mesCorrente(hoje: Date = new Date()): string {
  return dataParaMes(hoje);
}

export function proximoMes(mes: string): string {
  return somarMeses(mes, 1);
}

export function mesAnterior(mes: string): string {
  return somarMeses(mes, -1);
}

/** `2026-09` → `setembro de 2026` (RNF-03). */
export function mesPorExtenso(mes: string): string {
  return EXTENSO.format(mesParaData(mes));
}

/** `2025-10` → `out/25`: rótulo do eixo dos gráficos do histórico (F-11 §3.2.4). */
export function mesAbreviado(mes: string): string {
  const [ano, numero] = partes(mes);
  return `${ABREVIADOS[numero - 1]}/${String(ano % 100).padStart(2, '0')}`;
}

/** Meses de `inicio` a `fim`, inclusive nas pontas (0 ou menos se `fim` vem antes). */
export function mesesNoPeriodo(inicio: string, fim: string): number {
  const [anoInicio, numeroInicio] = partes(inicio);
  const [anoFim, numeroFim] = partes(fim);
  return (anoFim - anoInicio) * 12 + (numeroFim - numeroInicio) + 1;
}

/** Soma (ou subtrai) meses de um `YYYY-MM`. */
export function somarMeses(mes: string, quantidade: number): string {
  const [ano, numero] = partes(mes);
  return dataParaMes(new Date(ano, numero - 1 + quantidade, 1));
}

/** Primeiro dia do mês, à meia-noite local — o que o datepicker usa. */
export function mesParaData(mes: string): Date {
  const [ano, numero] = partes(mes);
  return new Date(ano, numero - 1, 1);
}

export function dataParaMes(data: Date): string {
  const numero = String(data.getMonth() + 1).padStart(2, '0');
  return `${String(data.getFullYear()).padStart(4, '0')}-${numero}`;
}

function partes(mes: string): [number, number] {
  const encontrado = PADRAO_MES.exec(mes);
  if (!encontrado) {
    throw new Error(`Mês fora do formato YYYY-MM: ${mes}`);
  }
  return [Number(encontrado[1]), Number(encontrado[2])];
}
