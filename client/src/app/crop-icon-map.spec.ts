import topRows from './crop-icons-top100.fixture.json';
import { cropIconPath } from './crop-icons';
import { parcelIconMapId } from './crop-icon-map';

type TopGewasRow = { gewas: string; parcel_count: number };

describe('parcel map icons vs cropIconPath', () => {
  it('matches cropIconPath for top-100 gewassen', () => {
    const mismatches: string[] = [];
    for (const row of topRows as TopGewasRow[]) {
      const path = cropIconPath(row.gewas);
      const mapId = parcelIconMapId(row.gewas);
      const pathMatches = path !== null;
      const mapMatches = mapId !== null;
      if (pathMatches !== mapMatches) {
        mismatches.push(row.gewas);
      }
    }
    expect(mismatches).toEqual([]);
  });
});
