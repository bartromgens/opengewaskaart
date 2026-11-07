import topRows from './crop-icons-top100.fixture.json';
import { cropIconPath } from './crop-icons';

type TopGewasRow = { gewas: string; parcel_count: number };

/** No matching icon in Open Crop Icons / our originals (landscape, water, wood, reed, etc.). */
const NO_ICON_GEWAS = new Set([
  'Sloot',
  'Houtwal en houtsingel',
  'Natuurterreinen (incl. heide)',
  'Bosje',
  'Knip- of scheerheg',
  'Elzensingel',
  'Boomgroep',
  'Struweelhaag',
  'Poel en klein historisch water',
  'Water, overig',
  'Struweelrand',
  'Ruigtes op landbouwpercelen',
  'Natuurvriendelijke oever',
  'Bossingel',
  'Laanbomen/parkbomen, opzetters, open grond',
  'Schouwpad',
  'Bos, blijvend, met herplantplicht',
  'Bos- en haagplanten, open grond',
  'Hakhoutbosje',
  'Sierheesters en klimplanten, open grond',
  'Laan',
  'Sierconiferen, open grond',
  'Rietland',
  'Laanbomen/parkbomen, spillen, open grond',
  'Sierheesters en klimplanten, pot- en containerveld',
  'Bos zonder herplantplicht',
  'Vlas, vezel-',
  'Tuunwallen',
  'Riet in water, anders dan een subsidiabele sloot',
  'Tijdelijk onbeteelde grond, anders dan voor publieke werken',
  'Overige niet genoemde groenten, productie',
  'Riet',
]);

describe('crop icons top 100 gewassen', () => {
  it('assigns icons to cultivable top gewassen when an icon exists', () => {
    const missing: string[] = [];
    const unexpected: string[] = [];

    for (const row of topRows as TopGewasRow[]) {
      const icon = cropIconPath(row.gewas);
      if (NO_ICON_GEWAS.has(row.gewas)) {
        if (icon !== null) {
          unexpected.push(row.gewas);
        }
        continue;
      }
      if (icon === null) {
        missing.push(row.gewas);
      }
    }

    expect(unexpected).toEqual([]);
    expect(missing).toEqual([]);
  });
});
