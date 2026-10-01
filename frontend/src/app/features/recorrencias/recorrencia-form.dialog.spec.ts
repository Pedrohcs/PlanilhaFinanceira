import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ApplicationRef, DebugElement, getDebugNode } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { DateAdapter, MAT_DATE_LOCALE, provideNativeDateAdapter } from '@angular/material/core';
import { MatDialog } from '@angular/material/dialog';
import { provideRouter } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { umaCategoria } from '../../../testing/categorias';
import { provideMaterialParaTestes } from '../../../testing/material';
import { Avisos } from '../../core/avisos/avisos';
import { erroInterceptor, TRATAMENTO_LOCAL } from '../../core/interceptors/erro.interceptor';
import { Recorrencia } from '../../core/models/recorrencia';
import { ConexaoStore } from '../../core/state/conexao.store';
import { AdaptadorDeDataPtBr, hoje } from '../../core/utils/adaptador-de-data';
import { mesCorrente, mesParaData, mesPorExtenso, somarMeses } from '../../core/utils/mes';
import { DadosFormularioRecorrencia, RecorrenciaFormDialog } from './recorrencia-form.dialog';

const URL_CATEGORIAS = '/api/categorias?incluir_inativas=true';
const CATEGORIAS = [
  umaCategoria({ id: 'assinaturas', nome: 'Assinaturas' }),
  umaCategoria({ id: 'velha', nome: 'Velha', ativa: false }),
  umaCategoria({ id: 'salario', nome: 'Salário', tipo: 'RECEITA', cor: '#66BB6A' }),
];
const FORMAS = [
  { codigo: 'PIX', nome: 'Pix' },
  { codigo: 'CREDITO', nome: 'Cartão de crédito' },
];
const CORRENTE = mesCorrente();
const ORIGINAL: Recorrencia = {
  id: 'r1',
  tipo: 'GASTO',
  descricao: 'Streaming',
  valor: 39.9,
  categoria_id: 'velha',
  forma_pagamento: 'CREDITO',
  dia_do_mes: 10,
  mes_inicio: somarMeses(CORRENTE, -3),
  mes_fim: null,
  status: 'ATIVA',
  ultimo_mes_gerado: CORRENTE,
  proximo_mes: somarMeses(CORRENTE, 1),
  criado_em: '2026-07-01T09:00:00',
  atualizado_em: '2026-07-01T09:00:00',
};

describe('RecorrenciaFormDialog', () => {
  let controle: HttpTestingController;
  let dialog: MatDialog;
  let avisos: { mostrar: ReturnType<typeof vi.fn> };
  let resultado: Promise<Recorrencia | undefined>;

  beforeEach(() => {
    avisos = { mostrar: vi.fn() };
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([erroInterceptor])),
        provideHttpClientTesting(),
        provideMaterialParaTestes(),
        provideRouter([]),
        provideNativeDateAdapter(),
        { provide: DateAdapter, useClass: AdaptadorDeDataPtBr },
        { provide: MAT_DATE_LOCALE, useValue: 'pt-BR' },
        { provide: Avisos, useValue: avisos },
      ],
    });
    controle = TestBed.inject(HttpTestingController);
    dialog = TestBed.inject(MatDialog);
  });

  afterEach(() => {
    dialog.closeAll();
    controle.verify();
  });

  async function estabilizar(): Promise<void> {
    await new Promise((resolver) => setTimeout(resolver));
    await TestBed.inject(ApplicationRef).whenStable();
  }

  async function abrir(recorrencia?: Recorrencia): Promise<void> {
    const referencia = dialog.open<RecorrenciaFormDialog, DadosFormularioRecorrencia, Recorrencia>(
      RecorrenciaFormDialog,
      { data: { recorrencia } },
    );
    resultado = firstValueFrom(referencia.afterClosed());
    await estabilizar();
    // Os stores carregam uma vez só: na 2ª abertura não há pedido novo.
    controle.match(URL_CATEGORIAS).forEach((pedido) => pedido.flush(CATEGORIAS));
    controle.match('/api/formas-pagamento').forEach((pedido) => pedido.flush(FORMAS));
    await estabilizar();
  }

  function container(): HTMLElement {
    return document.querySelector<HTMLElement>('mat-dialog-container')!;
  }

  function texto(el: Element | null | undefined): string {
    return (el?.textContent ?? '').replace(/ /g, ' ').replace(/\s+/g, ' ').trim();
  }

  function campo(nome: string): HTMLInputElement {
    return container().querySelector<HTMLInputElement>(`[formcontrolname="${nome}"]`)!;
  }

  async function digitar(nome: string, valor: string): Promise<void> {
    const elemento = campo(nome);
    elemento.value = valor;
    elemento.dispatchEvent(new Event('input'));
    elemento.dispatchEvent(new Event('blur'));
    await estabilizar();
  }

  async function abrirPainel(nome: string): Promise<void> {
    campo(nome).querySelector<HTMLElement>('.mat-mdc-select-trigger')!.click();
    await estabilizar();
  }

  async function opcoes(nome: string): Promise<string[]> {
    await abrirPainel(nome);
    const textos = Array.from(document.querySelectorAll('mat-option')).map(texto);
    document.querySelector<HTMLElement>('.cdk-overlay-transparent-backdrop')?.click();
    await estabilizar();
    return textos;
  }

  async function escolher(nome: string, rotulo: string): Promise<void> {
    await abrirPainel(nome);
    Array.from(document.querySelectorAll<HTMLElement>('mat-option'))
      .find((opcao) => texto(opcao) === rotulo)!
      .click();
    await estabilizar();
  }

  /** Escolhe o mês no datepicker de início (0) ou de fim (1), como o usuário. */
  async function escolherMes(qual: 0 | 1, mes: string): Promise<void> {
    const elemento = container().querySelectorAll('mat-datepicker')[qual];
    (getDebugNode(elemento) as DebugElement).triggerEventHandler('monthSelected', mesParaData(mes));
    await estabilizar();
  }

  function botaoMes(qual: 'inicio' | 'fim'): string {
    return texto(container().querySelector(`.mes button.${qual}`));
  }

  async function salvar(): Promise<void> {
    container().querySelector<HTMLButtonElement>('button[type="submit"]')!.click();
    await estabilizar();
  }

  function erroDe(seletor: string): string {
    return texto(container().querySelector(seletor));
  }

  it('novo_e_edicao__CA_F13_22', async () => {
    await abrir();

    expect(texto(container().querySelector('h2'))).toBe('Nova recorrência');
    expect(texto(campo('tipo').querySelector('.mat-mdc-select-value'))).toBe('Gasto');
    expect(campo('dia_do_mes').value).toBe(String(hoje().getDate()));
    expect(botaoMes('inicio')).toBe(mesPorExtenso(CORRENTE));
    expect(botaoMes('fim')).toBe('Sem fim');
    expect(texto(container())).toContain('Nos meses sem esse dia, usa o último dia do mês.');
    expect(await opcoes('categoria_id')).toEqual(['Assinaturas']); // só ativas do tipo (RN-04)

    await digitar('valor', '39,9');
    expect(campo('valor').value).toBe('39,90'); // reformatado ao sair
    await digitar('descricao', '  Streaming  ');
    await escolher('categoria_id', 'Assinaturas');
    await escolher('forma_pagamento', 'Cartão de crédito');
    await digitar('dia_do_mes', '31');
    await escolherMes(1, somarMeses(CORRENTE, 5));
    await salvar();

    const pedido = controle.expectOne('/api/recorrencias');
    expect(pedido.request.method).toBe('POST');
    expect(pedido.request.context.get(TRATAMENTO_LOCAL)).toBe(true);
    expect(pedido.request.body).toEqual({
      tipo: 'GASTO',
      descricao: 'Streaming',
      valor: 39.9,
      categoria_id: 'assinaturas',
      forma_pagamento: 'CREDITO',
      dia_do_mes: 31,
      mes_inicio: CORRENTE,
      mes_fim: somarMeses(CORRENTE, 5),
    });
    pedido.flush({ ...ORIGINAL, id: 'nova' });
    expect((await resultado)?.id).toBe('nova');

    // Edição: pré-preenchida; a categoria atual inativa aparece (F-08 Q1).
    await abrir(ORIGINAL);
    expect(texto(container().querySelector('h2'))).toBe('Editar recorrência');
    expect(campo('valor').value).toBe('39,90');
    expect(botaoMes('inicio')).toBe(mesPorExtenso(ORIGINAL.mes_inicio));
    expect(await opcoes('categoria_id')).toEqual(['Assinaturas', 'Velha (inativa)']);
    expect(container().querySelector('.retroativo')).toBeNull(); // já gerou: nada retroativo

    await escolher('tipo', 'Receita'); // troca de tipo limpa a categoria de gasto
    expect(await opcoes('forma_pagamento')).toEqual(['Não informar', 'Pix', 'Cartão de crédito']);
    await escolher('categoria_id', 'Salário');
    await escolher('forma_pagamento', 'Não informar');
    await salvar();
    const put = controle.expectOne('/api/recorrencias/r1');
    expect(put.request.method).toBe('PUT');
    expect(put.request.body).toMatchObject({
      tipo: 'RECEITA',
      categoria_id: 'salario',
      forma_pagamento: null,
    });
    put.flush(ORIGINAL);
  });

  it('erros_no_campo__CA_F13_23', async () => {
    await abrir();
    await salvar(); // vazio: nada é enviado
    controle.expectNone('/api/recorrencias');
    expect(erroDe('mat-error')).toBe('Informe um valor maior que zero.');

    await digitar('valor', '10');
    await digitar('descricao', 'Aluguel');
    await escolher('categoria_id', 'Assinaturas');
    await escolher('forma_pagamento', 'Pix');
    await digitar('dia_do_mes', '32');
    expect(texto(container())).toContain('Informe um dia de 1 a 31.');
    await digitar('dia_do_mes', '5');
    // 409 de categoria → no campo categoria, sem aviso global.
    await salvar();
    controle.expectOne('/api/recorrencias').flush(
      { erro: { codigo: 'CATEGORIA_INATIVA', mensagem: 'A categoria "Assinaturas" está inativa.', detalhes: [] } },
      { status: 409, statusText: 'x' },
    ); // prettier-ignore
    await estabilizar();
    // A lista de categorias é recarregada: a escolhida foi desativada em outro lugar.
    controle
      .expectOne(URL_CATEGORIAS)
      .flush([
        umaCategoria({ id: 'assinaturas', nome: 'Assinaturas', ativa: false }),
        umaCategoria({ id: 'moradia', nome: 'Moradia' }),
      ]);
    await estabilizar();
    expect(texto(container())).toContain('A categoria "Assinaturas" está inativa.');
    expect(avisos.mostrar).not.toHaveBeenCalled();
    expect(await opcoes('categoria_id')).toEqual(['Moradia']);

    // 422 com campo → no campo, diálogo aberto com os dados (CA-01.4).
    await escolher('categoria_id', 'Moradia');
    await salvar();
    controle.expectOne('/api/recorrencias').flush(
      {
        erro: {
          codigo: 'VALIDACAO',
          mensagem: 'O mês de fim deve ser igual ou posterior ao mês de início.',
          detalhes: [{ campo: 'mes_fim', mensagem: 'O mês de fim deve ser igual ou posterior ao mês de início.' }],
        },
      },
      { status: 422, statusText: 'x' },
    ); // prettier-ignore
    await estabilizar();
    expect(erroDe('.mes .erro')).toBe('O mês de fim deve ser igual ou posterior ao mês de início.');
    expect(campo('descricao').value).toBe('Aluguel');

    // O usuário corrige o campo apontado (o erro do servidor sai ao mudar o campo).
    await escolherMes(1, somarMeses(CORRENTE, 2));
    expect(container().querySelector('.mes .erro')).toBeNull();

    // 503 → banner; o diálogo continua aberto.
    await salvar();
    controle
      .expectOne('/api/recorrencias')
      .flush(
        { erro: { codigo: 'PLANILHA_INDISPONIVEL', mensagem: 'Fora do ar.', detalhes: [] } },
        { status: 503, statusText: 'x' },
      );
    await estabilizar();
    expect(TestBed.inject(ConexaoStore).mensagem()).toBe('Fora do ar.');
    expect(container()).not.toBeNull();
  });

  it('aviso_retroativo_e_vigencia__CA_F13_24', async () => {
    await abrir();
    expect(container().querySelector('.retroativo')).toBeNull(); // início no mês corrente

    const tresAtras = somarMeses(CORRENTE, -3);
    await escolherMes(0, tresAtras);
    expect(botaoMes('inicio')).toBe(mesPorExtenso(tresAtras));
    expect(texto(container().querySelector('.retroativo'))).toBe(
      `Os lançamentos de ${mesPorExtenso(tresAtras)} a ${mesPorExtenso(CORRENTE)} serão gerados ao salvar.`,
    );

    // Fim antes do corrente limita o que sai; um mês só, no singular.
    await escolherMes(1, tresAtras);
    expect(texto(container().querySelector('.retroativo'))).toBe(
      `O lançamento de ${mesPorExtenso(tresAtras)} será gerado ao salvar.`,
    );

    // Fim antes do início: erro no campo, nada é enviado.
    await escolherMes(1, somarMeses(CORRENTE, -4));
    expect(erroDe('.mes .erro')).toBe('O mês de fim deve ser igual ou posterior ao mês de início.');
    await digitar('valor', '10');
    await digitar('descricao', 'Aluguel');
    await escolher('categoria_id', 'Assinaturas');
    await escolher('forma_pagamento', 'Pix');
    await salvar();
    controle.expectNone('/api/recorrencias');

    // "Sem fim" de novo: o erro some.
    container().querySelector<HTMLButtonElement>('button.sem-fim')!.click();
    await estabilizar();
    expect(botaoMes('fim')).toBe('Sem fim');
    expect(container().querySelector('.mes .erro')).toBeNull();
  });
});
