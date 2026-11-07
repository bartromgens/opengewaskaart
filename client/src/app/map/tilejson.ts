export const DEFAULT_TILE_MIN_ZOOM = 5;
export const DEFAULT_TILE_MAX_ZOOM = 16;

interface TileJson {
  minzoom?: number;
  maxzoom?: number;
  tiles?: string[];
  bounds?: [number, number, number, number];
}

export interface TileConfig {
  minZoom: number;
  maxZoom: number;
  tiles: string[] | null;
  bounds: [number, number, number, number] | undefined;
}

export async function loadTileConfig(url: string): Promise<TileConfig> {
  const defaults: TileConfig = {
    minZoom: DEFAULT_TILE_MIN_ZOOM,
    maxZoom: DEFAULT_TILE_MAX_ZOOM,
    tiles: null,
    bounds: undefined,
  };

  try {
    const response = await fetch(url);
    if (!response.ok) {
      return defaults;
    }

    const tilejson = (await response.json()) as TileJson;
    return {
      minZoom: typeof tilejson.minzoom === 'number' ? tilejson.minzoom : DEFAULT_TILE_MIN_ZOOM,
      maxZoom: typeof tilejson.maxzoom === 'number' ? tilejson.maxzoom : DEFAULT_TILE_MAX_ZOOM,
      tiles: Array.isArray(tilejson.tiles) && tilejson.tiles.length > 0 ? tilejson.tiles : null,
      bounds:
        Array.isArray(tilejson.bounds) && tilejson.bounds.length === 4
          ? (tilejson.bounds as [number, number, number, number])
          : undefined,
    };
  } catch {
    return defaults;
  }
}
