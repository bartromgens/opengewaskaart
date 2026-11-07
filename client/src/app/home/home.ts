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
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import {
  Map as MapLibreMap,
  NavigationControl,
  Popup,
  type ExpressionSpecification,
  type GeoJSONSource,
  type MapGeoJSONFeature,
  type MapLayerMouseEvent,
} from 'maplibre-gl';
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
  gewasDisplayColor,
  viewportGewasDisplayColor,
  type ColorMode,
  type LegendEntry,
} from '../crop-colors';
import { gewasHoverPopupHtml } from '../crop-icons';
import { PARCEL_MAP_ICON_MIN_ZOOM } from '../crop-icon-map';
import { buildParcelIconFeatureCollection } from '../parcel-map-icons';
import { GewasFilterComponent } from '../gewas-filter/gewas-filter';
import { PerceelDetailPanelComponent } from '../perceel-detail-panel/perceel-detail-panel';
import { MapLegendComponent, type ViewportLegendRow } from '../map-legend/map-legend';
import { fetchOr } from '../map/fetch-or';
import { buildMapQueryString, readMapUrlState } from '../map/map-url-state';
import { parcelFromTileProperties } from '../map/parcel-from-tile';
import {
  EMPTY_ICON_FEATURES,
  PARCEL_ICONS_SOURCE,
  PERCELEN_FILL_LAYER,
  PERCELEN_ICON_LAYER,
  PERCELEN_SOURCE,
  addParcelFillLayer,
  addParcelIconLayer,
  addParcelOutlineLayer,
  buildParcelSourceSpec,
  setParcelFeatureSelected,
  setParcelFill,
  setParcelLayersFilter,
} from '../map/parcel-layers';
import { loadTileConfig, type TileConfig } from '../map/tilejson';
import { bboxParam, isWholeCountryView } from '../map/viewport';
import { environment } from '../../environments/environment';

const PARCEL_ICON_REFRESH_MS = 200;
const HOVER_GEWAS_MIN_ZOOM = 11;
const MAP_GEWAS_COLOR_TOP_N = 8;
const VIEWPORT_GEWASSEN_TOP_N = 10;
const VIEWPORT_GEWASSEN_DYNAMIC_TOP_N = 15;
const VIEWPORT_GEWASSEN_DEBOUNCE_MS = 400;

@Component({
  selector: 'app-home',
  imports: [
    GewasFilterComponent,
    MapLegendComponent,
    MatButtonModule,
    MatButtonToggleModule,
    MatIconModule,
    MatProgressSpinnerModule,
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
  readonly showApiStatus = !environment.production;
  apiStatus = signal<string | null>(null);
  mapLoading = signal(true);
  legendEntries = signal<LegendEntry[]>([]);
  colorMode = signal<ColorMode>('gewas');
  selectedParcel = signal<Gewasperceel | null>(null);
  parcelLoading = signal(false);
  parcelError = signal<string | null>(null);
  allGewassen = signal<GewasSummary[]>([]);
  selectedGewassen = signal<GewasSummary[]>([]);
  readonly selectedGewasColors = computed(() => assignSelectedGewasColors(this.selectedGewassen()));
  viewportGewassen = signal<GewasSummary[]>([]);
  viewportGewassenLoading = signal(false);
  readonly showViewportGewassenPanel = computed(
    () => !this.viewportShowsWholeCountry() && this.viewportGewassen().length > 0,
  );
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

  readonly viewportLegendRows = computed((): ViewportLegendRow[] => {
    const rows = this.viewportGewassen();
    const colorMap = this.viewportGewasColorMap();
    const top = this.topGewassenForMap;
    return rows.map((row) => ({
      gewas: row.gewas,
      gewascode: row.gewascode,
      areaM2: row.area_m2,
      color: this.usesViewportColors()
        ? viewportGewasDisplayColor(row, colorMap)
        : gewasDisplayColor(row.gewas, row.gewascode, top),
    }));
  });

  private selectedFeatureId: number | null = null;
  private parcelLayersAdded = false;
  private tileConfig: TileConfig | null = null;

  private topGewassenForMap: GewasSummary[] = [];
  private gewasFillExpression: ExpressionSpecification | null = null;
  private gebruikFillExpression: ExpressionSpecification | null = null;
  private gebruikSummaryRows: GebruikSummary[] = [];
  private pendingGewasFilterCodes: readonly number[] | null = null;
  private viewportFetchTimer: ReturnType<typeof setTimeout> | null = null;
  private parcelIconRefreshTimer: ReturnType<typeof setTimeout> | null = null;
  private viewportRequestId = 0;
  private viewportShowsWholeCountry = signal(true);
  private viewportFetchAllowed = false;
  private hoverGewasPopup: Popup | null = null;

  ngOnInit(): void {
    const urlState = readMapUrlState(this.route.snapshot.queryParamMap);
    this.colorMode.set(urlState.colorMode);
    this.viewportColors.set(urlState.viewportColors);
    this.pendingGewasFilterCodes = urlState.gewasCodes;
    void this.initMap(urlState);
    if (this.showApiStatus) {
      this.loadHealth();
    }
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
    this.clearHoverGewasPopup();
    this.map?.remove();
  }

  closeDetailPanel(): void {
    this.clearSelection();
    this.selectedParcel.set(null);
    this.parcelError.set(null);
    this.parcelLoading.set(false);
  }

  private async initMap(urlState: ReturnType<typeof readMapUrlState>): Promise<void> {
    this.tileConfig = await loadTileConfig(environment.tilesUrl);
    const cfg = this.tileConfig;

    this.map = new MapLibreMap({
      container: this.mapContainer.nativeElement,
      style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
      center: urlState.center,
      zoom: Math.max(cfg.minZoom, Math.min(cfg.maxZoom, urlState.zoom)),
      minZoom: cfg.minZoom,
    });

    this.map.addControl(new NavigationControl(), 'top-right');
    this.hoverGewasPopup = new Popup({
      closeButton: false,
      closeOnClick: false,
      offset: 12,
      className: 'parcel-gewas-popup',
    });

    this.map.on('load', () => {
      void (async () => {
        const [top, mapping, allGewassen, summary] = await Promise.all([
          fetchOr(this.api.getGewassen({ limit: MAP_GEWAS_COLOR_TOP_N }), []),
          fetchOr(this.api.getGewasGebruik(), []),
          fetchOr(this.api.getGewassen({}), []),
          fetchOr(this.api.getGebruikSummary(), []),
        ]);
        this.allGewassen.set(allGewassen);
        this.applyPendingGewasSelectionFromQuery();
        this.addParcelLayers(top, mapping, summary);
        this.refreshLegendForColorMode();
      })();
    });

    this.registerMapEvents();
  }

  private registerMapEvents(): void {
    if (!this.map) {
      return;
    }

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
      this.scheduleParcelIconRefresh();
    });
    this.map.on('click', PERCELEN_FILL_LAYER, (event) => this.onParcelClick(event));
    this.map.on('mouseenter', PERCELEN_FILL_LAYER, () => {
      if (this.map) {
        this.map.getCanvas().style.cursor = 'pointer';
      }
    });
    this.map.on('mousemove', PERCELEN_FILL_LAYER, (event) => this.onParcelHoverMove(event));
    this.map.on('mouseleave', PERCELEN_FILL_LAYER, () => {
      if (this.map) {
        this.map.getCanvas().style.cursor = '';
      }
      this.clearHoverGewasPopup();
    });
    this.map.on('zoom', () => {
      if (this.map && this.map.getZoom() < HOVER_GEWAS_MIN_ZOOM) {
        this.clearHoverGewasPopup();
      }
      this.scheduleParcelIconRefresh();
    });
    this.map.on('click', (event) => {
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

  private addParcelLayers(
    topGewassen: GewasSummary[],
    gewasGebruik: GewasGebruikMap[],
    gebruikSummary: GebruikSummary[],
  ): void {
    if (!this.map || this.parcelLayersAdded || !this.tileConfig) {
      return;
    }

    this.topGewassenForMap = topGewassen;
    this.gebruikSummaryRows = gebruikSummary;
    this.gewasFillExpression = buildGewasFillColorExpression(topGewassen);
    this.gebruikFillExpression =
      gewasGebruik.length > 0
        ? buildGebruikFillColorExpression(gewasGebruik)
        : this.gewasFillExpression;

    const fillColor = this.activeFillExpression();

    this.map.addSource(
      PERCELEN_SOURCE,
      buildParcelSourceSpec(this.tileConfig, environment.tilesUrl),
    );
    addParcelFillLayer(this.map, fillColor);
    addParcelOutlineLayer(this.map);

    if (gewasGebruik.length === 0 && this.colorMode() === 'gebruik') {
      this.colorMode.set('gewas');
    }

    void addParcelIconLayer(this.map).then(() => this.scheduleParcelIconRefresh());

    this.parcelLayersAdded = true;
    this.map.once('idle', () => {
      this.mapLoading.set(false);
      this.viewportFetchAllowed = true;
      this.scheduleViewportGewassenRefresh();
      this.scheduleParcelIconRefresh();
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
    setParcelLayersFilter(this.map, buildGewascodeInLayerFilter(codes));
    this.scheduleParcelIconRefresh();
  }

  private scheduleParcelIconRefresh(): void {
    if (this.parcelIconRefreshTimer !== null) {
      clearTimeout(this.parcelIconRefreshTimer);
    }
    this.parcelIconRefreshTimer = setTimeout(() => {
      this.parcelIconRefreshTimer = null;
      this.refreshParcelIconsFromView();
    }, PARCEL_ICON_REFRESH_MS);
  }

  private refreshParcelIconsFromView(): void {
    if (!this.map) {
      return;
    }
    const source = this.map.getSource(PARCEL_ICONS_SOURCE) as GeoJSONSource | undefined;
    if (!source || !this.map.getLayer(PERCELEN_ICON_LAYER)) {
      return;
    }
    if (this.map.getZoom() < PARCEL_MAP_ICON_MIN_ZOOM) {
      source.setData(EMPTY_ICON_FEATURES);
      return;
    }
    if (!this.map.getLayer(PERCELEN_FILL_LAYER)) {
      return;
    }
    const rendered = this.map.queryRenderedFeatures(undefined, {
      layers: [PERCELEN_FILL_LAYER],
    }) as MapGeoJSONFeature[];
    const gewasCodes = this.selectedGewassen().map((g) => g.gewascode);
    source.setData(buildParcelIconFeatureCollection(rendered, gewasCodes));
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

  private applyActiveFillPaint(): void {
    if (!this.map || !this.parcelLayersAdded) {
      return;
    }
    setParcelFill(this.map, this.activeFillExpression());
  }

  private onParcelHoverMove(event: MapLayerMouseEvent): void {
    if (!this.map || !this.hoverGewasPopup) {
      return;
    }
    if (this.map.getZoom() < HOVER_GEWAS_MIN_ZOOM) {
      this.clearHoverGewasPopup();
      return;
    }
    const feature = event.features?.[0];
    const gewas = feature?.properties?.['gewas'];
    if (typeof gewas !== 'string' || gewas.length === 0) {
      this.clearHoverGewasPopup();
      return;
    }
    const lngLat = event.lngLat;
    this.hoverGewasPopup.setHTML(gewasHoverPopupHtml(gewas));
    if (!this.hoverGewasPopup.isOpen()) {
      this.hoverGewasPopup.setLngLat(lngLat).addTo(this.map);
    } else {
      this.hoverGewasPopup.setLngLat(lngLat);
    }
  }

  private clearHoverGewasPopup(): void {
    if (this.hoverGewasPopup?.isOpen()) {
      this.hoverGewasPopup.remove();
    }
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

    const stub = parcelFromTileProperties(parcelId, tileProperties);
    this.selectedParcel.set(stub);

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
    if (this.map) {
      setParcelFeatureSelected(this.map, id, true);
    }
  }

  private clearSelection(): void {
    if (this.map && this.selectedFeatureId !== null) {
      setParcelFeatureSelected(this.map, this.selectedFeatureId, false);
    }
    this.selectedFeatureId = null;
  }

  private loadHealth(): void {
    this.api.getHealth().subscribe({
      next: (response) => this.apiStatus.set(response.status),
      error: () => this.apiStatus.set('error'),
    });
  }

  private updateUrlFromMap(): void {
    if (!this.map) {
      return;
    }

    const center = this.map.getCenter();
    const zoom = this.map.getZoom();
    const query = buildMapQueryString({
      lng: center.lng,
      lat: center.lat,
      zoom,
      colorMode: this.colorMode(),
      viewportColors: this.viewportColors(),
      gewasCodes: this.selectedGewassen().map((g) => g.gewascode),
    });
    this.location.replaceState('/', query);
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

  private async refreshViewportGewassen(): Promise<void> {
    if (!this.map || !this.parcelLayersAdded) {
      return;
    }

    const wholeCountry = isWholeCountryView(this.map.getBounds());
    this.viewportShowsWholeCountry.set(wholeCountry);
    if (wholeCountry) {
      this.viewportGewassen.set([]);
      this.viewportGewassenLoading.set(false);
      this.refreshLegendForColorMode();
      this.applyActiveFillPaint();
      return;
    }

    const requestId = ++this.viewportRequestId;
    const bbox = bboxParam(this.map.getBounds());
    const gewasCodes = this.selectedGewassen().map((g) => g.gewascode);

    this.viewportGewassenLoading.set(true);
    try {
      const rows = await fetchOr(
        this.api.getGewassen({
          limit:
            this.viewportColors() && this.viewportColorsToggleEnabled()
              ? VIEWPORT_GEWASSEN_DYNAMIC_TOP_N
              : VIEWPORT_GEWASSEN_TOP_N,
          bbox,
          gewasCodes: gewasCodes.length > 0 ? gewasCodes : undefined,
        }),
        [],
      );
      if (requestId !== this.viewportRequestId) {
        return;
      }
      this.viewportGewassen.set(rows);
      this.refreshLegendForColorMode();
      this.applyActiveFillPaint();
    } finally {
      if (requestId === this.viewportRequestId) {
        this.viewportGewassenLoading.set(false);
      }
    }
  }
}
