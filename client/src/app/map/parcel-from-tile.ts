import type { Gewasperceel } from '../api.service';

export function parcelFromTileProperties(
  parcelId: number,
  tileProperties?: Record<string, unknown>,
): Gewasperceel | null {
  const tileGewas = tileProperties?.['gewas'];
  if (typeof tileGewas !== 'string' || tileGewas.length === 0) {
    return null;
  }
  return {
    id: parcelId,
    jaar: Number(tileProperties?.['jaar'] ?? 0),
    gewascode: Number(tileProperties?.['gewascode'] ?? 0),
    gewas: tileGewas,
    category: String(tileProperties?.['category'] ?? ''),
    status: String(tileProperties?.['status'] ?? ''),
    gebruik: 'onbekend',
    area_m2: null,
    geometry: { type: 'Polygon', coordinates: [] },
  };
}
