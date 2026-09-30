import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';
import { Avisos } from '../avisos/avisos';
import {
  BACKEND_INDISPONIVEL,
  ErroApi,
  MENSAGEM_BACKEND_INDISPONIVEL,
  MENSAGEM_ERRO_INTERNO,
} from '../models/erro-api';
import { ConexaoStore } from '../state/conexao.store';
import { erroInterceptor } from './erro.interceptor';

describe('erroInterceptor (SPECS/03 §8.4)', () => {
  let http: HttpClient;
  let controle: HttpTestingController;
  let conexao: ConexaoStore;
  let avisos: { mostrar: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    avisos = { mostrar: vi.fn() };
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([erroInterceptor])),
        provideHttpClientTesting(),
        { provide: Avisos, useValue: avisos },
      ],
    });
    http = TestBed.inject(HttpClient);
    controle = TestBed.inject(HttpTestingController);
    conexao = TestBed.inject(ConexaoStore);
  });

  afterEach(() => controle.verify());

  /** Faz a chamada, responde com `responder` e devolve o erro que chegou a quem chamou. */
  async function erroDe(responder: (url: string) => void): Promise<unknown> {
    const resposta = firstValueFrom(http.get('/api/qualquer'));
    responder('/api/qualquer');
    return resposta.then(
      () => {
        throw new Error('a chamada deveria falhar');
      },
      (erro: unknown) => erro,
    );
  }

  function envelope(codigo: string, mensagem: string, detalhes: unknown[] = []) {
    return { erro: { codigo, mensagem, detalhes } };
  }

  it('converte_envelope_em_ErroApi__CA_F04_13', async () => {
    const detalhes = [{ campo: 'valor', mensagem: 'deve ser maior que zero' }];

    const erro = await erroDe((url) =>
      controle.expectOne(url).flush(envelope('CATEGORIA_DUPLICADA', 'Já existe.', detalhes), {
        status: 409,
        statusText: 'Conflict',
      }),
    );

    expect(erro).toEqual({
      status: 409,
      codigo: 'CATEGORIA_DUPLICADA',
      mensagem: 'Já existe.',
      detalhes,
    } satisfies ErroApi);
  });

  it('503_vai_para_o_banner_sem_snackbar__CA_F04_14', async () => {
    const mensagem = 'Compartilhe a planilha com robo@x.iam.gserviceaccount.com como Editor.';

    const erro = await erroDe((url) =>
      controle.expectOne(url).flush(envelope('SEM_PERMISSAO_PLANILHA', mensagem), {
        status: 503,
        statusText: 'Service Unavailable',
      }),
    );

    expect((erro as ErroApi).codigo).toBe('SEM_PERMISSAO_PLANILHA');
    expect(conexao.estado()).toBe('falha');
    expect(conexao.mensagem()).toBe(mensagem);
    expect(avisos.mostrar).not.toHaveBeenCalled();
  });

  it('422_vai_para_o_formulario_sem_snackbar__CA_F04_15', async () => {
    const detalhes = [{ campo: 'descricao', mensagem: 'obrigatória' }];

    const erro = await erroDe((url) =>
      controle.expectOne(url).flush(envelope('VALIDACAO', 'Dados inválidos.', detalhes), {
        status: 422,
        statusText: 'Unprocessable Content',
      }),
    );

    expect((erro as ErroApi).detalhes).toEqual(detalhes);
    expect(avisos.mostrar).not.toHaveBeenCalled();
    expect(conexao.estado()).toBe('verificando');
  });

  for (const [status, codigo] of [
    [404, 'NAO_ENCONTRADO'],
    [409, 'CATEGORIA_EM_USO'],
    [500, 'ERRO_INTERNO'],
  ] as const) {
    it(`${status}_abre_snackbar__CA_F04_16`, async () => {
      await erroDe((url) =>
        controle.expectOne(url).flush(envelope(codigo, `mensagem ${status}`), {
          status,
          statusText: 'x',
        }),
      );

      expect(avisos.mostrar).toHaveBeenCalledWith(`mensagem ${status}`);
      expect(conexao.estado()).toBe('verificando');
    });
  }

  it('backend_fora_do_ar_status_0__CA_F04_17', async () => {
    const erro = await erroDe((url) => controle.expectOne(url).error(new ProgressEvent('error')));

    expect(erro).toEqual({
      status: 0,
      codigo: BACKEND_INDISPONIVEL,
      mensagem: MENSAGEM_BACKEND_INDISPONIVEL,
      detalhes: [],
    } satisfies ErroApi);
    expect(conexao.estado()).toBe('falha');
    expect(conexao.mensagem()).toBe(MENSAGEM_BACKEND_INDISPONIVEL);
    expect(avisos.mostrar).not.toHaveBeenCalled();
  });

  for (const status of [502, 504]) {
    it(`backend_fora_do_ar_proxy_${status}__CA_F04_17`, async () => {
      // O proxy do `ng serve` devolve texto, sem o envelope da API (borda 13).
      const erro = await erroDe((url) =>
        controle
          .expectOne(url)
          .flush('Error occurred while trying to proxy', { status, statusText: 'x' }),
      );

      expect((erro as ErroApi).codigo).toBe(BACKEND_INDISPONIVEL);
      expect(conexao.estado()).toBe('falha');
      expect(avisos.mostrar).not.toHaveBeenCalled();
    });
  }

  it('corpo_fora_do_envelope_vira_erro_interno__borda_20', async () => {
    const erro = await erroDe((url) =>
      controle
        .expectOne(url)
        .flush('<html>Internal Server Error</html>', { status: 500, statusText: 'x' }),
    );

    expect((erro as ErroApi).mensagem).toBe(MENSAGEM_ERRO_INTERNO);
    expect(avisos.mostrar).toHaveBeenCalledWith(MENSAGEM_ERRO_INTERNO);
    expect(conexao.estado()).toBe('verificando');
  });

  it('sucesso_passa_intacto', async () => {
    const resposta = firstValueFrom(http.get('/api/qualquer'));
    controle.expectOne('/api/qualquer').flush({ ok: true });

    expect(await resposta).toEqual({ ok: true });
  });
});
