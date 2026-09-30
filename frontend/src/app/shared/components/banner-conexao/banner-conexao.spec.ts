import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Avisos } from '../../../core/avisos/avisos';
import { ConexaoStore } from '../../../core/state/conexao.store';
import { BannerConexao } from './banner-conexao';

const FALHA = {
  status: 503,
  codigo: 'PLANILHA_INDISPONIVEL',
  mensagem: 'Google Sheets indisponível no momento. Tente novamente.',
  detalhes: [],
};

describe('BannerConexao', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Avisos, useValue: { mostrar: vi.fn() } },
      ],
    });
  });

  it('aparece_so_na_falha_com_a_mensagem_do_backend__F04_3_5_6', async () => {
    const fixture = TestBed.createComponent(BannerConexao);
    const conexao = TestBed.inject(ConexaoStore);
    const elemento = fixture.nativeElement as HTMLElement;
    await fixture.whenStable();
    expect(elemento.querySelector('[role="alert"]')).toBeNull(); // 'verificando': nada na tela

    conexao.registrarFalha(FALHA);
    await fixture.whenStable();

    const banner = elemento.querySelector('[role="alert"]');
    expect(banner?.textContent).toContain(FALHA.mensagem);
    // Persistente: o único botão é "Tentar novamente", sem "fechar".
    const botoes = Array.from(elemento.querySelectorAll('button'));
    expect(botoes.map((botao) => botao.textContent?.trim())).toEqual(['Tentar novamente']);

    conexao.registrarOk();
    await fixture.whenStable();
    expect(elemento.querySelector('[role="alert"]')).toBeNull();
  });

  it('botao_tentar_novamente_desabilita_durante_a_chamada__CA_F04_26', async () => {
    const fixture = TestBed.createComponent(BannerConexao);
    const conexao = TestBed.inject(ConexaoStore);
    const controle = TestBed.inject(HttpTestingController);
    const elemento = fixture.nativeElement as HTMLElement;
    conexao.registrarFalha(FALHA);
    await fixture.whenStable();
    const botao = () => elemento.querySelector<HTMLButtonElement>('button')!;

    botao().click();
    await fixture.whenStable();

    expect(botao().disabled).toBe(true);
    expect(botao().textContent?.trim()).toBe('Tentando…');
    botao().click(); // desabilitado: não gera outra requisição
    const pendentes = controle.match('/api/health');
    expect(pendentes).toHaveLength(1);

    pendentes[0].flush({
      status: 'degradado',
      planilha: {
        ok: false,
        titulo: null,
        erro: { codigo: 'SEM_PERMISSAO_PLANILHA', mensagem: 'Compartilhe a planilha.' },
      },
    });
    await new Promise((resolver) => setTimeout(resolver));
    await fixture.whenStable();

    expect(botao().disabled).toBe(false);
    expect(botao().textContent?.trim()).toBe('Tentar novamente');
    expect(elemento.querySelector('[role="alert"]')?.textContent).toContain(
      'Compartilhe a planilha.',
    );
    controle.verify();
  });
});
