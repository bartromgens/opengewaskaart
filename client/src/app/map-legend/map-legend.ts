import { Component, computed, input, output, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

import { cropIconPath } from '../crop-icons';
import { formatHa, type ColorMode, type LegendEntry } from '../crop-colors';
import { injectSmallScreen } from '../shared/small-screen';

export interface ViewportLegendRow {
  gewas: string;
  gewascode: number;
  color: string;
  areaM2: number | null;
}

@Component({
  selector: 'app-map-legend',
  imports: [MatButtonModule, MatIconModule, MatProgressSpinnerModule, MatSlideToggleModule],
  templateUrl: './map-legend.html',
  styleUrl: './map-legend.scss',
})
export class MapLegendComponent {
  readonly cropIconPath = cropIconPath;

  entries = input.required<LegendEntry[]>();
  viewportRows = input<ViewportLegendRow[]>([]);
  viewportLoading = input(false);
  showViewportPanel = input(false);
  colorMode = input.required<ColorMode>();
  hasSelection = input(false);
  usesViewportColors = input(false);
  viewportColors = input(false);
  viewportColorsToggleEnabled = input(false);

  viewportColorsChange = output<boolean>();

  readonly smallScreen = injectSmallScreen();
  readonly legendOpen = signal(false);

  readonly isCompactGebruik = computed(() => this.smallScreen() && this.colorMode() === 'gebruik');

  readonly showViewportLegend = computed(
    () =>
      !this.smallScreen() &&
      this.colorMode() === 'gewas' &&
      (this.showViewportPanel() || this.viewportLoading()),
  );

  readonly hasLegendContent = computed(() => {
    if (this.colorMode() === 'gebruik' && this.entries().length > 0) {
      return true;
    }
    return this.showViewportLegend() || this.entries().length > 1 || this.hasSelection();
  });

  readonly showLegendStack = computed(
    () => !this.smallScreen() || this.legendOpen() || this.isCompactGebruik(),
  );

  readonly viewportTotalAreaM2 = computed(() =>
    this.viewportRows().reduce((sum, row) => sum + (row.areaM2 ?? 0), 0),
  );

  readonly legendTitle = computed(() => {
    if (this.colorMode() === 'gebruik') {
      return 'Gebruik (oppervlakte)';
    }
    if (this.hasSelection()) {
      return 'Geselecteerde gewassen';
    }
    if (this.usesViewportColors()) {
      return 'Top gewassen in dit gebied';
    }
    return 'Top gewassen (percelentelling)';
  });

  closeLegendSheet(): void {
    this.legendOpen.set(false);
  }

  openLegendSheet(): void {
    this.legendOpen.set(true);
  }

  viewportAreaSharePercent(row: ViewportLegendRow): string | null {
    const total = this.viewportTotalAreaM2();
    if (total <= 0 || row.areaM2 == null) {
      return null;
    }
    return `${((100 * row.areaM2) / total).toFixed(1)}%`;
  }

  viewportAreaHa(row: ViewportLegendRow): string {
    return formatHa(row.areaM2);
  }

  onViewportColorsChange(enabled: boolean): void {
    this.viewportColorsChange.emit(enabled);
  }
}
