import { registerLocaleData } from '@angular/common';
import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';
import localePt from '@angular/common/locales/pt';
import {
  ApplicationConfig,
  DEFAULT_CURRENCY_CODE,
  inject,
  LOCALE_ID,
  provideBrowserGlobalErrorListeners,
  provideEnvironmentInitializer,
  provideZonelessChangeDetection,
} from '@angular/core';
import { DateAdapter, MAT_DATE_LOCALE, provideNativeDateAdapter } from '@angular/material/core';
import { MatIconRegistry } from '@angular/material/icon';
import { provideRouter } from '@angular/router';
import { routes } from './app.routes';
import { erroInterceptor } from './core/interceptors/erro.interceptor';
import { provideVerificacaoDeConexao } from './core/state/conexao.store';
import { AdaptadorDeDataPtBr } from './core/utils/adaptador-de-data';

// Dados de pt-BR para CurrencyPipe, DatePipe e DecimalPipe (RNF-03).
registerLocaleData(localePt);

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    // Redundante na v22 (sem zone.js o padrão já é zoneless), mantido explícito
    // para que a garantia fique visível no código (SPECS/02 §4).
    provideZonelessChangeDetection(),
    provideRouter(routes),
    provideHttpClient(withFetch(), withInterceptors([erroInterceptor])),
    // Health na abertura, sem segurar a 1ª renderização (SPECS/03 §7.2, F-04 Q4).
    provideVerificacaoDeConexao(),
    { provide: LOCALE_ID, useValue: 'pt-BR' },
    { provide: DEFAULT_CURRENCY_CODE, useValue: 'BRL' },
    // Datepicker (seletor de mês, F-04 Q7; formulários em F-06), em pt-BR.
    provideNativeDateAdapter(),
    // Entende `dd/mm/aaaa` digitado; o nativo usa o formato americano (F-06, T-016).
    { provide: DateAdapter, useClass: AdaptadorDeDataPtBr },
    { provide: MAT_DATE_LOCALE, useValue: 'pt-BR' },
    // A fonte Material Symbols vem do pacote `material-symbols` (ADR-15); sem isto o `<mat-icon>`
    // procuraria a antiga "Material Icons" e mostraria o nome do ícone em texto.
    provideEnvironmentInitializer(() =>
      inject(MatIconRegistry).setDefaultFontSetClass('material-symbols-outlined'),
    ),
  ],
};
