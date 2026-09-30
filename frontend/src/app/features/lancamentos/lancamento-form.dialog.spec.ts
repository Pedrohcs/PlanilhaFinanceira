import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ApplicationRef } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { DateAdapter, MAT_DATE_LOCALE, provideNativeDateAdapter } from '@angular/material/core';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { provideRouter } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { umaCategoria } from '../../../testing/categorias';
import { provideMaterialParaTestes } from '../../../testing/material';
import { Avisos } from '../../core/avisos/avisos';
import { erroInterceptor } from '../../core/interceptors/erro.interceptor';
import { Categoria } from '../../core/models/categoria';
import { MENSAGEM_BACKEND_INDISPONIVEL } from '../../core/models/erro-api';
import { Lancamento } from '../../core/models/lancamento';
import { ConexaoStore } from '../../core/state/conexao.store';
import { AdaptadorDeDataPtBr, dataParaIso, hoje } from '../../core/utils/adaptador-de-data';
import { DadosFormularioLancamento, LancamentoFormDialog } from './lancamento-form.dialog';

const URL_CATEGORIAS = '/api/categorias?incluir_inativas=true';
const CATEGORIAS: Categoria[] = [
  umaCategoria({ id: 'mercado', nome: 'Mercado' }),
  umaCategoria({ id: 'velha', nome: 'Velha', ativa: false }),
  umaCategoria({ id: 'salario', nome: 'Salário', tipo: 'RECEITA', cor: '#66BB6A' }),
];
const FORMAS = [
  { codigo: 'PIX', nome: 'Pix' },
  { codigo: 'CREDITO', nome: 'Cartão de crédito' },
];

describe('LancamentoFormDialog', () => {
  let controle: HttpTestingController;
  let dialog: MatDialog;
  let avisos: { mostrar: ReturnType<typeof vi.fn> };
  let resultado: Promise<Lancamento | undefined>;

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

  async function abrir(tipo: 'GASTO' | 'RECEITA', categorias = CATEGORIAS): Promise<void> {
    const referencia: MatDialogRef<LancamentoFormDialog, Lancamento> = dialog.open(
      LancamentoFormDialog,
      { data: { tipo } satisfies DadosFormularioLancamento },
    );
    resultado = firstValueFrom(referencia.afterClosed());
    await estabilizar();
    controle.expectOne(URL_CATEGORIAS).flush(categorias);
    controle.expectOne('/api/formas-pagamento').flush(FORMAS);
    await estabilizar();
  }

  function container(): HTMLElement {
    return document.querySelector<HTMLElement>('mat-dialog-container')!;
  }

  function campo(nome: string): HTMLInputElement {
    return container().querySelector<HTMLInputElement>(`[formcontrolname="${nome}"]`)!;
  }

  async function digitar(nome: string, texto: string): Promise<void> {
    const elemento = campo(nome);
    elemento.value = texto;
    elemento.dispatchEvent(new Event('input'));
    elemento.dispatchEvent(new Event('blur'));
    await estabilizar();
  }

  async function abrirPainel(nome: string): Promise<void> {
    campo(nome).querySelector<HTMLElement>('.mat-mdc-select-trigger')!.click();
    await estabilizar();
  }

  /** Opções do select, fechando o painel em seguida (clique no fundo do painel). */
  async function opcoes(nome: string): Promise<string[]> {
    await abrirPainel(nome);
    const textos = Array.from(document.querySelectorAll('mat-option')).map(
      (opcao) => opcao.textContent?.trim() ?? '',
    );
    // O select usa fundo transparente; o `.cdk-overlay-backdrop` comum é o do diálogo.
    document.querySelector<HTMLElement>('.cdk-overlay-transparent-backdrop')?.click();
    await estabilizar();
    return textos;
  }

  async function escolher(nome: string, texto: string): Promise<void> {
    await abrirPainel(nome);
    const opcao = Array.from(document.querySelectorAll<HTMLElement>('mat-option')).find(
      (item) => item.textContent?.trim() === texto,
    );
    if (!opcao) {
      throw new Error(`opção "${texto}" não encontrada em ${nome}`);
    }
    opcao.click();
    await estabilizar();
  }

  function botao(texto: string): HTMLButtonElement {
    return Array.from(container().querySelectorAll<HTMLButtonElement>('button')).find(
      (item) => item.textContent?.trim() === texto,
    )!;
  }

  async function salvar(): Promise<void> {
    container().querySelector<HTMLButtonElement>('button[type="submit"]')!.click();
    await estabilizar();
  }

  function erros(): string[] {
    return Array.from(container().querySelectorAll('mat-error')).map(
      (erro) => erro.textContent?.trim() ?? '',
    );
  }

  async function preencherGasto(): Promise<void> {
    await digitar('valor', '1.234,5');
    await digitar('descricao', '  Almoço  ');
    await escolher('categoria_id', 'Mercado');
    await escolher('forma_pagamento', 'Pix');
  }

  it('abre_com_hoje_e_categorias_do_tipo__CA_01_1', async () => {
    await abrir('GASTO');

    expect(container().querySelector('h2')?.textContent).toBe('Registrar gasto');
    const formato = new Intl.DateTimeFormat('pt-BR', {
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
    });
    expect(campo('data').value).toBe(formato.format(hoje()));
    expect(document.activeElement).toBe(campo('valor')); // foco no valor
    expect(await opcoes('categoria_id')).toEqual(['Mercado']); // só ativas de gasto
    expect(campo('forma_pagamento').textContent?.trim()).toBe(''); // nada pré-selecionado (Q4)
  });

  it('receita_so_ativas_de_receita__CA_02_1', async () => {
    await abrir('RECEITA');

    expect(container().querySelector('h2')?.textContent).toBe('Registrar receita');
    expect(await opcoes('categoria_id')).toEqual(['Salário']);
    expect(await opcoes('forma_pagamento')).toEqual(['Não informar', 'Pix', 'Cartão de crédito']);
  });

  it('invalido_nao_envia__CA_01_3', async () => {
    await abrir('GASTO');

    await salvar();

    expect(erros()).toEqual([
      'Informe um valor maior que zero.',
      'Informe a descrição.',
      'Escolha uma categoria.',
      'Escolha a forma de pagamento.',
    ]);
    await digitar('valor', '0,001');
    expect(erros()).toContain('Use no máximo 2 casas decimais.');
    await digitar('valor', 'abc');
    expect(erros()).toContain('Valor inválido. Ex.: 1.234,56');
    await digitar('data', '29/02/2025');
    expect(erros()).toContain('Informe uma data válida.');
    controle.expectNone('/api/lancamentos');
  });

  it('salva_com_corpo_certo__CA_01_2', async () => {
    await abrir('GASTO');
    await preencherGasto();
    expect(campo('valor').value).toBe('1.234,50'); // reformatado ao sair (Q2)

    await salvar();
    container().querySelector<HTMLButtonElement>('button[type="submit"]')!.click(); // duplo clique
    await estabilizar();

    const post = controle.expectOne('/api/lancamentos'); // uma só (borda 11)
    expect(post.request.body).toEqual({
      data: dataParaIso(hoje()),
      tipo: 'GASTO',
      descricao: 'Almoço',
      valor: 1234.5,
      categoria_id: 'mercado',
      forma_pagamento: 'PIX',
      observacao: null,
    });
    expect(botao('Salvando…')).toBeDefined();
    post.flush({ ...post.request.body, id: 'novo' });
    await estabilizar();

    expect((await resultado)?.id).toBe('novo');
    expect(dialog.openDialogs).toHaveLength(0);
  });

  it('receita_sem_forma__CA_02_2', async () => {
    await abrir('RECEITA');
    await digitar('valor', '5000');
    await digitar('descricao', 'Salário de setembro');
    await escolher('categoria_id', 'Salário');
    await digitar('observacao', '   ');

    await salvar();

    const post = controle.expectOne('/api/lancamentos');
    expect(post.request.body.forma_pagamento).toBeNull();
    expect(post.request.body.observacao).toBeNull();
    expect(post.request.body.valor).toBe(5000);
    post.flush({ ...post.request.body, id: 'r1' });
    await estabilizar();
  });

  it('falha_422_marca_o_campo_e_mantem_os_dados__CA_01_4', async () => {
    await abrir('GASTO');
    await preencherGasto();
    await salvar();

    controle.expectOne('/api/lancamentos').flush(
      {
        erro: {
          codigo: 'VALIDACAO',
          mensagem: 'Dados inválidos.',
          detalhes: [{ campo: 'descricao', mensagem: 'descrição recusada' }],
        },
      },
      { status: 422, statusText: 'x' },
    );
    await estabilizar();

    expect(dialog.openDialogs).toHaveLength(1);
    expect(erros()).toEqual(['descrição recusada']);
    expect(campo('valor').value).toBe('1.234,50');
    expect(campo('descricao').value).toBe('  Almoço  ');
    expect(avisos.mostrar).not.toHaveBeenCalled();
  });

  it('falha_409_marca_categoria_e_recarrega__CA_F06_12', async () => {
    await abrir('GASTO');
    await preencherGasto();
    await salvar();

    controle.expectOne('/api/lancamentos').flush(
      {
        erro: {
          codigo: 'CATEGORIA_INATIVA',
          mensagem: 'A categoria "Mercado" está desativada. Escolha uma categoria ativa.',
          detalhes: [],
        },
      },
      { status: 409, statusText: 'x' },
    );
    await estabilizar();

    expect(erros()).toEqual([
      'A categoria "Mercado" está desativada. Escolha uma categoria ativa.',
    ]);
    expect(avisos.mostrar).not.toHaveBeenCalled(); // só no campo (Q3)
    controle.expectOne(URL_CATEGORIAS).flush(CATEGORIAS.filter((c) => c.id !== 'mercado'));
    await estabilizar();
    expect(dialog.openDialogs).toHaveLength(1);
  });

  it('falha_503_ou_sem_backend_mantem_os_dados__RNF_06', async () => {
    await abrir('GASTO');
    await preencherGasto();

    await salvar();
    controle
      .expectOne('/api/lancamentos')
      .flush(
        { erro: { codigo: 'PLANILHA_INDISPONIVEL', mensagem: 'Indisponível.', detalhes: [] } },
        { status: 503, statusText: 'x' },
      );
    await estabilizar();
    expect(TestBed.inject(ConexaoStore).mensagem()).toBe('Indisponível.');
    expect(dialog.openDialogs).toHaveLength(1);

    await salvar(); // tenta de novo
    controle.expectOne('/api/lancamentos').error(new ProgressEvent('error'));
    await estabilizar();

    expect(TestBed.inject(ConexaoStore).mensagem()).toBe(MENSAGEM_BACKEND_INDISPONIVEL);
    expect(dialog.openDialogs).toHaveLength(1);
    expect(campo('descricao').value).toBe('  Almoço  ');
    expect(botao('Salvar').disabled).toBe(false);
  });

  it('sem_categoria_ativa__CA_F06_13', async () => {
    await abrir('RECEITA', [
      umaCategoria({ id: 'x', nome: 'Antiga', tipo: 'RECEITA', ativa: false }),
    ]);

    const aviso = container().querySelector('.sem-categorias');
    expect(aviso?.textContent).toContain('Nenhuma categoria de receita ativa.');
    expect(aviso?.querySelector('a')?.getAttribute('href')).toBe('/categorias');
    expect(container().querySelector('[formcontrolname="categoria_id"]')).toBeNull();
    expect(container().querySelector<HTMLButtonElement>('button[type="submit"]')!.disabled).toBe(
      true,
    );
  });
});
