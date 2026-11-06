import type { ExpressionSpecification } from 'maplibre-gl';

import type { GebruikSummary, GewasGebruikKey, GewasGebruikMap, GewasSummary } from './api.service';

export type ColorMode = 'gewas' | 'gebruik';

/** Map layer colours per gebruik bucket (Okabe–Ito inspired, distinct from gewas palette). */
export const GEBRUIK_COLORS: Record<GewasGebruikKey, string> = {
  veevoer: '#E69F00',
  voedsel: '#009E73',
  gemengd: '#F0E442',
  niet_voedsel: '#CC79A7',
  onbekend: '#bdbdbd',
};

export const GEBRUIK_LABELS: Record<GewasGebruikKey, string> = {
  veevoer: 'Veevoer',
  voedsel: 'Voedsel',
  gemengd: 'Gemengd / onbekend eindgebruik',
  niet_voedsel: 'Niet voedsel of veevoer',
  onbekend: 'Onbekend',
};

export function gebruikLabel(gebruik: GewasGebruikKey): string {
  return GEBRUIK_LABELS[gebruik] ?? gebruik;
}

/** Fixed colours for gewas name patterns (checked before top-N palette). */
export const GRASLAND_GEWAS_COLOR = '#2E7D32';
export const MAIS_GEWAS_COLOR = '#FDD835';
export const TARWE_GEWAS_COLOR = '#F57C00';

/**
 * Eight Okabe–Ito inspired colours (skipping pure black for fill visibility).
 * Used for the eight most common gewassen (by parcel count from the API),
 * after fixed pattern colours.
 */
export const GEWAS_PALETTE: readonly string[] = [
  '#0072B2',
  '#E69F00',
  '#009E73',
  '#56B4E9',
  '#F0E442',
  '#D55E00',
  '#CC79A7',
  '#332288',
] as const;

/** Parcels that are not a fixed pattern and not in the top-N palette. */
export const OTHER_GEWAS_COLOR = '#6D4C41';

function orderedTopCodes(top: GewasSummary[]): number[] {
  const seen = new Set<number>();
  const codes: number[] = [];
  for (const row of top) {
    if (!seen.has(row.gewascode)) {
      seen.add(row.gewascode);
      codes.push(row.gewascode);
    }
  }
  return codes;
}

function paletteIndexForCode(gewascode: number, orderedCodes: readonly number[]): number {
  const idx = orderedCodes.indexOf(gewascode);
  return idx >= 0 && idx < GEWAS_PALETTE.length ? idx : -1;
}

/**
 * Mirrors map styling: fixed grasland / maïs / tarwe, then top-N by code, else brown.
 */
export function gewasDisplayColor(gewas: string, gewascode: number, top: GewasSummary[]): string {
  const lower = gewas.toLowerCase();
  if (lower.includes('grasland')) {
    return GRASLAND_GEWAS_COLOR;
  }
  if (lower.includes('maïs') || lower.includes('mais')) {
    return MAIS_GEWAS_COLOR;
  }
  if (lower.includes('tarwe')) {
    return TARWE_GEWAS_COLOR;
  }

  const codes = orderedTopCodes(top);
  const pidx = paletteIndexForCode(gewascode, codes);
  if (pidx >= 0) {
    return GEWAS_PALETTE[pidx]!;
  }
  return OTHER_GEWAS_COLOR;
}

/**
 * Fill colour: fixed patterns on lowercased gewas name, then top N by gewascode, else brown.
 */
export function buildGewasFillColorExpression(top: GewasSummary[]): ExpressionSpecification {
  const pairs: (number | string)[] = [];
  const seen = new Set<number>();

  for (const row of top) {
    if (seen.has(row.gewascode)) {
      continue;
    }
    seen.add(row.gewascode);
    const color = GEWAS_PALETTE[pairs.length / 2];
    if (color === undefined) {
      break;
    }
    pairs.push(row.gewascode, color);
  }

  const codeMatch: ExpressionSpecification = [
    'match',
    ['to-number', ['get', 'gewascode']],
    ...pairs,
    OTHER_GEWAS_COLOR,
  ] as unknown as ExpressionSpecification;

  const nameLower: ExpressionSpecification = [
    'downcase',
    ['to-string', ['get', 'gewas']],
  ] as unknown as ExpressionSpecification;

  return [
    'case',
    ['>=', ['index-of', 'grasland', nameLower], 0],
    GRASLAND_GEWAS_COLOR,
    [
      'any',
      ['>=', ['index-of', 'maïs', nameLower], 0],
      ['>=', ['index-of', 'mais', nameLower], 0],
    ],
    MAIS_GEWAS_COLOR,
    ['>=', ['index-of', 'tarwe', nameLower], 0],
    TARWE_GEWAS_COLOR,
    codeMatch,
  ] as unknown as ExpressionSpecification;
}

export interface LegendEntry {
  label: string;
  color: string;
}

export function buildLegendEntries(top: GewasSummary[]): LegendEntry[] {
  const seen = new Set<number>();
  const entries: LegendEntry[] = [];

  for (const row of top) {
    if (seen.has(row.gewascode)) {
      continue;
    }
    seen.add(row.gewascode);
    if (entries.length >= GEWAS_PALETTE.length) {
      break;
    }
    const color = gewasDisplayColor(row.gewas, row.gewascode, top);
    entries.push({ label: row.gewas, color });
  }

  entries.push({ label: 'Overig', color: OTHER_GEWAS_COLOR });
  return entries;
}

/**
 * Fill colour by tile property `gewascode`, using the API mapping `gewascode → gebruik`.
 */
export function buildGebruikFillColorExpression(mapping: GewasGebruikMap[]): ExpressionSpecification {
  const pairs: (number | string)[] = [];
  for (const row of mapping) {
    pairs.push(row.gewascode, GEBRUIK_COLORS[row.gebruik]);
  }
  return [
    'match',
    ['to-number', ['get', 'gewascode']],
    ...pairs,
    GEBRUIK_COLORS.onbekend,
  ] as unknown as ExpressionSpecification;
}

function formatHa(areaM2: number | null): string {
  if (areaM2 == null || !Number.isFinite(areaM2)) {
    return '—';
  }
  const ha = areaM2 / 10_000;
  return `${ha.toLocaleString('nl-NL', { minimumFractionDigits: 0, maximumFractionDigits: 1 })} ha`;
}

/**
 * Legend rows for gebruik mode with area share from `GET /api/gebruik/`.
 */
export function buildGebruikLegendEntries(summary: GebruikSummary[]): LegendEntry[] {
  const order: GewasGebruikKey[] = ['veevoer', 'voedsel', 'gemengd', 'niet_voedsel', 'onbekend'];
  const byGebruik = new Map(summary.map((s) => [s.gebruik, s]));
  const totalArea = summary.reduce((sum, s) => sum + (s.area_m2 ?? 0), 0);
  const totalParcels = summary.reduce((sum, s) => sum + s.parcel_count, 0);

  const entries: LegendEntry[] = [];
  for (const g of order) {
    const row = byGebruik.get(g);
    if (!row) {
      continue;
    }
    const haStr = formatHa(row.area_m2);
    let pctStr = '';
    if (totalArea > 0 && row.area_m2 != null) {
      pctStr = ` (${((100 * row.area_m2) / totalArea).toFixed(1)}%)`;
    } else if (totalParcels > 0) {
      pctStr = ` (${((100 * row.parcel_count) / totalParcels).toFixed(1)}% percelen)`;
    }
    entries.push({
      label: `${gebruikLabel(g)} — ${haStr}${pctStr}`,
      color: GEBRUIK_COLORS[g],
    });
  }
  return entries;
}
