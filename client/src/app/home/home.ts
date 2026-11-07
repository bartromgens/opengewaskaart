import { Location } from '@angular/common';
import {
  Component,
  computed,
  ElementRef,
  OnDestroy,
  OnInit,
  ViewChild,
  inject,
  signal,
} from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import {
  Map as MapLibreMap,
  NavigationControl,
  type ExpressionSpecification,
  type MapLayerMouseEvent,
} from 'maplibre-gl';
import { firstValueFrom } from 'rxjs';

import {
  ApiService,
  type GewasGebruikMap,
  type GebruikSummary,
  type Gewasperceel,
  type GewasSummary,
} from '../api.service';
import {
  assignSelectedGewasColors,
  assignViewportGewasColors,
  buildGebruikFillColorExpression,
  buildGebruikLegendEntries,
  buildGewasFillColorExpression,
  buildGewascodeInLayerFilter,
  buildLegendEntries,
  buildSelectedGewasFillColorExpression,
  buildSelectedLegendEntries,
  buildViewportGewasFillColorExpression,
  buildViewportLegendEntries,
  formatHa,
  gewasDisplayColor,
  viewportGewasDisplayColor,
  type ColorMode,
  type LegendEntry,
} from '../crop-colors';
import { GewasFilterComponent } from '../gewas-filter/gewas-filter';
import { PerceelDetailPanelComponent } from '../perceel-detail-panel/perceel-detail-panel';
import { environment } from '../../environments/environment';

const PERCELEN_SOURCE = 'percelen';
const PERCELEN_LAYER = 'percelen';
const PERCELEN_FILL_LAYER = 'percelen-fill';
const PERCELEN_OUTLINE_LAYER = 'percelen-outline';

const DEFAULT_TILE_MIN_ZOOM = 5;
const DEFAULT_TILE_MAX_ZOOM = 16;
const DEFAULT_MAP_ZOOM = 7;
const DEFAULT_CENTER: [number, number] = [5.3, 52.2];
// Boundaries are useful once a field is large enough to read. Below this zoom
// a 1px stroke covers most of each parcel and hides the crop colors.
const OUTLINE_MIN_ZOOM = 12;
const MAP_GEWAS_COLOR_TOP_N = 8;
const VIEWPORT_GEWASSEN_TOP_N = 10;
const VIEWPORT_GEWASSEN_DYNAMIC_TOP_N = 15;
const VIEWPORT_GEWASSEN_DEBOUNCE_MS = 400;
const NETHERLANDS_BOUNDS = {
  west: 3.2,
  south: 50.75,
  east: 7.2,
  north: 53.7,
};
const WHOLE_COUNTRY_MARGIN_DEG = 0.15;

interface TileJson {
  minzoom?: number;
  maxzoom?: number;
  tiles?: string[];
  bounds?: [number, number, number, number];
}

@Component({
  selector: 'app-home',
  imports: [
    GewasFilterComponent,
    MatButtonToggleModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSlideToggleModule,
    PerceelDetailPanelComponent,
  ],
  templateUrl: './home.html',
  styleUrl: './home.scss',
})
export class HomeComponent implements OnInit, OnDestroy {
  @ViewChild('mapContainer', { static: true }) mapContainer!: ElementRef<HTMLDivElement>;

  private api = inject(ApiService);
  private location = inject(Location);
  private route = inject(ActivatedRoute);

  map: MapLibreMap | null = null;
  apiStatus = signal<string | null>(null);
  /** True until the parcel layer is added and its tiles have finished loading. */
  mapLoading = signal(true);
  /** Top gewassen used for map colours + legend (from /api/gewassen/?limit=). */
  legendEntries = signal<LegendEntry[]>([]);
  /** Map colouring: per gewas palette or veevoer/voedsel buckets from API. */
  colorMode = signal<ColorMode>('gewas');
  selectedParcel = signal<Gewasperceel | null>(null);
  parcelLoading = signal(false);
  parcelError = signal<string | null>(null);
  /** Full gewas list for the map filter (from `GET /api/gewassen/`). */
  allGewassen = signal<GewasSummary[]>([]);
  /** Multi-select filter; empty means show all gewassen. */
  selectedGewassen = signal<GewasSummary[]>([]);
  readonly selectedGewasColors = computed(() => assignSelectedGewasColors(this.selectedGewassen()));
  /** Top gewassen in the current map view (by area), from /api/gewassen/?bbox=. */
  viewportGewassen = signal<GewasSummary[]>([]);
  viewportGewassenLoading = signal(false);
  readonly showViewportGewassenPanel = computed(
    () => !this.viewportShowsWholeCountry() && this.viewportGewassen().length > 0,
  );
  readonly viewportTotalAreaM2 = computed(() =>
    this.viewportGewassen().reduce((sum, row) => sum + (row.area_m2 ?? 0), 0),
  );
  /** When on, map fill and gewas legend follow top crops in the current view. */
  viewportColors = signal(false);
  readonly viewportColorsToggleEnabled = computed(
    () => this.colorMode() === 'gewas' && this.selectedGewassen().length === 0,
  );
  readonly usesViewportColors = computed(
    () =>
      this.viewportColors() &&
      this.viewportColorsToggleEnabled() &&
      this.viewportGewassen().length > 0,
  );
  private readonly viewportGewasColorMap = computed(() =>
    assignViewportGewasColors(this.viewportGewassen()),
  );

  private selectedFeatureId: number | null = null;
  private parcelLayersAdded = false;
  private tileMinZoom = DEFAULT_TILE_MIN_ZOOM;
  private tileMaxZoom = DEFAULT_TILE_MAX_ZOOM;
  private tileJsonTiles: string[] | null = null;
  private tileJsonBounds: [number, number, number, number] | undefined;

  private topGewassenForMap: GewasSummary[] = [];
  private gewasFillExpression: ExpressionSpecification | null = null;
  private gebruikFillExpression: ExpressionSpecification | null = null;
  private gebruikSummaryRows: GebruikSummary[] = [];
  private pendingGewasFilterCodes: readonly number[] | null = null;
  private viewportFetchTimer: ReturnType<typeof setTimeout> | null = null;
  private viewportRequestId = 0;
  private viewportShowsWholeCountry = signal(true);
  private viewportFetchAllowed = false;

  ngOnInit(): void {
    this.colorMode.set(this.readColorModeFromQuery());
    this.viewportColors.set(this.readViewportColorsFromQuery());
    this.pendingGewasFilterCodes = this.readGewasCodesFromQuery();
    void this.initMap();
    this.loadHealth();
  }

  setColorMode(mode: ColorMode): void {
    if (this.colorMode() === mode) {
      return;
    }
    this.colorMode.set(mode);
    this.refreshLegendForColorMode();
    this.applyActiveFillPaint();
    this.updateUrlFromMap();
  }

  setViewportColors(enabled: boolean): void {
    if (!this.viewportColorsToggleEnabled() && enabled) {
      return;
    }
    if (this.viewportColors() === enabled) {
      return;
    }
    this.viewportColors.set(enabled);
    this.refreshLegendForColorMode();
    this.applyActiveFillPaint();
    this.scheduleViewportGewassenRefresh();
    this.updateUrlFromMap();
  }

  onGewasFilterChange(selected: GewasSummary[]): void {
    this.selectedGewassen.set(selected);
    this.applyParcelLayerGewasFilter();
    this.refreshLegendForColorMode();
    this.applyActiveFillPaint();
    this.clearParcelIfFilteredOut();
    this.scheduleViewportGewassenRefresh();
    this.updateUrlFromMap();
  }

  ngOnDestroy(): void {
    if (this.viewportFetchTimer !== null) {
      clearTimeout(this.viewportFetchTimer);
      this.viewportFetchTimer = null;
    }
    this.map?.remove();
  }

  viewportGewasColor(row: GewasSummary): string {
    if (this.usesViewportColors()) {
      return viewportGewasDisplayColor(row, this.viewportGewasColorMap());
    }
    return gewasDisplayColor(row.gewas, row.gewascode, this.topGewassenForMap);
  }

  viewportAreaSharePercent(row: GewasSummary): string | null {
    const total = this.viewportTotalAreaM2();
    if (total <= 0 || row.area_m2 == null) {
      return null;
    }
    return `${((100 * row.area_m2) / total).toFixed(1)}%`;
  }

  viewportAreaHa(row: GewasSummary): string {
    return formatHa(row.area_m2);
  }

  closeDetailPanel(): void {
    this.clearSelection();
    this.selectedParcel.set(null);
    this.parcelError.set(null);
    this.parcelLoading.set(false);
  }

  private async initMap(): Promise<void> {
    await this.loadTileZoomRange();

    const { center, zoom } = this.getInitialMapState();

    this.map = new MapLibreMap({
      container: this.mapContainer.nativeElement,
      style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
      center,
      zoom: Math.max(this.tileMinZoom, Math.min(this.tileMaxZoom, zoom)),
      minZoom: this.tileMinZoom,
    });

    this.map.addControl(new NavigationControl(), 'top-right');
    this.map.on('load', () => {
      void (async () => {
        const [top, mapping, allGewassen, summary] = await Promise.all([
          this.fetchTopGewassen(),
          this.fetchGewasGebruik(),
          this.fetchAllGewassen(),
          this.fetchGebruikSummary(),
        ]);
        this.allGewassen.set(allGewassen);
        this.applyPendingGewasSelectionFromQuery();
        this.addParcelLayers(top, mapping, summary);
        this.refreshLegendForColorMode();
      })();
    });
    // Derive loading state from the parcel source itself; the global 'idle'
    // event can be missed or delayed (e.g. basemap activity, failed tiles).
    const syncLoading = (): void => {
      if (!this.map || !this.parcelLayersAdded || !this.map.getSource(PERCELEN_SOURCE)) {
        return;
      }
      this.mapLoading.set(!this.map.isSourceLoaded(PERCELEN_SOURCE));
    };
    this.map.on('dataloading', syncLoading);
    this.map.on('sourcedata', syncLoading);
    this.map.on('moveend', syncLoading);
    this.map.on('idle', () => {
      if (this.parcelLayersAdded) {
        this.mapLoading.set(false);
      }
    });
    this.map.on('error', () => {
      if (this.parcelLayersAdded) {
        this.mapLoading.set(false);
      }
    });
    this.map.on('moveend', () => {
      this.updateUrlFromMap();
      this.scheduleViewportGewassenRefresh();
    });
    this.map.on('click', PERCELEN_FILL_LAYER, (event) => this.onParcelClick(event));
    this.map.on('mouseenter', PERCELEN_FILL_LAYER, () => {
      if (this.map) {
        this.map.getCanvas().style.cursor = 'pointer';
      }
    });
    this.map.on('mouseleave', PERCELEN_FILL_LAYER, () => {
      if (this.map) {
        this.map.getCanvas().style.cursor = '';
      }
    });
    this.map.on('click', (event) => {
      // Layer is added only after async fetch; querying missing layer throws.
      if (!this.map || !this.map.getLayer(PERCELEN_FILL_LAYER)) {
        return;
      }
      const features = this.map.queryRenderedFeatures(event.point, {
        layers: [PERCELEN_FILL_LAYER],
      });
      if (!features.length) {
        this.closeDetailPanel();
      }
    });
  }

  private async fetchTopGewassen(): Promise<GewasSummary[]> {
    try {
      return await firstValueFrom(this.api.getGewassen({ limit: MAP_GEWAS_COLOR_TOP_N }));
    } catch {
      return [];
    }
  }

  private async fetchGewasGebruik(): Promise<GewasGebruikMap[]> {
    try {
      return await firstValueFrom(this.api.getGewasGebruik());
    } catch {
      return [];
    }
  }

  private async fetchGebruikSummary(): Promise<GebruikSummary[]> {
    try {
      return await firstValueFrom(this.api.getGebruikSummary());
    } catch {
      return [];
    }
  }

  private async fetchAllGewassen(): Promise<GewasSummary[]> {
    try {
      return await firstValueFrom(this.api.getGewassen({}));
    } catch {
      return [];
    }
  }

  private addParcelLayers(
    topGewassen: GewasSummary[],
    gewasGebruik: GewasGebruikMap[],
    gebruikSummary: GebruikSummary[],
  ): void {
    if (!this.map || this.parcelLayersAdded) {
      return;
    }

    this.topGewassenForMap = topGewassen;
    this.gebruikSummaryRows = gebruikSummary;
    this.gewasFillExpression = buildGewasFillColorExpression(topGewassen);
    this.gebruikFillExpression =
      gewasGebruik.length > 0
        ? buildGebruikFillColorExpression(gewasGebruik)
        : this.gewasFillExpression;

    this.refreshLegendForColorMode();
    const fillColor = this.activeFillExpression();

    const sourceSpec: {
      type: 'vector';
      minzoom: number;
      maxzoom: number;
      url?: string;
      tiles?: string[];
      bounds?: [number, number, number, number];
    } = {
      type: 'vector',
      // Keep source minzoom at 0 so MapLibre requests tiles for the current map
      // zoom and can substitute loaded child tiles when zoomed out below the tile set minimum.
      minzoom: 0,
      maxzoom: this.tileMaxZoom,
    };

    if (this.tileJsonTiles?.length) {
      sourceSpec.tiles = this.tileJsonTiles;
      if (this.tileJsonBounds) {
        sourceSpec.bounds = this.tileJsonBounds;
      }
    } else {
      sourceSpec.url = environment.tilesUrl;
    }

    this.map.addSource(PERCELEN_SOURCE, sourceSpec);

    // zoom must be the top-level interpolate input. feature-state lives in the stops.
    const selectedCase = (selected: number, normal: number): ExpressionSpecification =>
      [
        'case',
        ['boolean', ['feature-state', 'selected'], false],
        selected,
        normal,
      ] as ExpressionSpecification;

    this.map.addLayer({
      id: PERCELEN_FILL_LAYER,
      type: 'fill',
      source: PERCELEN_SOURCE,
      'source-layer': PERCELEN_LAYER,
      paint: {
        'fill-color': fillColor,
        'fill-opacity': [
          'interpolate',
          ['linear'],
          ['zoom'],
          5,
          selectedCase(0.92, 0.88),
          13,
          selectedCase(0.9, 0.72),
          16,
          selectedCase(0.9, 0.62),
        ],
        // Same color as the fill, so shared edges do not draw a dark grid.
        'fill-outline-color': [
          'case',
          ['boolean', ['feature-state', 'selected'], false],
          '#1565c0',
          fillColor,
        ],
      },
    });

    if (gewasGebruik.length === 0 && this.colorMode() === 'gebruik') {
      this.colorMode.set('gewas');
    }

    this.map.addLayer({
      id: PERCELEN_OUTLINE_LAYER,
      type: 'line',
      source: PERCELEN_SOURCE,
      'source-layer': PERCELEN_LAYER,
      minzoom: OUTLINE_MIN_ZOOM,
      paint: {
        'line-color': [
          'case',
          ['boolean', ['feature-state', 'selected'], false],
          '#1565c0',
          '#4a4a4a',
        ],
        'line-opacity': [
          'interpolate',
          ['linear'],
          ['zoom'],
          OUTLINE_MIN_ZOOM,
          selectedCase(1, 0),
          13.5,
          selectedCase(1, 0.45),
          15,
          selectedCase(1, 0.8),
        ],
        'line-width': [
          'interpolate',
          ['linear'],
          ['zoom'],
          OUTLINE_MIN_ZOOM,
          selectedCase(2.5, 0.2),
          14,
          selectedCase(2.5, 0.6),
          16,
          selectedCase(2.5, 1.1),
        ],
      },
    });

    this.parcelLayersAdded = true;
    // Safety net: clear the indicator once the map settles after adding layers.
    this.map.once('idle', () => {
      this.mapLoading.set(false);
      this.viewportFetchAllowed = true;
      this.scheduleViewportGewassenRefresh();
    });
    this.applyParcelLayerGewasFilter();
    this.applyActiveFillPaint();
    this.updateUrlFromMap();
  }

  private activeFillExpression(): ExpressionSpecification {
    const selected = this.selectedGewassen();
    if (selected.length > 0 && this.colorMode() === 'gewas') {
      return buildSelectedGewasFillColorExpression(this.selectedGewasColors());
    }
    if (this.colorMode() === 'gebruik' && this.gebruikFillExpression) {
      return this.gebruikFillExpression;
    }
    if (this.usesViewportColors()) {
      return buildViewportGewasFillColorExpression(this.viewportGewassen());
    }
    return this.gewasFillExpression ?? buildGewasFillColorExpression([]);
  }

  private refreshLegendForColorMode(): void {
    if (this.colorMode() === 'gebruik') {
      this.legendEntries.set(buildGebruikLegendEntries(this.gebruikSummaryRows));
      return;
    }
    const selected = this.selectedGewassen();
    if (selected.length > 0) {
      this.legendEntries.set(buildSelectedLegendEntries(selected, this.selectedGewasColors()));
      return;
    }
    if (this.usesViewportColors()) {
      this.legendEntries.set(buildViewportLegendEntries(this.viewportGewassen()));
      return;
    }
    this.legendEntries.set(buildLegendEntries(this.topGewassenForMap));
  }

  private applyParcelLayerGewasFilter(): void {
    if (!this.map || !this.parcelLayersAdded) {
      return;
    }
    const codes = this.selectedGewassen().map((s) => s.gewascode);
    const filter = buildGewascodeInLayerFilter(codes);
    this.map.setFilter(PERCELEN_FILL_LAYER, filter);
    this.map.setFilter(PERCELEN_OUTLINE_LAYER, filter);
  }

  private clearParcelIfFilteredOut(): void {
    const parcel = this.selectedParcel();
    if (!parcel) {
      return;
    }
    const codes = this.selectedGewassen();
    if (codes.length > 0 && !codes.some((s) => s.gewascode === parcel.gewascode)) {
      this.closeDetailPanel();
    }
  }

  private applyPendingGewasSelectionFromQuery(): void {
    const pending = this.pendingGewasFilterCodes;
    this.pendingGewasFilterCodes = null;
    if (pending === null || pending.length === 0) {
      return;
    }
    const byCode = new Map(this.allGewassen().map((g) => [g.gewascode, g]));
    const chosen: GewasSummary[] = [];
    const seen = new Set<number>();
    for (const code of pending) {
      if (seen.has(code)) {
        continue;
      }
      const row = byCode.get(code);
      if (row) {
        seen.add(code);
        chosen.push(row);
      }
    }
    this.selectedGewassen.set(chosen);
  }

  private readGewasCodesFromQuery(): readonly number[] | null {
    const raw = this.route.snapshot.queryParamMap.get('gewas');
    if (raw === null || raw.trim() === '') {
      return null;
    }
    return raw
      .split(',')
      .map((s) => Number(s.trim()))
      .filter((n) => Number.isFinite(n));
  }

  private applyActiveFillPaint(): void {
    if (!this.map || !this.parcelLayersAdded || !this.map.getLayer(PERCELEN_FILL_LAYER)) {
      return;
    }
    const fill = this.activeFillExpression();
    this.map.setPaintProperty(PERCELEN_FILL_LAYER, 'fill-color', fill);
    this.map.setPaintProperty(PERCELEN_FILL_LAYER, 'fill-outline-color', [
      'case',
      ['boolean', ['feature-state', 'selected'], false],
      '#1565c0',
      fill,
    ] as ExpressionSpecification);
  }

  private onParcelClick(event: MapLayerMouseEvent): void {
    if (!this.map) {
      return;
    }

    const feature = event.features?.[0];
    const rawId = feature?.id ?? feature?.properties?.['id'];
    const parcelId = typeof rawId === 'number' ? rawId : Number(rawId);

    if (!Number.isFinite(parcelId)) {
      return;
    }

    event.preventDefault();
    this.selectFeature(parcelId);
    this.loadParcelDetail(parcelId, feature?.properties);
  }

  private loadParcelDetail(parcelId: number, tileProperties?: Record<string, unknown>): void {
    this.parcelLoading.set(true);
    this.parcelError.set(null);

    const tileGewas = tileProperties?.['gewas'];
    if (typeof tileGewas === 'string' && tileGewas.length > 0) {
      this.selectedParcel.set({
        id: parcelId,
        jaar: Number(tileProperties?.['jaar'] ?? 0),
        gewascode: Number(tileProperties?.['gewascode'] ?? 0),
        gewas: tileGewas,
        category: String(tileProperties?.['category'] ?? ''),
        status: String(tileProperties?.['status'] ?? ''),
        gebruik: 'onbekend',
        area_m2: null,
        geometry: { type: 'Polygon', coordinates: [] },
      });
    } else {
      this.selectedParcel.set(null);
    }

    this.api.getParcel(parcelId).subscribe({
      next: (parcel) => {
        this.selectedParcel.set(parcel);
        this.parcelLoading.set(false);
      },
      error: () => {
        this.parcelError.set('Kon perceelgegevens niet laden.');
        this.parcelLoading.set(false);
      },
    });
  }

  private selectFeature(id: number): void {
    this.clearSelection();
    this.selectedFeatureId = id;
    this.map?.setFeatureState(
      { source: PERCELEN_SOURCE, sourceLayer: PERCELEN_LAYER, id },
      { selected: true },
    );
  }

  private clearSelection(): void {
    if (this.map && this.selectedFeatureId !== null) {
      this.map.setFeatureState(
        { source: PERCELEN_SOURCE, sourceLayer: PERCELEN_LAYER, id: this.selectedFeatureId },
        { selected: false },
      );
    }
    this.selectedFeatureId = null;
  }

  private async loadTileZoomRange(): Promise<void> {
    try {
      const response = await fetch(environment.tilesUrl);
      if (!response.ok) {
        return;
      }

      const tilejson = (await response.json()) as TileJson;
      if (typeof tilejson.minzoom === 'number') {
        this.tileMinZoom = tilejson.minzoom;
      }
      if (typeof tilejson.maxzoom === 'number') {
        this.tileMaxZoom = tilejson.maxzoom;
      }
      if (Array.isArray(tilejson.tiles) && tilejson.tiles.length > 0) {
        this.tileJsonTiles = tilejson.tiles;
      }
      if (Array.isArray(tilejson.bounds) && tilejson.bounds.length === 4) {
        this.tileJsonBounds = tilejson.bounds as [number, number, number, number];
      }
    } catch {
      // Keep defaults when TileJSON is unavailable during startup.
    }
  }

  private loadHealth(): void {
    this.api.getHealth().subscribe({
      next: (response) => this.apiStatus.set(response.status),
      error: () => this.apiStatus.set('error'),
    });
  }

  private readColorModeFromQuery(): ColorMode {
    const kleur = this.route.snapshot.queryParamMap.get('kleur');
    return kleur === 'gebruik' ? 'gebruik' : 'gewas';
  }

  private readViewportColorsFromQuery(): boolean {
    return this.route.snapshot.queryParamMap.get('kleurInBeeld') === '1';
  }

  private getInitialMapState(): { center: [number, number]; zoom: number } {
    const params = this.route.snapshot.queryParamMap;
    const lat = params.get('lat');
    const lng = params.get('lng');
    const zoom = params.get('zoom');

    const lngValue = lng != null && !Number.isNaN(Number(lng)) ? Number(lng) : DEFAULT_CENTER[0];
    const latValue = lat != null && !Number.isNaN(Number(lat)) ? Number(lat) : DEFAULT_CENTER[1];
    const zoomValue = zoom != null && !Number.isNaN(Number(zoom)) ? Number(zoom) : DEFAULT_MAP_ZOOM;

    return {
      center: [lngValue, latValue],
      zoom: zoomValue,
    };
  }

  private updateUrlFromMap(): void {
    if (!this.map) {
      return;
    }

    const center = this.map.getCenter();
    const zoom = this.map.getZoom();
    this.location.replaceState('/', this.buildQueryString(center.lng, center.lat, zoom));
  }

  private scheduleViewportGewassenRefresh(): void {
    if (!this.viewportFetchAllowed) {
      return;
    }
    if (this.viewportFetchTimer !== null) {
      clearTimeout(this.viewportFetchTimer);
    }
    this.viewportFetchTimer = setTimeout(() => {
      this.viewportFetchTimer = null;
      void this.refreshViewportGewassen();
    }, VIEWPORT_GEWASSEN_DEBOUNCE_MS);
  }

  private isWholeCountryMapView(): boolean {
    if (!this.map) {
      return true;
    }
    const bounds = this.map.getBounds();
    const margin = WHOLE_COUNTRY_MARGIN_DEG;
    return (
      bounds.getWest() <= NETHERLANDS_BOUNDS.west + margin &&
      bounds.getSouth() <= NETHERLANDS_BOUNDS.south + margin &&
      bounds.getEast() >= NETHERLANDS_BOUNDS.east - margin &&
      bounds.getNorth() >= NETHERLANDS_BOUNDS.north - margin
    );
  }

  private async refreshViewportGewassen(): Promise<void> {
    if (!this.map || !this.parcelLayersAdded) {
      return;
    }

    const wholeCountry = this.isWholeCountryMapView();
    this.viewportShowsWholeCountry.set(wholeCountry);
    if (wholeCountry) {
      this.viewportGewassen.set([]);
      this.viewportGewassenLoading.set(false);
      this.refreshLegendForColorMode();
      this.applyActiveFillPaint();
      return;
    }

    const requestId = ++this.viewportRequestId;
    const bounds = this.map.getBounds();
    const bbox = `${bounds.getWest()},${bounds.getSouth()},${bounds.getEast()},${bounds.getNorth()}`;
    const gewasCodes = this.selectedGewassen().map((g) => g.gewascode);

    this.viewportGewassenLoading.set(true);
    try {
      const rows = await firstValueFrom(
        this.api.getGewassen({
          limit:
            this.viewportColors() && this.viewportColorsToggleEnabled()
              ? VIEWPORT_GEWASSEN_DYNAMIC_TOP_N
              : VIEWPORT_GEWASSEN_TOP_N,
          bbox,
          gewasCodes: gewasCodes.length > 0 ? gewasCodes : undefined,
        }),
      );
      if (requestId !== this.viewportRequestId) {
        return;
      }
      this.viewportGewassen.set(rows);
      this.refreshLegendForColorMode();
      this.applyActiveFillPaint();
    } catch {
      if (requestId !== this.viewportRequestId) {
        return;
      }
    } finally {
      if (requestId === this.viewportRequestId) {
        this.viewportGewassenLoading.set(false);
      }
    }
  }

  private buildQueryString(lng: number, lat: number, zoom: number): string {
    const params = new URLSearchParams();
    params.set('lat', lat.toFixed(5));
    params.set('lng', lng.toFixed(5));
    params.set('zoom', String(zoom));
    if (this.colorMode() === 'gebruik') {
      params.set('kleur', 'gebruik');
    }
    if (this.viewportColors()) {
      params.set('kleurInBeeld', '1');
    }
    const gewasCodes = this.selectedGewassen().map((g) => g.gewascode);
    if (gewasCodes.length > 0) {
      params.set('gewas', gewasCodes.join(','));
    }
    return params.toString();
  }
}
