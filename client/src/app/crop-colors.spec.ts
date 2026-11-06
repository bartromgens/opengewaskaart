import type { GewasSummary } from './api.service';
import {
  assignSelectedGewasColors,
  buildGewascodeInLayerFilter,
  buildSelectedGewasFillColorExpression,
} from './crop-colors';

function mockRow(gewascode: number, gewas: string): GewasSummary {
  return {
    gewascode,
    gewas,
    category: 'x',
    parcel_count: 1,
    area_m2: 1,
    gebruik: 'onbekend',
    gebruik_geclassificeerd: false,
  };
}

describe('crop-colors gewas filter helpers', () => {
  it('assignSelectedGewasColors assigns stable distinct colors in selection order', () => {
    const selected = [mockRow(101, 'A'), mockRow(202, 'B'), mockRow(303, 'C')];
    const map1 = assignSelectedGewasColors(selected);
    expect(map1.size).toBe(3);
    expect(map1.get(101)).toBeDefined();
    expect(map1.get(202)).toBeDefined();
    expect(map1.get(303)).toBeDefined();
    expect(new Set(map1.values()).size).toBe(3);

    const map2 = assignSelectedGewasColors(selected);
    expect(map2.get(101)).toBe(map1.get(101));
    expect(map2.get(202)).toBe(map1.get(202));
    expect(map2.get(303)).toBe(map1.get(303));
  });

  it('buildGewascodeInLayerFilter returns null for empty codes', () => {
    expect(buildGewascodeInLayerFilter([])).toBeNull();
  });

  it('buildGewascodeInLayerFilter deduplicates codes', () => {
    const filter = buildGewascodeInLayerFilter([3, 3, 1, 2]);
    expect(filter).not.toBeNull();
    expect(filter).toEqual(['in', ['to-number', ['get', 'gewascode']], ['literal', [3, 1, 2]]]);
  });

  it('buildSelectedGewasFillColorExpression builds a match expression', () => {
    const colors = assignSelectedGewasColors([mockRow(7, 'X'), mockRow(8, 'Y')]);
    const expr = buildSelectedGewasFillColorExpression(colors);
    expect(Array.isArray(expr)).toBe(true);
    expect(expr[0]).toBe('match');
  });
});
