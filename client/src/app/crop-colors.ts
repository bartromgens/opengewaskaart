import type { ExpressionSpecification } from 'maplibre-gl';

export const DEFAULT_CATEGORY_COLOR = '#bdbdbd';

export const CATEGORY_COLORS: Record<string, string> = {
  Granen: '#f4d03f',
  Grasland: '#58d68d',
  Aardappelen: '#d68910',
  Bieten: '#8e44ad',
  'Maïs': '#a9dfbf',
  Fruit: '#e74c3c',
  'Blijvend teeltgewas': '#1e8449',
  Bloembollen: '#f1948a',
  Overig: '#95a5a6',
};

export function buildCategoryFillColorExpression(): ExpressionSpecification {
  const pairs = Object.entries(CATEGORY_COLORS).flatMap(([category, color]) => [
    category,
    color,
  ]);

  return [
    'match',
    ['get', 'category'],
    ...pairs,
    DEFAULT_CATEGORY_COLOR,
  ] as unknown as ExpressionSpecification;
}
