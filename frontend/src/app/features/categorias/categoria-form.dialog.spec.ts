import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ApplicationRef } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { firstValueFrom } from 'rxjs';
import { umaCategoria } from '../../../testing/categorias';
import { provideMaterialParaTestes } from '../../../testing/material';
import { Avisos } from '../../core/avisos/avisos';
import { erroInterceptor } from '../../core/interceptors/erro.interceptor';
import { Categoria } from '../../core/models/categoria';
import { CategoriaFormDialog, DadosFormularioCategoria } from './categoria-form.dialog';
import { PALETA } from './paleta';

describe('CategoriaFormDialog', () => {
  let controle: HttpTestingController;
  let dialog: MatDialog;
  let referencia: MatDialogRef<CategoriaFormDialog, Categoria>;
  let resultado: Promise<Categoria | undefined>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([erroInterceptor])),
        provideHttpClientTesting(),
        provideMaterialParaTestes(),
        { provide: Avisos, useValue: { mostrar: vi.fn() } },
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

  async function abrir(dados: DadosFormularioCategoria): Promise<void> {
    referencia = dialog.open<CategoriaFormDialog, DadosFormularioCategoria, Categoria>(
      CategoriaFormDialog,
      { data: dados },
    );
    resultado = firstValueFrom(referencia.afterClosed());
    await estabilizar();
  }

  function campoNome(): HTMLInputElement {
    return document.querySelector<HTMLInputElement>('mat-dialog-container input')!;
  }

  function digitar(texto: string): void {
    campoNome().value = texto;
    campoNome().dispatchEvent(new Event('input'));
  }

  function amostras(): HTMLButtonElement[] {
    return Array.from(document.querySelectorAll<HTMLButtonElement>('.paleta button'));
  }

  function selecionada(): string | null | undefined {
    return amostras()
      .find((b) => b.getAttribute('aria-pressed') === 'true')
      ?.getAttribute('aria-label');
  }

  async function salvar(): Promise<void> {
    document
      .querySelector<HTMLButtonElement>('mat-dialog-container button[type="submit"]')!
      .click();
    await estabilizar();
  }

  function textoDoDialogo(): string {
    return document.querySelector('mat-dialog-container')?.textContent ?? '';
  }

  it('cria_com_nome_e_cor', async () => {
    await abrir({ tipo: 'RECEITA', corInicial: '#9CCC65' });
    expect(textoDoDialogo()).toContain('Nova categoria');
    expect(textoDoDialogo()).toContain('Tipo: Receita');

    digitar('  Bônus   anual ');
    await estabilizar();
    expect(textoDoDialogo()).toContain('11/40'); // contador sobre o nome normalizado
    amostras()[15].click();
    await salvar();

    const post = controle.expectOne('/api/categorias');
    expect(post.request.body).toEqual({ nome: 'Bônus anual', tipo: 'RECEITA', cor: PALETA[15] });
    expect(textoDoDialogo()).toContain('Salvando…');
    post.flush(umaCategoria({ id: 'bonus-anual', nome: 'Bônus anual', tipo: 'RECEITA' }));
    await estabilizar();

    expect((await resultado)?.id).toBe('bonus-anual');
  });

  it('duplicada_mantem_dialogo_e_marca_nome__CA_F05_16', async () => {
    await abrir({ tipo: 'GASTO', corInicial: '#E57373' });
    digitar('mercado');
    await salvar();

    controle.expectOne('/api/categorias').flush(
      {
        erro: {
          codigo: 'CATEGORIA_DUPLICADA',
          mensagem: 'Já existe uma categoria de gasto chamada "mercado".',
          detalhes: [],
        },
      },
      { status: 409, statusText: 'Conflict' },
    );
    await estabilizar();

    expect(dialog.openDialogs).toHaveLength(1); // continua aberto
    expect(campoNome().value).toBe('mercado'); // com os dados
    expect(document.querySelector('mat-error')?.textContent).toContain(
      'Já existe uma categoria de gasto chamada "mercado".',
    );
    expect(textoDoDialogo()).toContain('Salvar');
  });

  it('422_marca_o_campo', async () => {
    await abrir({ tipo: 'GASTO', corInicial: '#E57373' });
    digitar('Pet');
    await salvar();

    controle.expectOne('/api/categorias').flush(
      {
        erro: {
          codigo: 'VALIDACAO',
          mensagem: 'Dados inválidos.',
          detalhes: [{ campo: 'cor', mensagem: 'cor inválida' }],
        },
      },
      { status: 422, statusText: 'x' },
    );
    await estabilizar();

    expect(dialog.openDialogs).toHaveLength(1);
    expect(document.querySelector('.erro-cor')?.textContent).toContain('cor inválida');
  });

  it('limite_de_40_no_cliente', async () => {
    await abrir({ tipo: 'GASTO', corInicial: '#E57373' });

    digitar('x'.repeat(41));
    await salvar();
    expect(document.querySelector('mat-error')?.textContent).toContain('no máximo 40');

    digitar('   ');
    await salvar();
    expect(document.querySelector('mat-error')?.textContent).toContain('Informe o nome.');

    controle.expectNone('/api/categorias'); // nada enviado com o formulário inválido
  });

  it('paleta_e_pre_selecao__CA_F05_24', async () => {
    await abrir({ tipo: 'GASTO', corInicial: PALETA[11] });

    expect(amostras()).toHaveLength(24);
    expect(selecionada()).toBe(PALETA[11]);
  });

  it('cor_fora_da_paleta_na_edicao__CA_F05_24', async () => {
    const categoria = umaCategoria({ id: 'pet', nome: 'Pet', cor: '#123456', ativa: false });
    await abrir({ tipo: 'GASTO', categoria, corInicial: categoria.cor });
    expect(textoDoDialogo()).toContain('Editar categoria');
    expect(amostras()).toHaveLength(25); // borda 23: a cor atual como opção extra
    expect(selecionada()).toBe('#123456');

    digitar('Pet Shop');
    await salvar();

    const put = controle.expectOne('/api/categorias/pet');
    expect(put.request.body).toEqual({ nome: 'Pet Shop', cor: '#123456', ativa: false });
    put.flush({ ...categoria, nome: 'Pet Shop' });
    await estabilizar();
    expect((await resultado)?.nome).toBe('Pet Shop');
  });
});
