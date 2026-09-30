import { Routes } from '@angular/router';

const SUFIXO_TITULO = ' · Planilha Financeira';

/** Rotas de SPECS/03 §8.1, todas carregadas sob demanda (SPECS/02 §4). */
export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'resumo' },
  {
    path: 'resumo',
    title: `Resumo${SUFIXO_TITULO}`,
    loadComponent: () => import('./features/resumo/resumo.page').then((m) => m.ResumoPage),
  },
  {
    path: 'lancamentos',
    title: `Lançamentos${SUFIXO_TITULO}`,
    loadComponent: () =>
      import('./features/lancamentos/lancamentos.page').then((m) => m.LancamentosPage),
  },
  {
    path: 'historico',
    title: `Histórico${SUFIXO_TITULO}`,
    loadComponent: () => import('./features/historico/historico.page').then((m) => m.HistoricoPage),
  },
  {
    path: 'categorias',
    title: `Categorias${SUFIXO_TITULO}`,
    loadComponent: () =>
      import('./features/categorias/categorias.page').then((m) => m.CategoriasPage),
  },
  {
    path: 'recorrencias',
    title: `Recorrências${SUFIXO_TITULO}`,
    loadComponent: () =>
      import('./features/recorrencias/recorrencias.page').then((m) => m.RecorrenciasPage),
  },
  // App pessoal, sem links externos: endereço desconhecido volta ao Resumo (F-04 Q2).
  { path: '**', redirectTo: 'resumo' },
];
