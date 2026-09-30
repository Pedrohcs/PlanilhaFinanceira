import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ApplicationInitStatus } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Avisos } from '../avisos/avisos';
import { erroInterceptor } from '../interceptors/erro.interceptor';
import { MENSAGEM_BACKEND_INDISPONIVEL } from '../models/erro-api';
import { RespostaHealth } from '../models/health';
import {
  ConexaoStore,
  DURACAO_AVISO_RECONEXAO_MS,
  MENSAGEM_CONEXAO_RESTABELECIDA,
  provideVerificacaoDeConexao,
} from './conexao.store';
import { DadosStore } from './dados.store';

const OK: RespostaHealth = {
  status: 'ok',
  planilha: { ok: true, titulo: 'Planilha Financeira', erro: null },
};

function degradado(codigo: string, mensagem: string): RespostaHealth {
  return { status: 'degradado', planilha: { ok: false, titulo: null, erro: { codigo, mensagem } } };
}

const SEM_PERMISSAO = degradado(
  'SEM_PERMISSAO_PLANILHA',
  'Compartilhe a planilha com robo@projeto.iam.gserviceaccount.com como Editor.',
);
const SEM_INTERNET = degradado(
  'PLANILHA_INDISPONIVEL',
  'Google Sheets indisponível no momento. Tente novamente.',
);

describe('ConexaoStore', () => {
  let controle: HttpTestingController;
  let avisos: { mostrar: ReturnType<typeof vi.fn> };

  function configurar(comInicializador: boolean): void {
    avisos = { mostrar: vi.fn() };
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([erroInterceptor])),
        provideHttpClientTesting(),
        { provide: Avisos, useValue: avisos },
        ...(comInicializador ? [provideVerificacaoDeConexao()] : []),
      ],
    });
    controle = TestBed.inject(HttpTestingController);
  }

  /** Responde o health pendente e espera o store processar a resposta. */
  async function responder(corpo: RespostaHealth): Promise<void> {
    controle.expectOne('/api/health').flush(corpo);
    await new Promise((resolver) => setTimeout(resolver));
  }

  afterEach(() => controle.verify());

  it('comeca_verificando_e_guarda_a_ultima_falha', () => {
    configurar(false);
    const store = TestBed.inject(ConexaoStore);
    expect(store.estado()).toBe('verificando');
    expect(store.mensagem()).toBeNull();

    store.registrarFalha({ status: 503, codigo: 'A', mensagem: 'primeira', detalhes: [] });
    store.registrarFalha({ status: 503, codigo: 'B', mensagem: 'segunda', detalhes: [] });

    expect(store.estado()).toBe('falha');
    expect(store.mensagem()).toBe('segunda'); // borda 14: um banner, a mais recente

    store.registrarOk();
    expect(store.estado()).toBe('ok');
    expect(store.mensagem()).toBeNull();
  });

  it('abertura_faz_um_health__CA_F04_23', async () => {
    configurar(true);
    const inicializacao = TestBed.inject(ApplicationInitStatus);
    await inicializacao.donePromise;

    // Q4: o inicializador terminou e a resposta ainda nem chegou.
    expect(inicializacao.done).toBe(true);
    const pendentes = controle.match('/api/health');
    expect(pendentes).toHaveLength(1);
    expect(TestBed.inject(ConexaoStore).estado()).toBe('verificando');

    pendentes[0].flush(OK);
    await new Promise((resolver) => setTimeout(resolver));
    expect(TestBed.inject(ConexaoStore).estado()).toBe('ok');
  });

  it('health_ok_sem_banner__CA_F04_24', async () => {
    configurar(false);
    const store = TestBed.inject(ConexaoStore);

    const verificacao = store.verificar();
    await responder(OK);

    expect(await verificacao).toBe(true);
    expect(store.estado()).toBe('ok');
    expect(store.mensagem()).toBeNull();
  });

  it('abertura_ok_nao_mostra_aviso_nem_recarrega__Q5', async () => {
    configurar(false);
    const store = TestBed.inject(ConexaoStore);

    const verificacao = store.verificar();
    await responder(OK);
    await verificacao;

    expect(avisos.mostrar).not.toHaveBeenCalled();
    expect(TestBed.inject(DadosStore).versao()).toBe(0);
  });

  it('health_degradado_mostra_banner__CA_16_1', async () => {
    configurar(false);
    const store = TestBed.inject(ConexaoStore);

    const verificacao = store.verificar();
    await responder(SEM_PERMISSAO);

    expect(await verificacao).toBe(false);
    expect(store.estado()).toBe('falha');
    expect(store.mensagem()).toBe(
      'Compartilhe a planilha com robo@projeto.iam.gserviceaccount.com como Editor.',
    );
  });

  it('backend_desligado_vira_falha__CA_F04_29', async () => {
    configurar(false);
    const store = TestBed.inject(ConexaoStore);

    const verificacao = store.verificar();
    controle.expectOne('/api/health').error(new ProgressEvent('error'));

    expect(await verificacao).toBe(false);
    expect(store.estado()).toBe('falha');
    expect(store.mensagem()).toBe(MENSAGEM_BACKEND_INDISPONIVEL);
  });

  it('tentar_novamente_uma_requisicao_por_vez__CA_F04_26', async () => {
    configurar(false);
    const store = TestBed.inject(ConexaoStore);

    const primeira = store.tentarNovamente();
    expect(store.tentando()).toBe(true);
    await store.tentarNovamente(); // duplo clique (borda 15): ignorado na hora

    const pendentes = controle.match('/api/health');
    expect(pendentes).toHaveLength(1);
    expect(store.tentando()).toBe(true);

    pendentes[0].flush(OK);
    await primeira;
    expect(store.tentando()).toBe(false);
  });

  it('tentar_novamente_com_sucesso__CA_16_2', async () => {
    configurar(false);
    const store = TestBed.inject(ConexaoStore);
    store.registrarFalha({ status: 200, codigo: 'X', mensagem: 'sem internet', detalhes: [] });

    const tentativa = store.tentarNovamente();
    await responder(OK);
    await tentativa;

    expect(store.estado()).toBe('ok');
    expect(store.tentando()).toBe(false);
    expect(avisos.mostrar).toHaveBeenCalledWith(
      MENSAGEM_CONEXAO_RESTABELECIDA,
      DURACAO_AVISO_RECONEXAO_MS,
    );
    expect(TestBed.inject(DadosStore).versao()).toBe(1);
  });

  it('tentar_novamente_com_nova_falha__CA_F04_28', async () => {
    configurar(false);
    const store = TestBed.inject(ConexaoStore);
    store.registrarFalha({
      status: 200,
      codigo: SEM_INTERNET.planilha.erro!.codigo,
      mensagem: SEM_INTERNET.planilha.erro!.mensagem,
      detalhes: [],
    });

    const tentativa = store.tentarNovamente();
    await responder(SEM_PERMISSAO);
    await tentativa;

    expect(store.estado()).toBe('falha');
    expect(store.mensagem()).toBe(SEM_PERMISSAO.planilha.erro!.mensagem);
    expect(store.tentando()).toBe(false);
    expect(avisos.mostrar).not.toHaveBeenCalled();
    expect(TestBed.inject(DadosStore).versao()).toBe(0);
  });
});
