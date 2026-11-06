import type { ExpressionSpecification } from 'maplibre-gl';

import type { GewasSummary } from './api.service';

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
