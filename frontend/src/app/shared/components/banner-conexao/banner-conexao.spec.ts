import { TestBed } from '@angular/core/testing';
import { ConexaoStore } from '../../../core/state/conexao.store';
import { BannerConexao } from './banner-conexao';

describe('BannerConexao', () => {
  it('aparece_so_na_falha_com_a_mensagem_do_backend__F04_3_5_6', async () => {
    const fixture = TestBed.createComponent(BannerConexao);
    const conexao = TestBed.inject(ConexaoStore);
    const elemento = fixture.nativeElement as HTMLElement;
    await fixture.whenStable();
    expect(elemento.querySelector('[role="alert"]')).toBeNull(); // 'verificando': nada na tela

    conexao.registrarFalha({
      status: 503,
      codigo: 'PLANILHA_INDISPONIVEL',
      mensagem: 'Google Sheets indisponível no momento. Tente novamente.',
      detalhes: [],
    });
    await fixture.whenStable();

    const banner = elemento.querySelector('[role="alert"]');
    expect(banner?.textContent).toContain(
      'Google Sheets indisponível no momento. Tente novamente.',
    );
    expect(elemento.querySelector('button')).toBeNull(); // sem "fechar": persistente

    conexao.registrarOk();
    await fixture.whenStable();
    expect(elemento.querySelector('[role="alert"]')).toBeNull();
  });
});
