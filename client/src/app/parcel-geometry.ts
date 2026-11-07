import type { MultiPolygon, Polygon, Position } from 'geojson';

const M_PER_DEG_LAT = 111_320;

function ringCentroid(ring: Position[]): Position {
  let sumLon = 0;
  let sumLat = 0;
  let n = 0;
  for (const [lon, lat] of ring) {
    sumLon += lon;
    sumLat += lat;
    n += 1;
  }
  if (n === 0) {
    return [0, 0];
  }
  return [sumLon / n, sumLat];
}

function ringBBoxAreaM2(ring: Position[]): number {
  let minLon = Infinity;
  let maxLon = -Infinity;
  let minLat = Infinity;
  let maxLat = -Infinity;
  for (const [lon, lat] of ring) {
    minLon = Math.min(minLon, lon);
    maxLon = Math.max(maxLon, lon);
    minLat = Math.min(minLat, lat);
    maxLat = Math.max(maxLat, lat);
  }
  if (!Number.isFinite(minLon)) {
    return 0;
  }
  const latRad = (((minLat + maxLat) / 2) * Math.PI) / 180;
  const widthM = (maxLon - minLon) * M_PER_DEG_LAT * Math.cos(latRad);
  const heightM = (maxLat - minLat) * M_PER_DEG_LAT;
  return Math.max(0, widthM * heightM);
}

function polygonAreaAndCentroid(polygon: Polygon): { areaM2: number; center: Position } {
  const outer = polygon.coordinates[0];
  if (!outer?.length) {
    return { areaM2: 0, center: [0, 0] };
  }
  const center = ringCentroid(outer);
  let areaM2 = ringBBoxAreaM2(outer);
  for (let h = 1; h < polygon.coordinates.length; h += 1) {
    areaM2 -= ringBBoxAreaM2(polygon.coordinates[h]);
  }
  return { areaM2: Math.max(0, areaM2), center };
}

export function parcelAreaM2(geometry: Polygon | MultiPolygon): number {
  if (geometry.type === 'Polygon') {
    return polygonAreaAndCentroid(geometry).areaM2;
  }
  let total = 0;
  for (const poly of geometry.coordinates) {
    total += polygonAreaAndCentroid({ type: 'Polygon', coordinates: poly }).areaM2;
  }
  return total;
}

export function parcelLabelPoint(geometry: Polygon | MultiPolygon): Position {
  if (geometry.type === 'Polygon') {
    return polygonAreaAndCentroid(geometry).center;
  }
  let bestArea = 0;
  let bestCenter: Position = ringCentroid(geometry.coordinates[0]?.[0] ?? [[0, 0]]);
  for (const poly of geometry.coordinates) {
    const part = polygonAreaAndCentroid({ type: 'Polygon', coordinates: poly });
    if (part.areaM2 > bestArea) {
      bestArea = part.areaM2;
      bestCenter = part.center;
    }
  }
  return bestCenter;
}
