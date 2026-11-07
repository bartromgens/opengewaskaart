import { cropIconPath, gewasHoverPopupHtml } from './crop-icons';

describe('cropIconPath', () => {
  it('returns null for empty names', () => {
    expect(cropIconPath('')).toBeNull();
    expect(cropIconPath('   ')).toBeNull();
  });

  it('matches common Dutch gewas names', () => {
    expect(cropIconPath('Grasland, blijvend')).toContain('grasland.svg');
    expect(cropIconPath('Maïs')).toContain('corn.svg');
    expect(cropIconPath('Wintertarwe')).toContain('wheat.svg');
    expect(cropIconPath('Aardappel, consumptie-')).toContain('russet-potato.svg');
    expect(cropIconPath('Bloembollen, tulp')).toContain('tulip.svg');
    expect(cropIconPath('Suikerbiet')).toContain('beet.svg');
    expect(cropIconPath('Ui, zaai-ui')).toContain('yellow-onion.svg');
    expect(cropIconPath('Uien, zilver-')).toContain('yellow-onion.svg');
    expect(cropIconPath('Uien, poot en plant, 1e jaars')).toContain('yellow-onion.svg');
    expect(cropIconPath('Spruitkool')).toContain('brussel-sprout.svg');
    expect(cropIconPath('Broccoli')).toContain('broccoli.svg');
    expect(cropIconPath('Courgette, productie')).toContain('zucchini.svg');
    expect(cropIconPath('Vlas, vezel-')).toBeNull();
    expect(cropIconPath('Bonen, witte-')).toContain('broad-bean.svg');
    expect(cropIconPath('Pronkbonen, productie')).toContain('broad-bean.svg');
    expect(cropIconPath('Stamsperziebonen (=stamslabonen), zaden')).toContain('broad-bean.svg');
    expect(cropIconPath('Kapucijners (en grauwe erwten)')).toContain('broad-bean.svg');
    expect(cropIconPath('Pruimen')).toContain('plum.svg');
    expect(cropIconPath('Bessen, blauwe')).toContain('blueberry.svg');
    expect(cropIconPath('Bessen, rode')).toContain('raspberry.svg');
    expect(
      cropIconPath('Bessen, zwarte (opbrengst verwerkt voor verwerkende industrie)'),
    ).toContain('blackberry.svg');
    expect(cropIconPath('Frambozen')).toContain('raspberry.svg');
    expect(cropIconPath('Trek- en besheesters, open grond')).toBeNull();
  });

  it('prefers aardappel over appel', () => {
    expect(cropIconPath('Aardappel, zetmeel-')).toContain('russet-potato.svg');
    expect(cropIconPath('Appel, consumptie')).toContain('generic-apple.svg');
  });

  it('excludes koolzaad from cabbage icon', () => {
    expect(cropIconPath('Koolzaad')).toBeNull();
    expect(cropIconPath('Boerenkool')).toContain('green-cabbage.svg');
  });
});

describe('gewasHoverPopupHtml', () => {
  it('includes an img when a crop icon exists', () => {
    const html = gewasHoverPopupHtml('Wintertarwe');
    expect(html).toContain('parcel-gewas-popup-icon');
    expect(html).toContain('wheat.svg');
    expect(html).toContain('Wintertarwe');
  });

  it('escapes gewas text and omits img without a match', () => {
    expect(gewasHoverPopupHtml('Koolzaad')).toBe('Koolzaad');
    expect(gewasHoverPopupHtml('A & B <test>')).toBe('A &amp; B &lt;test&gt;');
  });
});
