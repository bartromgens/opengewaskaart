import type { ParamMap } from '@angular/router';

import type { ColorMode } from '../crop-colors';

export const DEFAULT_CENTER: [number, number] = [5.3, 52.2];
export const DEFAULT_MAP_ZOOM = 7;

export interface MapUrlState {
  center: [number, number];
  zoom: number;
  colorMode: ColorMode;
  viewportColors: boolean;
  gewasCodes: readonly number[] | null;
}

export function readMapUrlState(params: ParamMap): MapUrlState {
  const kleur = params.get('kleur');
  const colorMode: ColorMode = kleur === 'gebruik' ? 'gebruik' : 'gewas';
  const viewportColors = params.get('kleurInBeeld') === '1';

  const lat = params.get('lat');
  const lng = params.get('lng');
  const zoom = params.get('zoom');

  const lngValue = lng != null && !Number.isNaN(Number(lng)) ? Number(lng) : DEFAULT_CENTER[0];
  const latValue = lat != null && !Number.isNaN(Number(lat)) ? Number(lat) : DEFAULT_CENTER[1];
  const zoomValue = zoom != null && !Number.isNaN(Number(zoom)) ? Number(zoom) : DEFAULT_MAP_ZOOM;

  const rawGewas = params.get('gewas');
  let gewasCodes: readonly number[] | null = null;
  if (rawGewas !== null && rawGewas.trim() !== '') {
    gewasCodes = rawGewas
      .split(',')
      .map((s) => Number(s.trim()))
      .filter((n) => Number.isFinite(n));
  }

  return {
    center: [lngValue, latValue],
    zoom: zoomValue,
    colorMode,
    viewportColors,
    gewasCodes,
  };
}

export interface MapQueryWriteState {
  lng: number;
  lat: number;
  zoom: number;
  colorMode: ColorMode;
  viewportColors: boolean;
  gewasCodes: number[];
}

export function buildMapQueryString(state: MapQueryWriteState): string {
  const params = new URLSearchParams();
  params.set('lat', state.lat.toFixed(5));
  params.set('lng', state.lng.toFixed(5));
  params.set('zoom', String(state.zoom));
  if (state.colorMode === 'gebruik') {
    params.set('kleur', 'gebruik');
  }
  if (state.viewportColors) {
    params.set('kleurInBeeld', '1');
  }
  if (state.gewasCodes.length > 0) {
    params.set('gewas', state.gewasCodes.join(','));
  }
  return params.toString();
}
