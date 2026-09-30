import { registerLocaleData } from '@angular/common';
import { provideHttpClient, withFetch } from '@angular/common/http';
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
import { MatIconRegistry } from '@angular/material/icon';
import { provideRouter } from '@angular/router';
import { routes } from './app.routes';

// Dados de pt-BR para CurrencyPipe, DatePipe e DecimalPipe (RNF-03).
registerLocaleData(localePt);

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    // Redundante na v22 (sem zone.js o padrão já é zoneless), mantido explícito
    // para que a garantia fique visível no código (SPECS/02 §4).
    provideZonelessChangeDetection(),
    provideRouter(routes),
    provideHttpClient(withFetch()),
    { provide: LOCALE_ID, useValue: 'pt-BR' },
    { provide: DEFAULT_CURRENCY_CODE, useValue: 'BRL' },
    // O `index.html` carrega a fonte Material Symbols; sem isto o `<mat-icon>`
    // procuraria a antiga "Material Icons" e mostraria o nome do ícone em texto.
    provideEnvironmentInitializer(() =>
      inject(MatIconRegistry).setDefaultFontSetClass('material-symbols-outlined'),
    ),
  ],
};
