import { Location } from '@angular/common';
import { Component, ElementRef, OnDestroy, OnInit, ViewChild, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { Map, NavigationControl, type MapLayerMouseEvent } from 'maplibre-gl';

import { ApiService, type Gewasperceel } from '../api.service';
import { buildCategoryFillColorExpression } from '../crop-colors';
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

interface TileJson {
  minzoom?: number;
  maxzoom?: number;
  tiles?: string[];
  bounds?: [number, number, number, number];
}

@Component({
  selector: 'app-home',
  imports: [MatIconModule, PerceelDetailPanelComponent],
  templateUrl: './home.html',
  styleUrl: './home.scss',
})
export class HomeComponent implements OnInit, OnDestroy {
  @ViewChild('mapContainer', { static: true }) mapContainer!: ElementRef<HTMLDivElement>;

  private api = inject(ApiService);
  private location = inject(Location);
  private route = inject(ActivatedRoute);

  map: Map | null = null;
  apiStatus = signal<string | null>(null);
  selectedParcel = signal<Gewasperceel | null>(null);
  parcelLoading = signal(false);
  parcelError = signal<string | null>(null);

  private selectedFeatureId: number | null = null;
  private parcelLayersAdded = false;
  private tileMinZoom = DEFAULT_TILE_MIN_ZOOM;
  private tileMaxZoom = DEFAULT_TILE_MAX_ZOOM;
  private tileJsonTiles: string[] | null = null;
  private tileJsonBounds: [number, number, number, number] | undefined;

  ngOnInit(): void {
    void this.initMap();
    this.loadHealth();
  }

  ngOnDestroy(): void {
    this.map?.remove();
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

    this.map = new Map({
      container: this.mapContainer.nativeElement,
      style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
      center,
      zoom: Math.max(this.tileMinZoom, Math.min(this.tileMaxZoom, zoom)),
      minZoom: this.tileMinZoom,
    });

    this.map.addControl(new NavigationControl(), 'top-right');
    this.map.on('load', () => this.addParcelLayers());
    this.map.on('moveend', () => this.updateUrlFromMap());
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
      const features = this.map?.queryRenderedFeatures(event.point, {
        layers: [PERCELEN_FILL_LAYER],
      });
      if (!features?.length) {
        this.closeDetailPanel();
      }
    });
  }

  private addParcelLayers(): void {
    if (!this.map || this.parcelLayersAdded) {
      return;
    }

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

    this.map.addLayer({
      id: PERCELEN_FILL_LAYER,
      type: 'fill',
      source: PERCELEN_SOURCE,
      'source-layer': PERCELEN_LAYER,
      paint: {
        'fill-color': buildCategoryFillColorExpression(),
        'fill-opacity': [
          'case',
          ['boolean', ['feature-state', 'selected'], false],
          0.85,
          0.65,
        ],
        'fill-outline-color': [
          'case',
          ['boolean', ['feature-state', 'selected'], false],
          '#1565c0',
          '#666666',
        ],
      },
    });

    this.map.addLayer({
      id: PERCELEN_OUTLINE_LAYER,
      type: 'line',
      source: PERCELEN_SOURCE,
      'source-layer': PERCELEN_LAYER,
      paint: {
        'line-color': [
          'case',
          ['boolean', ['feature-state', 'selected'], false],
          '#1565c0',
          '#555555',
        ],
        'line-width': [
          'case',
          ['boolean', ['feature-state', 'selected'], false],
          2.5,
          0.5,
        ],
      },
    });

    this.parcelLayersAdded = true;
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

  private loadParcelDetail(
    parcelId: number,
    tileProperties?: Record<string, unknown>,
  ): void {
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

  private getInitialMapState(): { center: [number, number]; zoom: number } {
    const params = this.route.snapshot.queryParamMap;
    const lat = params.get('lat');
    const lng = params.get('lng');
    const zoom = params.get('zoom');

    const lngValue =
      lng != null && !Number.isNaN(Number(lng)) ? Number(lng) : DEFAULT_CENTER[0];
    const latValue =
      lat != null && !Number.isNaN(Number(lat)) ? Number(lat) : DEFAULT_CENTER[1];
    const zoomValue =
      zoom != null && !Number.isNaN(Number(zoom)) ? Number(zoom) : DEFAULT_MAP_ZOOM;

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

  private buildQueryString(lng: number, lat: number, zoom: number): string {
    const params = new URLSearchParams();
    params.set('lat', lat.toFixed(5));
    params.set('lng', lng.toFixed(5));
    params.set('zoom', String(zoom));
    return params.toString();
  }
}
