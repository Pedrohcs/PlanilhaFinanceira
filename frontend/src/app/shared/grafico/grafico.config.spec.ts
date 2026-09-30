import { Chart } from 'chart.js';
import { CoresDoTema, formatarReais, opcoesPadrao, TipoGrafico } from './grafico.config';

const CORES: CoresDoTema = { texto: 'rgb(1, 2, 3)', grade: 'rgb(4, 5, 6)' };

/** O `Intl` de pt-BR separa `R$` do número com espaço não-quebrável. */
function semEspacoFixo(texto: string): string {
  return texto.replace(/ /g, ' ');
}

type Callback = (this: unknown, ...args: unknown[]) => unknown;

/** Só os campos de `TooltipItem` que o rótulo lê. */
function rotuloDoTooltip(tipo: TipoGrafico, item: Record<string, unknown>): string {
  const opcoes = opcoesPadrao(tipo, CORES, 'x');
  const label = opcoes.plugins?.tooltip?.callbacks?.label as unknown as Callback;
  return semEspacoFixo(label.call(undefined, item) as string);
}

describe('grafico.config', () => {
  it('registra_so_o_necessario__CA_F04_11', () => {
    for (const controller of ['doughnut', 'bar', 'line']) {
      expect(() => Chart.registry.getController(controller)).not.toThrow();
    }
    for (const elemento of ['arc', 'bar', 'line', 'point']) {
      expect(() => Chart.registry.getElement(elemento)).not.toThrow();
    }
    for (const escala of ['category', 'linear']) {
      expect(() => Chart.registry.getScale(escala)).not.toThrow();
    }
    for (const plugin of ['tooltip', 'legend']) {
      expect(() => Chart.registry.getPlugin(plugin)).not.toThrow();
    }
    for (const naoUsado of ['radar', 'pie', 'polarArea', 'scatter', 'bubble']) {
      expect(() => Chart.registry.getController(naoUsado)).toThrow();
    }
    expect(() => Chart.registry.getScale('time')).toThrow();
  });

  it('formata_reais_ptBR__CA_F04_12', () => {
    expect(semEspacoFixo(formatarReais(1234.56))).toBe('R$ 1.234,56');
    expect(semEspacoFixo(formatarReais(0))).toBe('R$ 0,00');
    expect(semEspacoFixo(formatarReais(1000000))).toBe('R$ 1.000.000,00');
  });

  it('tooltip_e_eixo_em_reais__CA_F04_12', () => {
    expect(
      rotuloDoTooltip('doughnut', { parsed: 1234.56, label: 'Alimentação', dataset: {} }),
    ).toBe('Alimentação: R$ 1.234,56');
    expect(
      rotuloDoTooltip('bar', {
        parsed: { x: 0, y: 99.9 },
        label: 'Pix',
        dataset: { label: 'Gastos' },
        chart: { options: { indexAxis: 'x' } },
      }),
    ).toBe('Gastos: R$ 99,90');
    expect(
      rotuloDoTooltip('bar', {
        parsed: { x: 50, y: 0 },
        label: 'Pix',
        dataset: {},
        chart: { options: { indexAxis: 'y' } },
      }),
    ).toBe('Pix: R$ 50,00');

    const vertical = opcoesPadrao('bar', CORES, 'x').scales as Record<
      string,
      { ticks: { callback?: Callback } }
    >;
    expect(semEspacoFixo(vertical['y'].ticks.callback?.call(undefined, 1500) as string)).toBe(
      'R$ 1.500,00',
    );
    expect(vertical['x'].ticks.callback).toBeUndefined();

    const horizontal = opcoesPadrao('bar', CORES, 'y').scales as Record<
      string,
      { ticks: { callback?: Callback } }
    >;
    expect(semEspacoFixo(horizontal['x'].ticks.callback?.call(undefined, 1500) as string)).toBe(
      'R$ 1.500,00',
    );
    expect(horizontal['y'].ticks.callback).toBeUndefined();
  });

  it('padroes_ptBR_e_cores_do_tema__CA_F04_30', () => {
    const linha = opcoesPadrao('line', CORES);
    expect(linha.locale).toBe('pt-BR');
    expect(linha.color).toBe(CORES.texto);
    expect(linha.plugins?.legend?.labels?.color).toBe(CORES.texto);
    const escalas = linha.scales as Record<
      string,
      { grid: { color: string }; ticks: { color: string } }
    >;
    expect(escalas['x'].grid.color).toBe(CORES.grade);
    expect(escalas['y'].ticks.color).toBe(CORES.texto);

    // Rosca não tem eixos: configurar `scales` nela criaria eixos indesejados.
    expect(opcoesPadrao('doughnut', CORES).scales).toBeUndefined();
  });
});
