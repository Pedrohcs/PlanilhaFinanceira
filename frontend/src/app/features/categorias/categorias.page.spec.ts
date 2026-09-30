import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ApplicationRef } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { umaCategoria } from '../../../testing/categorias';
import { provideMaterialParaTestes } from '../../../testing/material';
import { Avisos } from '../../core/avisos/avisos';
import { erroInterceptor } from '../../core/interceptors/erro.interceptor';
import { Categoria } from '../../core/models/categoria';
import { DadosStore } from '../../core/state/dados.store';
import { CategoriasPage, MENSAGEM_EM_USO, MENSAGEM_RESEED } from './categorias.page';

const URL_LISTA = '/api/categorias?incluir_inativas=true';

const LISTA: Categoria[] = [
  umaCategoria({ id: 'mercado', nome: 'Mercado', em_uso: true }),
  umaCategoria({ id: 'pet', nome: 'Pet' }),
  umaCategoria({ id: 'velha', nome: 'Velha', ativa: false, em_uso: true }),
  umaCategoria({ id: 'salario', nome: 'Salário', tipo: 'RECEITA', cor: '#66BB6A' }),
];

describe('CategoriasPage', () => {
  let fixture: ComponentFixture<CategoriasPage>;
  let controle: HttpTestingController;
  let avisos: { mostrar: ReturnType<typeof vi.fn> };
  let elemento: HTMLElement;

  beforeEach(() => {
    avisos = { mostrar: vi.fn() };
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([erroInterceptor])),
        provideHttpClientTesting(),
        provideMaterialParaTestes(),
        { provide: Avisos, useValue: avisos },
      ],
    });
    controle = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    TestBed.inject(MatDialog).closeAll();
    controle.verify();
  });

  async function estabilizar(): Promise<void> {
    await new Promise((resolver) => setTimeout(resolver));
    await TestBed.inject(ApplicationRef).whenStable();
    await fixture.whenStable();
  }

  async function abrirPagina(lista: Categoria[] = LISTA): Promise<void> {
    fixture = TestBed.createComponent(CategoriasPage);
    elemento = fixture.nativeElement as HTMLElement;
    await fixture.whenStable();
    controle.expectOne(URL_LISTA).flush(lista);
    await estabilizar();
  }

  /** Após uma escrita, a página incrementa `versao` e o store recarrega. */
  async function responderRecarga(lista: Categoria[]): Promise<void> {
    controle.expectOne(URL_LISTA).flush(lista);
    await estabilizar();
  }

  function secao(tipo: 'GASTO' | 'RECEITA'): HTMLElement {
    return elemento.querySelector<HTMLElement>(`section[aria-labelledby="titulo-${tipo}"]`)!;
  }

  function itens(tipo: 'GASTO' | 'RECEITA'): string[] {
    return Array.from(secao(tipo).querySelectorAll('li')).map(
      (li) =>
        (li.querySelector('.nome')?.textContent ?? '') +
        (li.querySelector('.selo') ? ' [Inativa]' : ''),
    );
  }

  async function acao(nome: string, rotulo: string): Promise<void> {
    elemento.querySelector<HTMLButtonElement>(`button[aria-label="Ações de ${nome}"]`)!.click();
    await estabilizar();
    const botao = Array.from(
      document.querySelectorAll<HTMLButtonElement>('.mat-mdc-menu-panel button'),
    ).find((b) => b.textContent?.trim().endsWith(rotulo));
    if (!botao) {
      throw new Error(`ação "${rotulo}" não encontrada`);
    }
    botao.click();
    await estabilizar();
  }

  function botaoDoDialogo(texto: string): HTMLButtonElement {
    const botao = Array.from(
      document.querySelectorAll<HTMLButtonElement>('mat-dialog-container button'),
    ).find((b) => b.textContent?.trim() === texto);
    if (!botao) {
      throw new Error(`botão "${texto}" não encontrado`);
    }
    return botao;
  }

  it('lista_por_tipo_com_selo_inativa__CA_F05_14', async () => {
    await abrirPagina();

    expect(elemento.querySelector('h1')?.textContent).toBe('Categorias');
    expect(itens('GASTO')).toEqual(['Mercado', 'Pet', 'Velha [Inativa]']);
    expect(itens('RECEITA')).toEqual(['Salário']);
    const cor = secao('RECEITA').querySelector<HTMLElement>('.cor')!;
    expect(cor.style.backgroundColor).toBe('rgb(102, 187, 106)');
  });

  it('estados_vazio_e_erro__borda_21', async () => {
    await abrirPagina([umaCategoria({ id: 'mercado', nome: 'Mercado' })]);
    expect(secao('RECEITA').textContent).toContain('Nenhuma categoria de receita.');

    const outro = TestBed.createComponent(CategoriasPage); // mesmo store: já carregado
    await outro.whenStable();
    controle.expectNone(URL_LISTA);
    outro.destroy();
  });

  it('erro_na_carga_mostra_estado_de_erro', async () => {
    fixture = TestBed.createComponent(CategoriasPage);
    elemento = fixture.nativeElement as HTMLElement;
    await fixture.whenStable();
    controle
      .expectOne(URL_LISTA)
      .flush(
        { erro: { codigo: 'PLANILHA_INDISPONIVEL', mensagem: 'Indisponível.', detalhes: [] } },
        { status: 503, statusText: 'x' },
      );
    await estabilizar();

    expect(elemento.textContent).toContain('Não foi possível carregar as categorias.');
    expect(elemento.querySelector('section')).toBeNull();
  });

  it('cria_na_secao_certa__CA_F05_15', async () => {
    await abrirPagina();

    const nova = Array.from(secao('RECEITA').querySelectorAll('button')).find((b) =>
      b.textContent?.includes('Nova categoria'),
    )!;
    nova.click();
    await estabilizar();
    const campo = document.querySelector<HTMLInputElement>('mat-dialog-container input')!;
    campo.value = 'Freelance';
    campo.dispatchEvent(new Event('input'));
    botaoDoDialogo('Salvar').click();
    await estabilizar();

    const post = controle.expectOne('/api/categorias');
    expect(post.request.body.tipo).toBe('RECEITA');
    expect(post.request.body.cor).toBe('#E57373'); // 1ª cor da paleta livre em RECEITA
    post.flush(umaCategoria({ id: 'freelance', nome: 'Freelance', tipo: 'RECEITA' }));
    await estabilizar();
    await responderRecarga([
      ...LISTA,
      umaCategoria({ id: 'freelance', nome: 'Freelance', tipo: 'RECEITA' }),
    ]);

    expect(dialogoAberto()).toBe(false);
    expect(avisos.mostrar).toHaveBeenCalledWith('Categoria criada.');
    expect(itens('RECEITA')).toEqual(['Salário', 'Freelance']);
    expect(TestBed.inject(DadosStore).versao()).toBe(1); // CA-F05.19
  });

  it('desativar_e_reativar__CA_F05_17', async () => {
    await abrirPagina();

    await acao('Pet', 'Desativar');
    const put = controle.expectOne('/api/categorias/pet');
    expect(put.request.body).toEqual({ nome: 'Pet', cor: '#E57373', ativa: false });
    put.flush({ ...LISTA[1], ativa: false });
    await estabilizar();
    const desativada = LISTA.map((c) => (c.id === 'pet' ? { ...c, ativa: false } : c));
    await responderRecarga(desativada);

    expect(avisos.mostrar).toHaveBeenCalledWith('Categoria desativada.');
    expect(itens('GASTO')).toContain('Pet [Inativa]');

    await acao('Pet', 'Reativar');
    const reativar = controle.expectOne('/api/categorias/pet');
    expect(reativar.request.body.ativa).toBe(true);
    reativar.flush(LISTA[1]);
    await estabilizar();
    await responderRecarga(LISTA);
    expect(avisos.mostrar).toHaveBeenCalledWith('Categoria reativada.');
  });

  it('excluir_em_uso_oferece_desativar__CA_11_3', async () => {
    await abrirPagina();

    await acao('Mercado', 'Excluir');
    expect(document.querySelector('mat-dialog-container')?.textContent).toContain(MENSAGEM_EM_USO);
    botaoDoDialogo('Desativar').click();
    await estabilizar();

    controle.expectNone((req) => req.method === 'DELETE'); // nenhum DELETE sai
    const put = controle.expectOne('/api/categorias/mercado');
    expect(put.request.body.ativa).toBe(false);
    put.flush({ ...LISTA[0], ativa: false });
    await estabilizar();
    await responderRecarga(LISTA);
    expect(avisos.mostrar).toHaveBeenCalledWith('Categoria desativada.');
  });

  it('excluir_sem_uso__CA_F05_18', async () => {
    await abrirPagina();

    await acao('Pet', 'Excluir');
    expect(document.querySelector('mat-dialog-container')?.textContent).toContain(
      'A categoria "Pet" será excluída.',
    );
    expect(document.querySelector('mat-dialog-container')?.textContent).not.toContain(
      MENSAGEM_RESEED,
    );
    botaoDoDialogo('Excluir').click();
    await estabilizar();

    const del = controle.expectOne('/api/categorias/pet');
    expect(del.request.method).toBe('DELETE');
    del.flush(null, { status: 204, statusText: 'No Content' });
    await estabilizar();
    await responderRecarga(LISTA.filter((c) => c.id !== 'pet'));

    expect(avisos.mostrar).toHaveBeenCalledWith('Categoria excluída.');
    expect(itens('GASTO')).toEqual(['Mercado', 'Velha [Inativa]']);
  });

  it('cancelar_a_exclusao_nao_envia_nada', async () => {
    await abrirPagina();

    await acao('Pet', 'Excluir');
    botaoDoDialogo('Cancelar').click();
    await estabilizar();

    controle.expectNone('/api/categorias/pet');
  });

  it('aviso_de_reseed_na_ultima__F05_3_6_6', async () => {
    await abrirPagina([umaCategoria({ id: 'pet', nome: 'Pet' })]);

    await acao('Pet', 'Excluir');

    expect(document.querySelector('mat-dialog-container')?.textContent).toContain(MENSAGEM_RESEED);
  });

  it('em_uso_inativa_nao_exclui', async () => {
    await abrirPagina();

    elemento.querySelector<HTMLButtonElement>('button[aria-label="Ações de Velha"]')!.click();
    await estabilizar();
    const excluir = Array.from(
      document.querySelectorAll<HTMLButtonElement>('.mat-mdc-menu-panel button'),
    ).find((b) => b.textContent?.includes('Excluir'))!;

    expect(excluir.textContent).toContain('Excluir (em uso)');
    expect(excluir.disabled).toBe(true);
  });

  function dialogoAberto(): boolean {
    return TestBed.inject(MatDialog).openDialogs.length > 0;
  }
});
