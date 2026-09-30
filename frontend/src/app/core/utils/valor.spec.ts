import { formatarValor, interpretarValor, ResultadoValor } from './valor';

/** O `Intl` de pt-BR usa espaço fixo; aqui só há separadores, sem `R$`. */
describe('utils/valor (F-06 §3.2.1)', () => {
  const casos: [string, ResultadoValor][] = [
    ['42,5', { valor: 42.5 }],
    ['42,50', { valor: 42.5 }],
    ['1.234,56', { valor: 1234.56 }],
    ['12.345.678,9', { valor: 12345678.9 }],
    ['1234,56', { valor: 1234.56 }],
    ['1.234', { valor: 1234 }],
    ['1.234.567', { valor: 1234567 }],
    ['42.50', { valor: 42.5 }],
    ['1.5', { valor: 1.5 }],
    ['42', { valor: 42 }],
    ['R$ 10', { valor: 10 }],
    ['r$10,00', { valor: 10 }],
    [' 7 ', { valor: 7 }],
    ['0,00', { valor: 0 }], // interpretado; "maior que zero" é outra regra
    ['', { erro: 'vazio' }],
    ['   ', { erro: 'vazio' }],
    ['R$', { erro: 'vazio' }],
    ['0,001', { erro: 'casas' }],
    ['1.2345', { erro: 'casas' }],
    ['abc', { erro: 'invalido' }],
    ['1,2,3', { erro: 'invalido' }],
    ['12.34.5', { erro: 'invalido' }],
    ['-5', { erro: 'invalido' }],
    [',5', { erro: 'invalido' }],
    ['5,', { erro: 'invalido' }],
    ['1.23,45', { erro: 'invalido' }],
  ];

  for (const [texto, esperado] of casos) {
    it(`interpreta_valor_ptBR__CA_F06_14 [${JSON.stringify(texto)}]`, () => {
      expect(interpretarValor(texto)).toEqual(esperado);
    });
  }

  it('formata_ao_sair', () => {
    const semEspacoFixo = (texto: string) => texto.replace(/ /g, ' ');
    expect(semEspacoFixo(formatarValor(42.5))).toBe('42,50');
    expect(semEspacoFixo(formatarValor(1234.5))).toBe('1.234,50');
    expect(semEspacoFixo(formatarValor(9999999999.99))).toBe('9.999.999.999,99');
  });
});
