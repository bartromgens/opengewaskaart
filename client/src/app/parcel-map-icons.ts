import type { Feature, FeatureCollection, MultiPolygon, Point, Polygon } from 'geojson';
import type { MapGeoJSONFeature } from 'maplibre-gl';

import { PARCEL_MAP_ICON_MIN_AREA_M2, parcelIconMapId } from './crop-icon-map';
import { parcelAreaM2, parcelLabelPoint } from './parcel-geometry';

type IconPointProps = { icon: string };

function featureAreaM2(feature: MapGeoJSONFeature): number {
  const raw = feature.properties?.['area_m2'];
  if (raw !== undefined && raw !== null && raw !== '') {
    const parsed = Number(raw);
    if (Number.isFinite(parsed) && parsed > 0) {
      return parsed;
    }
  }
  const geom = feature.geometry;
  if (geom.type === 'Polygon' || geom.type === 'MultiPolygon') {
    return parcelAreaM2(geom as Polygon | MultiPolygon);
  }
  return 0;
}

function dedupeKey(feature: MapGeoJSONFeature, center: [number, number]): string {
  const code = feature.properties?.['gewascode'] ?? '';
  const lon = center[0].toFixed(5);
  const lat = center[1].toFixed(5);
  return `${code}:${lon}:${lat}`;
}

export function buildParcelIconFeatureCollection(
  features: MapGeoJSONFeature[],
  gewasCodes: number[],
  minAreaM2: number = PARCEL_MAP_ICON_MIN_AREA_M2,
): FeatureCollection<Point, IconPointProps> {
  const iconFeatures: Feature<Point, IconPointProps>[] = [];
  const seen = new Set<string>();
  const codeFilter = gewasCodes.length > 0 ? new Set(gewasCodes) : null;

  for (const feature of features) {
    const gewas = feature.properties?.['gewas'];
    if (typeof gewas !== 'string' || gewas.length === 0) {
      continue;
    }
    const gewascode = Number(feature.properties?.['gewascode']);
    if (codeFilter !== null && !codeFilter.has(gewascode)) {
      continue;
    }
    const mapId = parcelIconMapId(gewas);
    if (mapId === null) {
      continue;
    }
    const areaM2 = featureAreaM2(feature);
    if (areaM2 < minAreaM2) {
      continue;
    }
    const geom = feature.geometry;
    if (geom.type !== 'Polygon' && geom.type !== 'MultiPolygon') {
      continue;
    }
    const center = parcelLabelPoint(geom as Polygon | MultiPolygon);
    const key = dedupeKey(feature, [center[0], center[1]]);
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    iconFeatures.push({
      type: 'Feature',
      properties: { icon: mapId },
      geometry: { type: 'Point', coordinates: center },
    });
  }

  return { type: 'FeatureCollection', features: iconFeatures };
}
