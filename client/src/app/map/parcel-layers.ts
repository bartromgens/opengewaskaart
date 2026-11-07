import type { ExpressionSpecification, FilterSpecification, Map as MapLibreMap } from 'maplibre-gl';

import {
  PARCEL_MAP_ICON_MIN_ZOOM,
  buildCropIconImageExpression,
  buildParcelIconLayerFilter,
  loadParcelCropIconImages,
} from '../crop-icon-map';
import type { TileConfig } from './tilejson';

export const PERCELEN_SOURCE = 'percelen';
export const PERCELEN_LAYER = 'percelen';
export const PERCELEN_FILL_LAYER = 'percelen-fill';
export const PERCELEN_OUTLINE_LAYER = 'percelen-outline';
export const PERCELEN_ICON_LAYER = 'percelen-icon';
export const OUTLINE_MIN_ZOOM = 12;
export const SELECTED_PARCEL_COLOR = '#1565c0';

export function selectedCase(selected: number, normal: number): ExpressionSpecification {
  return ['case', ['boolean', ['feature-state', 'selected'], false], selected, normal];
}

export function selectedOutlineColor(fill: ExpressionSpecification): ExpressionSpecification {
  return [
    'case',
    ['boolean', ['feature-state', 'selected'], false],
    SELECTED_PARCEL_COLOR,
    fill,
  ] as ExpressionSpecification;
}

export function buildParcelSourceSpec(
  tileConfig: TileConfig,
  tilesUrl: string,
): {
  type: 'vector';
  minzoom: number;
  maxzoom: number;
  url?: string;
  tiles?: string[];
  bounds?: [number, number, number, number];
} {
  const sourceSpec: {
    type: 'vector';
    minzoom: number;
    maxzoom: number;
    url?: string;
    tiles?: string[];
    bounds?: [number, number, number, number];
  } = {
    type: 'vector',
    minzoom: 0,
    maxzoom: tileConfig.maxZoom,
  };

  if (tileConfig.tiles?.length) {
    sourceSpec.tiles = tileConfig.tiles;
    if (tileConfig.bounds) {
      sourceSpec.bounds = tileConfig.bounds;
    }
  } else {
    sourceSpec.url = tilesUrl;
  }

  return sourceSpec;
}

export function addParcelFillLayer(map: MapLibreMap, fillColor: ExpressionSpecification): void {
  map.addLayer({
    id: PERCELEN_FILL_LAYER,
    type: 'fill',
    source: PERCELEN_SOURCE,
    'source-layer': PERCELEN_LAYER,
    paint: {
      'fill-color': fillColor,
      'fill-opacity': [
        'interpolate',
        ['linear'],
        ['zoom'],
        5,
        selectedCase(0.92, 0.88),
        13,
        selectedCase(0.9, 0.72),
        16,
        selectedCase(0.9, 0.62),
      ],
      'fill-outline-color': selectedOutlineColor(fillColor),
    },
  });
}

export function addParcelOutlineLayer(map: MapLibreMap): void {
  map.addLayer({
    id: PERCELEN_OUTLINE_LAYER,
    type: 'line',
    source: PERCELEN_SOURCE,
    'source-layer': PERCELEN_LAYER,
    minzoom: OUTLINE_MIN_ZOOM,
    paint: {
      'line-color': [
        'case',
        ['boolean', ['feature-state', 'selected'], false],
        SELECTED_PARCEL_COLOR,
        '#4a4a4a',
      ],
      'line-opacity': [
        'interpolate',
        ['linear'],
        ['zoom'],
        OUTLINE_MIN_ZOOM,
        selectedCase(1, 0),
        13.5,
        selectedCase(1, 0.45),
        15,
        selectedCase(1, 0.8),
      ],
      'line-width': [
        'interpolate',
        ['linear'],
        ['zoom'],
        OUTLINE_MIN_ZOOM,
        selectedCase(2.5, 0.2),
        14,
        selectedCase(2.5, 0.6),
        16,
        selectedCase(2.5, 1.1),
      ],
    },
  });
}

export async function addParcelIconLayer(map: MapLibreMap): Promise<void> {
  try {
    await loadParcelCropIconImages(map);
  } catch {
    return;
  }
  if (map.getLayer(PERCELEN_ICON_LAYER)) {
    return;
  }
  map.addLayer({
    id: PERCELEN_ICON_LAYER,
    type: 'symbol',
    source: PERCELEN_SOURCE,
    'source-layer': PERCELEN_LAYER,
    minzoom: PARCEL_MAP_ICON_MIN_ZOOM,
    filter: buildParcelIconLayerFilter([]),
    layout: {
      'icon-image': buildCropIconImageExpression(),
      'icon-size': ['interpolate', ['linear'], ['zoom'], PARCEL_MAP_ICON_MIN_ZOOM, 0.18, 16, 0.28],
      'icon-allow-overlap': true,
      'icon-ignore-placement': true,
    },
  });
}

export function setParcelFill(map: MapLibreMap, fill: ExpressionSpecification): void {
  if (!map.getLayer(PERCELEN_FILL_LAYER)) {
    return;
  }
  map.setPaintProperty(PERCELEN_FILL_LAYER, 'fill-color', fill);
  map.setPaintProperty(PERCELEN_FILL_LAYER, 'fill-outline-color', selectedOutlineColor(fill));
}

export function setParcelFeatureSelected(map: MapLibreMap, id: number, selected: boolean): void {
  map.setFeatureState({ source: PERCELEN_SOURCE, sourceLayer: PERCELEN_LAYER, id }, { selected });
}

export function setParcelLayersFilter(
  map: MapLibreMap,
  filter: FilterSpecification | null,
  gewasCodes: number[] = [],
): void {
  map.setFilter(PERCELEN_FILL_LAYER, filter);
  map.setFilter(PERCELEN_OUTLINE_LAYER, filter);
  if (map.getLayer(PERCELEN_ICON_LAYER)) {
    map.setFilter(PERCELEN_ICON_LAYER, buildParcelIconLayerFilter(gewasCodes));
  }
}
