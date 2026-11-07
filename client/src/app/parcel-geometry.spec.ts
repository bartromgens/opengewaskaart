import { parcelAreaM2, parcelLabelPoint } from './parcel-geometry';

describe('parcel geometry helpers', () => {
  it('approximates a ~1 ha square in the Netherlands', () => {
    const lat = 52.0;
    const dLat = 100 / 111_320;
    const dLon = 100 / (111_320 * Math.cos((lat * Math.PI) / 180));
    const ring: [number, number][] = [
      [5.0, lat],
      [5.0 + dLon, lat],
      [5.0 + dLon, lat + dLat],
      [5.0, lat + dLat],
      [5.0, lat],
    ];
    const polygon = { type: 'Polygon' as const, coordinates: [ring] };
    const area = parcelAreaM2(polygon);
    expect(area).toBeCloseTo(10_000, -1);
    const center = parcelLabelPoint(polygon);
    expect(center[0]).toBeGreaterThan(5.0);
    expect(center[1]).toBeGreaterThan(lat);
  });
});
