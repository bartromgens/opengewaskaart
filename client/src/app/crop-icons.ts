const OPEN_ICON = (slug: string): string => `/assets/crop-icons/open-crop-icons/${slug}.svg`;
const ORIGINAL_ICON = (slug: string): string => `/assets/crop-icons/original/${slug}.svg`;

type CropIconRule = {
  iconPath: string;
  matches: (gewasLower: string) => boolean;
};

const UI_PATTERN = /(^|[\s,(])ui([\s,)-]|$)/;
const HOP_PATTERN = /(^|[\s,(])hop([\s,)-]|$)/;

function matchesDutchBeanGewas(gewasLower: string): boolean {
  return (
    gewasLower.includes('bonen') ||
    gewasLower.includes('boon,') ||
    gewasLower.startsWith('boon ') ||
    gewasLower.includes('slaboon') ||
    gewasLower.includes('kapucijn')
  );
}

/** Substring rules in priority order (more specific gewas names first). */
const CROP_ICON_RULES: readonly CropIconRule[] = [
  { iconPath: OPEN_ICON('russet-potato'), matches: (g) => g.includes('aardappel') },
  { iconPath: OPEN_ICON('asparagus'), matches: (g) => g.includes('asperge') },
  { iconPath: OPEN_ICON('brussel-sprout'), matches: (g) => g.includes('spruitkool') },
  { iconPath: OPEN_ICON('cauliflower'), matches: (g) => g.includes('bloemkool') },
  {
    iconPath: OPEN_ICON('broccoli'),
    matches: (g) => g.includes('broccoli') || g.includes('brocoli'),
  },
  { iconPath: OPEN_ICON('zucchini'), matches: (g) => g.includes('courgette') },
  { iconPath: OPEN_ICON('pumpkin'), matches: (g) => g.includes('pompoen') },
  {
    iconPath: ORIGINAL_ICON('tulip'),
    matches: (g) => g.includes('tulp') || g.includes('bloembollen'),
  },
  {
    iconPath: ORIGINAL_ICON('flower-bulb'),
    matches: (g) =>
      g.includes('lelie') ||
      g.includes('narcis') ||
      g.includes('overige bloemen') ||
      g.includes('bloemkwekerij') ||
      g.includes('pioenroos') ||
      g.includes('vaste planten'),
  },
  {
    iconPath: ORIGINAL_ICON('grasland'),
    matches: (g) =>
      g.includes('grasland') ||
      g.includes('raaigras') ||
      g.includes('wild gras') ||
      g.includes('overige gras') ||
      g.includes('overige groenbemesters') ||
      g.includes('groene braak') ||
      g.includes('agrarisch natuurmengsel') ||
      g.includes('miscanthus') ||
      g.includes('olifantsgras') ||
      g.includes('drachtplanten') ||
      g.includes('luzerne') ||
      g.includes('klaver'),
  },
  {
    iconPath: OPEN_ICON('corn'),
    matches: (g) => g.includes('maïs') || g.includes('mais'),
  },
  {
    iconPath: OPEN_ICON('sorghum-millet'),
    matches: (g) =>
      g.includes('sorghum') || g.includes('soedangras') || g.includes('japanse haver'),
  },
  {
    iconPath: OPEN_ICON('wheat'),
    matches: (g) => g.includes('tarwe') || g.includes('triticale') || g.startsWith('granen,'),
  },
  { iconPath: OPEN_ICON('beet'), matches: (g) => g.includes('biet') },
  { iconPath: OPEN_ICON('shallot'), matches: (g) => g.includes('sjalot') },
  {
    iconPath: OPEN_ICON('yellow-onion'),
    matches: (g) => g.startsWith('uien') || g.includes('uien,'),
  },
  { iconPath: OPEN_ICON('yellow-onion'), matches: (g) => UI_PATTERN.test(g) },
  { iconPath: OPEN_ICON('barley'), matches: (g) => g.includes('gerst') },
  { iconPath: OPEN_ICON('rye'), matches: (g) => g.includes('rogge') },
  { iconPath: OPEN_ICON('oat'), matches: (g) => g.includes('haver') },
  { iconPath: OPEN_ICON('carrot'), matches: (g) => g.includes('peen') || g.includes('wortel') },
  { iconPath: OPEN_ICON('bing-cherry'), matches: (g) => g.includes('kers') },
  {
    iconPath: OPEN_ICON('generic-apple'),
    matches: (g) => g.includes('boomgaard') || g.includes('fruitteelt') || g.includes('appel'),
  },
  { iconPath: OPEN_ICON('pear'), matches: (g) => g.includes('peren') || g.includes('peer') },
  { iconPath: OPEN_ICON('plum'), matches: (g) => g.includes('pruim') },
  {
    iconPath: OPEN_ICON('blueberry'),
    matches: (g) => g.includes('bessen') && g.includes('blauw'),
  },
  {
    iconPath: OPEN_ICON('blackberry'),
    matches: (g) => g.includes('bessen') && g.includes('zwart'),
  },
  {
    iconPath: OPEN_ICON('raspberry'),
    matches: (g) =>
      (g.includes('bessen') && (g.includes('rod') || g.includes('rood'))) || g.includes('frambo'),
  },
  { iconPath: OPEN_ICON('raspberry'), matches: (g) => g.includes('bessen') },
  {
    iconPath: OPEN_ICON('belgian-endive'),
    matches: (g) => g.includes('cichorei') || g.includes('witlof'),
  },
  { iconPath: OPEN_ICON('leek'), matches: (g) => g.includes('prei') },
  { iconPath: OPEN_ICON('spinach'), matches: (g) => g.includes('spinazie') },
  {
    iconPath: OPEN_ICON('green-cabbage'),
    matches: (g) =>
      g.includes('kool') &&
      !g.includes('spruit') &&
      !g.includes('bloem') &&
      !g.includes('broccoli') &&
      !g.includes('brocoli') &&
      !g.includes('koolzaad'),
  },
  { iconPath: OPEN_ICON('soy-bean'), matches: (g) => g.includes('soja') },
  { iconPath: OPEN_ICON('broad-bean'), matches: (g) => matchesDutchBeanGewas(g) },
  { iconPath: OPEN_ICON('snap-pea'), matches: (g) => g.includes('erwt') },
  { iconPath: OPEN_ICON('sunflower'), matches: (g) => g.includes('zonnebloem') },
  {
    iconPath: OPEN_ICON('sunflower'),
    matches: (g) => g.includes('tagetes') || g.includes('afrikaantje'),
  },
  { iconPath: OPEN_ICON('hemp'), matches: (g) => g.includes('hennep') },
  { iconPath: OPEN_ICON('hop'), matches: (g) => HOP_PATTERN.test(g) },
  { iconPath: OPEN_ICON('cotton'), matches: (g) => g.includes('katoen') },
  { iconPath: OPEN_ICON('rice'), matches: (g) => g.includes('rijst') },
  { iconPath: OPEN_ICON('lettuce'), matches: (g) => g.includes('sla,') || g.startsWith('sla ') },
  { iconPath: OPEN_ICON('cucumber'), matches: (g) => g.includes('komkommer') },
  { iconPath: OPEN_ICON('tomato'), matches: (g) => g.includes('tomaat') },
  { iconPath: OPEN_ICON('strawberry'), matches: (g) => g.includes('aardbei') },
  { iconPath: OPEN_ICON('turnip'), matches: (g) => g.includes('raap') },
  { iconPath: OPEN_ICON('radish'), matches: (g) => g.includes('radijs') },
];

export function cropIconPath(gewas: string): string | null {
  if (!gewas.trim()) {
    return null;
  }
  const lower = gewas.toLowerCase();
  for (const rule of CROP_ICON_RULES) {
    if (rule.matches(lower)) {
      return rule.iconPath;
    }
  }
  return null;
}

function escapeHtml(text: string): string {
  return text
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

/** HTML for the map hover popup (icon optional). */
export function gewasHoverPopupHtml(gewas: string): string {
  const label = escapeHtml(gewas);
  const icon = cropIconPath(gewas);
  if (icon === null) {
    return label;
  }
  const src = escapeHtml(icon);
  return (
    `<span class="parcel-gewas-popup-inner">` +
    `<img class="parcel-gewas-popup-icon" src="${src}" alt="" />` +
    `<span>${label}</span></span>`
  );
}
