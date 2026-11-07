import type { LngLatBounds } from 'maplibre-gl';

export const NETHERLANDS_BOUNDS = {
  west: 3.2,
  south: 50.75,
  east: 7.2,
  north: 53.7,
};

const WHOLE_COUNTRY_MARGIN_DEG = 0.15;

export function isWholeCountryView(bounds: LngLatBounds): boolean {
  const margin = WHOLE_COUNTRY_MARGIN_DEG;
  return (
    bounds.getWest() <= NETHERLANDS_BOUNDS.west + margin &&
    bounds.getSouth() <= NETHERLANDS_BOUNDS.south + margin &&
    bounds.getEast() >= NETHERLANDS_BOUNDS.east - margin &&
    bounds.getNorth() >= NETHERLANDS_BOUNDS.north - margin
  );
}

export function bboxParam(bounds: LngLatBounds): string {
  return `${bounds.getWest()},${bounds.getSouth()},${bounds.getEast()},${bounds.getNorth()}`;
}
