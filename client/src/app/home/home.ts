import { Component, ElementRef, OnDestroy, OnInit, ViewChild, inject, signal } from '@angular/core';
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

@Component({
  selector: 'app-home',
  imports: [MatIconModule, PerceelDetailPanelComponent],
  templateUrl: './home.html',
  styleUrl: './home.scss',
})
export class HomeComponent implements OnInit, OnDestroy {
  @ViewChild('mapContainer', { static: true }) mapContainer!: ElementRef<HTMLDivElement>;

  private api = inject(ApiService);

  map: Map | null = null;
  apiStatus = signal<string | null>(null);
  selectedParcel = signal<Gewasperceel | null>(null);
  parcelLoading = signal(false);
  parcelError = signal<string | null>(null);

  private selectedFeatureId: number | null = null;
  private parcelLayersAdded = false;

  ngOnInit(): void {
    this.initMap();
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

  private initMap(): void {
    this.map = new Map({
      container: this.mapContainer.nativeElement,
      style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
      center: [5.3, 52.2],
      zoom: 7,
    });

    this.map.addControl(new NavigationControl(), 'top-right');
    this.map.on('load', () => this.addParcelLayers());
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

    this.map.addSource(PERCELEN_SOURCE, {
      type: 'vector',
      url: environment.tilesUrl,
    });

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
    this.loadParcelDetail(parcelId);
  }

  private loadParcelDetail(parcelId: number): void {
    this.parcelLoading.set(true);
    this.parcelError.set(null);
    this.selectedParcel.set(null);

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

  private loadHealth(): void {
    this.api.getHealth().subscribe({
      next: (response) => this.apiStatus.set(response.status),
      error: () => this.apiStatus.set('error'),
    });
  }
}
