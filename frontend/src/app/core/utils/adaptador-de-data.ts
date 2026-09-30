import { Injectable } from '@angular/core';
import { NativeDateAdapter } from '@angular/material/core';

const DD_MM_AAAA = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/;

/**
 * Adaptador de datas do Material que **entende `dd/mm/aaaa`** (F-06 §3.2).
 *
 * O `NativeDateAdapter` exibe em pt-BR, mas interpreta o texto digitado com
 * `Date.parse`, no formato americano: `30/09/2026` seria inválido e
 * `05/09/2026` viraria 9 de maio. Aqui só a interpretação muda; a exibição
 * continua a do adaptador nativo.
 */
@Injectable()
export class AdaptadorDeDataPtBr extends NativeDateAdapter {
  override parse(valor: unknown, formato: object): Date | null {
    if (typeof valor !== 'string') {
      return super.parse(valor, formato);
    }
    const texto = valor.trim();
    if (!texto) {
      return null;
    }
    const partes = DD_MM_AAAA.exec(texto);
    if (!partes) {
      return this.invalid();
    }
    const [dia, mes, ano] = [Number(partes[1]), Number(partes[2]), Number(partes[3])];
    const data = new Date(ano, mes - 1, dia);
    // 29/02/2025 viraria 01/03/2025 no `Date`: dia inexistente é inválido.
    if (data.getFullYear() !== ano || data.getMonth() !== mes - 1 || data.getDate() !== dia) {
      return this.invalid();
    }
    return data;
  }
}

/** Data local → `YYYY-MM-DD`, o formato da API (`SPECS/02` §3). */
export function dataParaIso(data: Date): string {
  const mes = String(data.getMonth() + 1).padStart(2, '0');
  const dia = String(data.getDate()).padStart(2, '0');
  return `${String(data.getFullYear()).padStart(4, '0')}-${mes}-${dia}`;
}

/** Hoje, à meia-noite local (valor inicial do campo data — RN-02). */
export function hoje(): Date {
  const agora = new Date();
  return new Date(agora.getFullYear(), agora.getMonth(), agora.getDate());
}

/**
 * `2026-09-30` → `30/09/2026` (RNF-03), só rearranjando o texto: sem `Date`,
 * sem fuso, e sem o `DatePipe` (que puxaria a formatação de datas do
 * `@angular/common` para o pacote inicial — T-018).
 */
export function exibirData(iso: string): string {
  const [ano, mes, dia] = iso.split('-');
  return `${dia}/${mes}/${ano}`;
}
