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
import { erroInterceptor, TRATAMENTO_LOCAL } from '../../core/interceptors/erro.interceptor';
import { Categoria } from '../../core/models/categoria';
import { MENSAGEM_BACKEND_INDISPONIVEL } from '../../core/models/erro-api';
import { Lancamento } from '../../core/models/lancamento';
import { ConexaoStore } from '../../core/state/conexao.store';
import { DadosStore } from '../../core/state/dados.store';
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
const ORIGINAL: Lancamento = {
  id: 'p3',
  data: '2026-09-30',
  tipo: 'GASTO',
  descricao: 'Geladeira',
  valor: 333.34,
  categoria_id: 'mercado',
  categoria_nome: 'Mercado',
  categoria_cor: '#E57373',
  forma_pagamento: 'CREDITO',
  observacao: 'loja do centro',
  parcelamento_id: 'par',
  parcela_numero: 3,
  parcela_total: 10,
  recorrencia_id: null,
  criado_em: '2026-09-01T10:00:00',
  atualizado_em: '2026-09-01T10:00:00',
};
/** Corpo do `PUT` sem mudanças: o que o formulário pré-preenchido envia. */
const CORPO_ORIGINAL = {
  data: '2026-09-30',
  tipo: 'GASTO',
  descricao: 'Geladeira',
  valor: 333.34,
  categoria_id: 'mercado',
  forma_pagamento: 'CREDITO',
  observacao: 'loja do centro',
};

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

  async function abrir(
    tipo: 'GASTO' | 'RECEITA',
    categorias = CATEGORIAS,
    lancamento?: Lancamento,
  ): Promise<void> {
    const referencia: MatDialogRef<LancamentoFormDialog, Lancamento> = dialog.open(
      LancamentoFormDialog,
      { data: { tipo, lancamento } satisfies DadosFormularioLancamento },
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

  async function abrirEdicao(lancamento = ORIGINAL, categorias = CATEGORIAS): Promise<void> {
    await abrir(lancamento.tipo, categorias, lancamento);
  }

  function selecionado(nome: string): string {
    return campo(nome).querySelector('.mat-mdc-select-value')?.textContent?.trim() ?? '';
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

  function caixaParcelada(): HTMLInputElement | null {
    return container().querySelector<HTMLInputElement>('mat-checkbox.parcelada input');
  }

  async function alternarParcelada(): Promise<void> {
    caixaParcelada()!.click();
    await estabilizar();
  }

  function rotulos(): string[] {
    return Array.from(container().querySelectorAll('mat-label')).map(
      (rotulo) => rotulo.textContent?.trim() ?? '',
    );
  }

  function previa(): string {
    return (container().querySelector('.previa')?.textContent ?? '').replace(/\u00a0/g, ' ').trim();
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

  it('edicao_pre_preenchida__CA_05_1', async () => {
    await abrirEdicao();

    expect(container().querySelector('h2')?.textContent).toBe('Editar gasto');
    expect(campo('data').value).toBe('30/09/2026');
    expect(campo('valor').value).toBe('333,34');
    expect(campo('descricao').value).toBe('Geladeira');
    expect(campo('observacao').value).toBe('loja do centro');
    expect(selecionado('tipo')).toBe('Gasto');
    expect(selecionado('categoria_id')).toBe('Mercado');
    expect(await opcoes('categoria_id')).toEqual(['Mercado']); // inativa de outro lançamento, não
    expect(selecionado('forma_pagamento')).toBe('Cartão de crédito');
    expect(container().querySelector('.vinculo')?.textContent?.trim()).toBe('Parcela 3/10');
  });

  it('registro_nao_mostra_tipo_nem_vinculo', async () => {
    await abrir('GASTO');

    expect(container().querySelector('[formcontrolname="tipo"]')).toBeNull();
    expect(container().querySelector('.vinculo')).toBeNull();
  });

  it('recorrente_mostra_vinculo__F08', async () => {
    await abrirEdicao({
      ...ORIGINAL,
      parcelamento_id: null,
      parcela_numero: null,
      parcela_total: null,
      recorrencia_id: 'rec',
    });

    expect(container().querySelector('.vinculo')?.textContent?.trim()).toBe(
      'Gerado por recorrência',
    );
  });

  it('salva_edicao_com_put__CA_F08_12', async () => {
    await abrirEdicao();
    await digitar('descricao', 'Geladeira nova');

    await salvar();

    const put = controle.expectOne('/api/lancamentos/p3');
    expect(put.request.method).toBe('PUT');
    expect(put.request.body).toEqual({ ...CORPO_ORIGINAL, descricao: 'Geladeira nova' });
    put.flush({ ...ORIGINAL, descricao: 'Geladeira nova' });
    await estabilizar();

    expect((await resultado)?.descricao).toBe('Geladeira nova');
    expect(dialog.openDialogs).toHaveLength(0);
    controle.expectNone('/api/lancamentos');
  });

  it('troca_de_tipo__CA_F08_11', async () => {
    await abrirEdicao();

    await escolher('tipo', 'Receita');

    expect(container().querySelector('h2')?.textContent).toBe('Editar receita');
    expect(selecionado('categoria_id')).toBe(''); // categoria de gasto limpa (RN-04)
    expect(await opcoes('categoria_id')).toEqual(['Salário']);
    await salvar();
    expect(erros()).toEqual(['Escolha uma categoria.']);
    controle.expectNone('/api/lancamentos/p3');

    await escolher('categoria_id', 'Salário');
    await escolher('forma_pagamento', 'Não informar');
    await salvar();

    const put = controle.expectOne('/api/lancamentos/p3');
    expect(put.request.body).toEqual({
      ...CORPO_ORIGINAL,
      tipo: 'RECEITA',
      categoria_id: 'salario',
      forma_pagamento: null,
    });
    put.flush({ ...ORIGINAL, ...put.request.body });
    await estabilizar();
  });

  it('volta_para_gasto_exige_forma__RN_05', async () => {
    await abrirEdicao({
      ...ORIGINAL,
      tipo: 'RECEITA',
      categoria_id: 'salario',
      forma_pagamento: null,
    });

    await escolher('tipo', 'Gasto');
    await escolher('categoria_id', 'Mercado');
    await salvar();

    expect(erros()).toEqual(['Escolha a forma de pagamento.']);
    controle.expectNone('/api/lancamentos/p3');
  });

  it('categoria_inativa_na_edicao__CA_F08_15', async () => {
    await abrirEdicao({ ...ORIGINAL, categoria_id: 'velha' });

    expect(selecionado('categoria_id')).toBe('Velha (inativa)');
    expect(await opcoes('categoria_id')).toEqual(['Mercado', 'Velha (inativa)']);
    await salvar();

    const put = controle.expectOne('/api/lancamentos/p3');
    expect(put.request.body.categoria_id).toBe('velha'); // mantida (Q1)
    put.flush({ ...ORIGINAL, categoria_id: 'velha' });
    await estabilizar();
  });

  it('erro_mantem_dados_na_edicao__CA_01_4', async () => {
    await abrirEdicao();
    await digitar('valor', '350');
    await salvar();

    controle.expectOne('/api/lancamentos/p3').flush(
      {
        erro: {
          codigo: 'VALIDACAO',
          mensagem: 'Dados inválidos.',
          detalhes: [{ campo: 'valor', mensagem: 'valor recusado' }],
        },
      },
      { status: 422, statusText: 'x' },
    );
    await estabilizar();

    expect(dialog.openDialogs).toHaveLength(1);
    expect(erros()).toEqual(['valor recusado']);
    expect(campo('valor').value).toBe('350,00');
  });

  it('404_fecha_o_dialogo__CA_F08_14', async () => {
    await abrirEdicao();
    await salvar();

    controle.expectOne('/api/lancamentos/p3').flush(
      {
        erro: { codigo: 'NAO_ENCONTRADO', mensagem: 'Lançamento não encontrado.', detalhes: [] },
      },
      { status: 404, statusText: 'x' },
    );
    await estabilizar();

    expect(avisos.mostrar).toHaveBeenCalledWith('Lançamento não encontrado.');
    expect(dialog.openDialogs).toHaveLength(0);
    expect(await resultado).toBeUndefined();
    expect(TestBed.inject(DadosStore).versao()).toBe(1); // a lista recarrega
    controle.expectOne(URL_CATEGORIAS).flush(CATEGORIAS); // e as categorias também
  });

  it('parcelada_so_em_gasto_novo__CA_F12_10', async () => {
    await abrir('RECEITA');

    expect(caixaParcelada()).toBeNull();
  });

  it('parcelada_nao_aparece_na_edicao__CA_F12_10', async () => {
    await abrirEdicao();

    expect(caixaParcelada()).toBeNull();
  });

  it('campos_e_validacao_da_parcelada__CA_F12_11', async () => {
    await abrir('GASTO');
    expect(caixaParcelada()?.closest('mat-checkbox')?.textContent?.trim()).toBe('Compra parcelada');
    expect(rotulos().slice(0, 2)).toEqual(['Valor', 'Data']);
    expect(container().querySelector('[formcontrolname="parcelas"]')).toBeNull();

    await alternarParcelada();

    expect(rotulos().slice(0, 3)).toEqual(['Valor total', 'Data da compra', 'Nº de parcelas']);
    expect(campo('parcelas').value).toBe(''); // vazio de início
    for (const invalido of ['1', '49']) {
      await digitar('parcelas', invalido);
      expect(erros()).toContain('Informe de 2 a 48 parcelas.');
    }
    await digitar('parcelas', '3');
    expect(erros()).not.toContain('Informe de 2 a 48 parcelas.');

    await alternarParcelada(); // desmarcada: o campo some (borda 18)
    expect(container().querySelector('[formcontrolname="parcelas"]')).toBeNull();
    expect(rotulos().slice(0, 2)).toEqual(['Valor', 'Data']);
  });

  it('previa_das_parcelas__CA_F12_12', async () => {
    await abrir('GASTO');
    await alternarParcelada();

    await digitar('valor', '1000');
    expect(previa()).toBe(''); // sem nº de parcelas ainda
    await digitar('parcelas', '3');
    expect(previa()).toBe('3× — 1ª de R$ 333,34 e 2× de R$ 333,33');
    await digitar('parcelas', '10');
    expect(previa()).toBe('10× de R$ 100,00');

    await digitar('valor', '0,05');
    expect(previa()).toBe('');
    expect(erros()).toContain('10 parcelas exigem um valor total de no mínimo R$ 0,10.');
    await digitar('parcelas', '5'); // mudar as parcelas revalida o total
    expect(erros()).not.toContain('10 parcelas exigem um valor total de no mínimo R$ 0,10.');
    expect(previa()).toBe('5× de R$ 0,01');
  });

  it('salva_parcelada__CA_F12_13', async () => {
    await abrir('GASTO');
    await preencherGasto();
    await alternarParcelada();
    await digitar('parcelas', '3');

    await salvar();
    container().querySelector<HTMLButtonElement>('button[type="submit"]')!.click(); // duplo clique
    await estabilizar();

    const post = controle.expectOne('/api/parcelamentos'); // um só (borda 17)
    expect(post.request.method).toBe('POST');
    expect(post.request.body).toEqual({
      data: dataParaIso(hoje()),
      descricao: 'Almoço',
      valor_total: 1234.5,
      parcelas: 3,
      categoria_id: 'mercado',
      forma_pagamento: 'PIX',
      observacao: null,
    });
    expect(post.request.context.get(TRATAMENTO_LOCAL)).toBe(true);
    controle.expectNone('/api/lancamentos');
    post.flush({ parcelamento_id: 'par', lancamentos: [] });
    await estabilizar();

    expect(await resultado).toEqual({ parcelamento_id: 'par', lancamentos: [] });
    expect(dialog.openDialogs).toHaveLength(0);
  });

  it('erro_marca_campo_da_parcelada__CA_F12_13', async () => {
    await abrir('GASTO');
    await preencherGasto();
    await alternarParcelada();
    await digitar('parcelas', '3');
    await salvar();

    controle.expectOne('/api/parcelamentos').flush(
      {
        erro: {
          codigo: 'VALIDACAO',
          mensagem: 'Dados inválidos.',
          detalhes: [
            { campo: 'valor_total', mensagem: 'total recusado' },
            { campo: 'parcelas', mensagem: 'parcelas recusadas' },
          ],
        },
      },
      { status: 422, statusText: 'x' },
    );
    await estabilizar();

    expect(dialog.openDialogs).toHaveLength(1);
    expect(erros()).toEqual(['total recusado', 'parcelas recusadas']);
    expect(campo('parcelas').value).toBe('3');
    expect(avisos.mostrar).not.toHaveBeenCalled();
  });

  it('desmarcada_envia_lancamento_comum__borda_18', async () => {
    await abrir('GASTO');
    await preencherGasto();
    await alternarParcelada();
    await digitar('parcelas', '3');
    await alternarParcelada();

    await salvar();

    controle.expectNone('/api/parcelamentos');
    const post = controle.expectOne('/api/lancamentos');
    expect(post.request.body.valor).toBe(1234.5);
    expect(post.request.body.parcelas).toBeUndefined();
    post.flush({ ...post.request.body, id: 'novo' });
    await estabilizar();
  });
});
