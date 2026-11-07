import type { ParamMap, Params } from '@angular/router';

import { buildMapQueryString, readMapUrlState } from './map-url-state';

function paramMap(params: Params): ParamMap {
  return {
    keys: Object.keys(params),
    get: (name: string) => params[name] ?? null,
    getAll: (name: string) => {
      const v = params[name];
      return v === undefined ? [] : Array.isArray(v) ? v : [v];
    },
    has: (name: string) => name in params,
  };
}

describe('readMapUrlState', () => {
  it('uses defaults when query params are absent', () => {
    const state = readMapUrlState(paramMap({}));
    expect(state.center).toEqual([5.3, 52.2]);
    expect(state.zoom).toBe(7);
    expect(state.colorMode).toBe('gewas');
    expect(state.viewportColors).toBe(false);
    expect(state.gewasCodes).toBeNull();
  });

  it('parses map position and options from query', () => {
    const state = readMapUrlState(
      paramMap({
        lat: '52.5',
        lng: '5.1',
        zoom: '10',
        kleur: 'gebruik',
        kleurInBeeld: '1',
        gewas: '1, 2, invalid, 3',
      }),
    );
    expect(state.center).toEqual([5.1, 52.5]);
    expect(state.zoom).toBe(10);
    expect(state.colorMode).toBe('gebruik');
    expect(state.viewportColors).toBe(true);
    expect(state.gewasCodes).toEqual([1, 2, 3]);
  });
});

describe('buildMapQueryString', () => {
  it('omits optional params when at defaults', () => {
    const qs = buildMapQueryString({
      lng: 5.3,
      lat: 52.2,
      zoom: 7,
      colorMode: 'gewas',
      viewportColors: false,
      gewasCodes: [],
    });
    expect(qs).toContain('lat=52.20000');
    expect(qs).toContain('lng=5.30000');
    expect(qs).not.toContain('kleur=');
    expect(qs).not.toContain('kleurInBeeld');
    expect(qs).not.toContain('gewas=');
  });

  it('includes non-default options', () => {
    const qs = buildMapQueryString({
      lng: 5,
      lat: 52,
      zoom: 12,
      colorMode: 'gebruik',
      viewportColors: true,
      gewasCodes: [10, 20],
    });
    expect(qs).toContain('kleur=gebruik');
    expect(qs).toContain('kleurInBeeld=1');
    expect(qs).toContain('gewas=10%2C20');
  });
});
