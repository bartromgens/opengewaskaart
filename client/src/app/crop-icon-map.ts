import type { ExpressionSpecification, FilterSpecification, Map as MapLibreMap } from 'maplibre-gl';

import { buildGewascodeInLayerFilter } from './crop-colors';

/** Show parcel-centre crop icons from this zoom (detail tiles). */
export const PARCEL_MAP_ICON_MIN_ZOOM = 12;

/** Ignore smaller parcels (m²) so icons stay readable in the polygon centre. */
export const PARCEL_MAP_ICON_MIN_AREA_M2 = 10_000;

const OPEN = (slug: string): string => `/assets/crop-icons/open-crop-icons/${slug}.svg`;
const ORIG = (slug: string): string => `/assets/crop-icons/original/${slug}.svg`;

const gewasLc = (): ExpressionSpecification => ['downcase', ['coalesce', ['get', 'gewas'], '']];

const has = (needle: string): ExpressionSpecification => [
  '!=',
  ['index-of', needle, gewasLc()],
  -1,
];

const lacks = (needle: string): ExpressionSpecification => [
  '==',
  ['index-of', needle, gewasLc()],
  -1,
];

const starts = (needle: string): ExpressionSpecification => [
  '==',
  ['index-of', needle, gewasLc()],
  0,
];

type ParcelIconCase = {
  mapId: string;
  url: string;
  when: ExpressionSpecification;
  matches: (gewasLower: string) => boolean;
};

const beansJs = (g: string): boolean =>
  g.includes('bonen') ||
  g.includes('boon,') ||
  g.startsWith('boon ') ||
  g.includes('slaboon') ||
  g.includes('kapucijn');

const beansGl: ExpressionSpecification = [
  'any',
  has('bonen'),
  has('boon,'),
  starts('boon '),
  has('slaboon'),
  has('kapucijn'),
];

/** Same priority order as crop-icons.ts (keep in sync). */
const PARCEL_ICON_CASES: readonly ParcelIconCase[] = [
  {
    mapId: 'crop-russet-potato',
    url: OPEN('russet-potato'),
    when: has('aardappel'),
    matches: (g) => g.includes('aardappel'),
  },
  {
    mapId: 'crop-asparagus',
    url: OPEN('asparagus'),
    when: has('asperge'),
    matches: (g) => g.includes('asperge'),
  },
  {
    mapId: 'crop-brussel-sprout',
    url: OPEN('brussel-sprout'),
    when: has('spruitkool'),
    matches: (g) => g.includes('spruitkool'),
  },
  {
    mapId: 'crop-cauliflower',
    url: OPEN('cauliflower'),
    when: has('bloemkool'),
    matches: (g) => g.includes('bloemkool'),
  },
  {
    mapId: 'crop-broccoli',
    url: OPEN('broccoli'),
    when: ['any', has('broccoli'), has('brocoli')],
    matches: (g) => g.includes('broccoli') || g.includes('brocoli'),
  },
  {
    mapId: 'crop-zucchini',
    url: OPEN('zucchini'),
    when: has('courgette'),
    matches: (g) => g.includes('courgette'),
  },
  {
    mapId: 'crop-pumpkin',
    url: OPEN('pumpkin'),
    when: has('pompoen'),
    matches: (g) => g.includes('pompoen'),
  },
  {
    mapId: 'crop-tulip',
    url: ORIG('tulip'),
    when: ['any', has('tulp'), has('bloembollen')],
    matches: (g) => g.includes('tulp') || g.includes('bloembollen'),
  },
  {
    mapId: 'crop-flower-bulb',
    url: ORIG('flower-bulb'),
    when: [
      'any',
      has('lelie'),
      has('narcis'),
      has('overige bloemen'),
      has('bloemkwekerij'),
      has('pioenroos'),
      has('vaste planten'),
    ],
    matches: (g) =>
      g.includes('lelie') ||
      g.includes('narcis') ||
      g.includes('overige bloemen') ||
      g.includes('bloemkwekerij') ||
      g.includes('pioenroos') ||
      g.includes('vaste planten'),
  },
  {
    mapId: 'crop-grasland',
    url: ORIG('grasland'),
    when: [
      'any',
      has('grasland'),
      has('raaigras'),
      has('wild gras'),
      has('overige gras'),
      has('overige groenbemesters'),
      has('groene braak'),
      has('agrarisch natuurmengsel'),
      has('miscanthus'),
      has('olifantsgras'),
      has('drachtplanten'),
      has('luzerne'),
      has('klaver'),
    ],
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
    mapId: 'crop-corn',
    url: OPEN('corn'),
    when: ['any', has('maïs'), has('mais')],
    matches: (g) => g.includes('maïs') || g.includes('mais'),
  },
  {
    mapId: 'crop-sorghum-millet',
    url: OPEN('sorghum-millet'),
    when: ['any', has('sorghum'), has('soedangras'), has('japanse haver')],
    matches: (g) =>
      g.includes('sorghum') || g.includes('soedangras') || g.includes('japanse haver'),
  },
  {
    mapId: 'crop-wheat',
    url: OPEN('wheat'),
    when: ['any', has('tarwe'), has('triticale'), starts('granen,')],
    matches: (g) => g.includes('tarwe') || g.includes('triticale') || g.startsWith('granen,'),
  },
  {
    mapId: 'crop-sugar-beet',
    url: ORIG('sugar-beet'),
    when: ['all', has('biet'), has('suiker')],
    matches: (g) => g.includes('biet') && g.includes('suiker'),
  },
  {
    mapId: 'crop-beet',
    url: OPEN('beet'),
    when: has('biet'),
    matches: (g) => g.includes('biet'),
  },
  {
    mapId: 'crop-shallot',
    url: OPEN('shallot'),
    when: has('sjalot'),
    matches: (g) => g.includes('sjalot'),
  },
  {
    mapId: 'crop-yellow-onion',
    url: OPEN('yellow-onion'),
    when: ['any', starts('uien'), has('uien,')],
    matches: (g) => g.startsWith('uien') || g.includes('uien,'),
  },
  {
    mapId: 'crop-barley',
    url: OPEN('barley'),
    when: has('gerst'),
    matches: (g) => g.includes('gerst'),
  },
  {
    mapId: 'crop-rye',
    url: OPEN('rye'),
    when: has('rogge'),
    matches: (g) => g.includes('rogge'),
  },
  {
    mapId: 'crop-oat',
    url: OPEN('oat'),
    when: has('haver'),
    matches: (g) => g.includes('haver'),
  },
  {
    mapId: 'crop-carrot',
    url: OPEN('carrot'),
    when: ['any', has('peen'), has('wortel')],
    matches: (g) => g.includes('peen') || g.includes('wortel'),
  },
  {
    mapId: 'crop-bing-cherry',
    url: OPEN('bing-cherry'),
    when: has('kers'),
    matches: (g) => g.includes('kers'),
  },
  {
    mapId: 'crop-generic-apple',
    url: OPEN('generic-apple'),
    when: ['any', has('boomgaard'), has('fruitteelt'), has('appel')],
    matches: (g) => g.includes('boomgaard') || g.includes('fruitteelt') || g.includes('appel'),
  },
  {
    mapId: 'crop-pear',
    url: OPEN('pear'),
    when: ['any', has('peren'), has('peer')],
    matches: (g) => g.includes('peren') || g.includes('peer'),
  },
  {
    mapId: 'crop-plum',
    url: OPEN('plum'),
    when: has('pruim'),
    matches: (g) => g.includes('pruim'),
  },
  {
    mapId: 'crop-blueberry',
    url: OPEN('blueberry'),
    when: ['all', has('bessen'), has('blauw')],
    matches: (g) => g.includes('bessen') && g.includes('blauw'),
  },
  {
    mapId: 'crop-blackberry',
    url: OPEN('blackberry'),
    when: ['all', has('bessen'), has('zwart')],
    matches: (g) => g.includes('bessen') && g.includes('zwart'),
  },
  {
    mapId: 'crop-raspberry',
    url: OPEN('raspberry'),
    when: ['any', ['all', has('bessen'), ['any', has('rod'), has('rood')]], has('frambo')],
    matches: (g) =>
      (g.includes('bessen') && (g.includes('rod') || g.includes('rood'))) || g.includes('frambo'),
  },
  {
    mapId: 'crop-raspberry',
    url: OPEN('raspberry'),
    when: has('bessen'),
    matches: (g) => g.includes('bessen'),
  },
  {
    mapId: 'crop-belgian-endive',
    url: OPEN('belgian-endive'),
    when: ['any', has('cichorei'), has('witlof')],
    matches: (g) => g.includes('cichorei') || g.includes('witlof'),
  },
  {
    mapId: 'crop-leek',
    url: OPEN('leek'),
    when: has('prei'),
    matches: (g) => g.includes('prei'),
  },
  {
    mapId: 'crop-spinach',
    url: OPEN('spinach'),
    when: has('spinazie'),
    matches: (g) => g.includes('spinazie'),
  },
  {
    mapId: 'crop-green-cabbage',
    url: OPEN('green-cabbage'),
    when: [
      'all',
      has('kool'),
      lacks('spruit'),
      lacks('bloem'),
      lacks('broccoli'),
      lacks('brocoli'),
      lacks('koolzaad'),
    ],
    matches: (g) =>
      g.includes('kool') &&
      !g.includes('spruit') &&
      !g.includes('bloem') &&
      !g.includes('broccoli') &&
      !g.includes('brocoli') &&
      !g.includes('koolzaad'),
  },
  {
    mapId: 'crop-soy-bean',
    url: OPEN('soy-bean'),
    when: has('soja'),
    matches: (g) => g.includes('soja'),
  },
  {
    mapId: 'crop-broad-bean',
    url: OPEN('broad-bean'),
    when: beansGl,
    matches: beansJs,
  },
  {
    mapId: 'crop-snap-pea',
    url: OPEN('snap-pea'),
    when: has('erwt'),
    matches: (g) => g.includes('erwt'),
  },
  {
    mapId: 'crop-sunflower',
    url: OPEN('sunflower'),
    when: has('zonnebloem'),
    matches: (g) => g.includes('zonnebloem'),
  },
  {
    mapId: 'crop-sunflower',
    url: OPEN('sunflower'),
    when: ['any', has('tagetes'), has('afrikaantje')],
    matches: (g) => g.includes('tagetes') || g.includes('afrikaantje'),
  },
  {
    mapId: 'crop-hemp',
    url: OPEN('hemp'),
    when: has('hennep'),
    matches: (g) => g.includes('hennep'),
  },
  {
    mapId: 'crop-hop',
    url: OPEN('hop'),
    when: has('hop'),
    matches: (g) => /(^|[\s,(])hop([\s,)-]|$)/.test(g),
  },
  {
    mapId: 'crop-cotton',
    url: OPEN('cotton'),
    when: has('katoen'),
    matches: (g) => g.includes('katoen'),
  },
  {
    mapId: 'crop-rice',
    url: OPEN('rice'),
    when: has('rijst'),
    matches: (g) => g.includes('rijst'),
  },
  {
    mapId: 'crop-lettuce',
    url: OPEN('lettuce'),
    when: ['any', has('sla,'), starts('sla ')],
    matches: (g) => g.includes('sla,') || g.startsWith('sla '),
  },
  {
    mapId: 'crop-cucumber',
    url: OPEN('cucumber'),
    when: has('komkommer'),
    matches: (g) => g.includes('komkommer'),
  },
  {
    mapId: 'crop-tomato',
    url: OPEN('tomato'),
    when: has('tomaat'),
    matches: (g) => g.includes('tomaat'),
  },
  {
    mapId: 'crop-strawberry',
    url: OPEN('strawberry'),
    when: has('aardbei'),
    matches: (g) => g.includes('aardbei'),
  },
  {
    mapId: 'crop-turnip',
    url: OPEN('turnip'),
    when: has('raap'),
    matches: (g) => g.includes('raap'),
  },
  {
    mapId: 'crop-radish',
    url: OPEN('radish'),
    when: has('radijs'),
    matches: (g) => g.includes('radijs'),
  },
];

export function parcelIconMapId(gewas: string): string | null {
  if (!gewas.trim()) {
    return null;
  }
  const lower = gewas.toLowerCase();
  for (const row of PARCEL_ICON_CASES) {
    if (row.matches(lower)) {
      return row.mapId;
    }
  }
  return null;
}

export function buildCropIconImageExpression(): ExpressionSpecification {
  const branches: (ExpressionSpecification | string)[] = [];
  for (const row of PARCEL_ICON_CASES) {
    branches.push(row.when, row.mapId);
  }
  branches.push('');
  return ['case', ...branches] as unknown as ExpressionSpecification;
}

export function buildParcelIconLayerFilter(
  gewasCodes: number[],
  minAreaM2: number = PARCEL_MAP_ICON_MIN_AREA_M2,
): FilterSpecification {
  const areaOk: ExpressionSpecification = [
    'case',
    ['has', 'area_m2'],
    ['>=', ['coalesce', ['to-number', ['get', 'area_m2']], 0], minAreaM2],
    true,
  ] as unknown as ExpressionSpecification;
  const parts: (boolean | ExpressionSpecification)[] = [
    areaOk,
    ['!=', buildCropIconImageExpression(), ''],
  ];
  const gewasFilter = buildGewascodeInLayerFilter(gewasCodes);
  if (gewasFilter) {
    parts.push(gewasFilter as ExpressionSpecification);
  }
  return ['all', ...parts] as unknown as FilterSpecification;
}

function uniqueParcelIconImages(): Map<string, string> {
  const urls = new Map<string, string>();
  for (const row of PARCEL_ICON_CASES) {
    if (!urls.has(row.mapId)) {
      urls.set(row.mapId, row.url);
    }
  }
  return urls;
}

const MAP_ICON_PIXEL_SIZE = 128;

async function loadImage(map: MapLibreMap, id: string, url: string): Promise<void> {
  if (map.hasImage(id)) {
    return;
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load map icon ${url} (${response.status})`);
  }
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  try {
    const img = new Image();
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve();
      img.onerror = () => reject(new Error(`Failed to decode map icon ${url}`));
      img.src = objectUrl;
    });
    const canvas = document.createElement('canvas');
    canvas.width = MAP_ICON_PIXEL_SIZE;
    canvas.height = MAP_ICON_PIXEL_SIZE;
    const ctx = canvas.getContext('2d');
    if (ctx === null) {
      throw new Error('Canvas 2D context unavailable for map icons');
    }
    ctx.drawImage(img, 0, 0, MAP_ICON_PIXEL_SIZE, MAP_ICON_PIXEL_SIZE);
    try {
      if (typeof createImageBitmap === 'function') {
        const bitmap = await createImageBitmap(canvas);
        map.addImage(id, bitmap, { pixelRatio: 1 });
      } else {
        const imageData = ctx.getImageData(0, 0, MAP_ICON_PIXEL_SIZE, MAP_ICON_PIXEL_SIZE);
        map.addImage(id, imageData, { pixelRatio: 1 });
      }
    } catch {
      map.addImage(id, img, { pixelRatio: 2 });
    }
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

export async function loadParcelCropIconImages(map: MapLibreMap): Promise<void> {
  const images = uniqueParcelIconImages();
  const results = await Promise.allSettled([...images].map(([id, url]) => loadImage(map, id, url)));
  const loaded = results.filter((r) => r.status === 'fulfilled').length;
  if (loaded === 0) {
    throw new Error('No parcel crop icons could be loaded');
  }
}
