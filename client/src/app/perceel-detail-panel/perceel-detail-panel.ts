import { Component, input, output } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

import type { Gewasperceel, GewasGebruikKey } from '../api.service';
import { gebruikLabel } from '../crop-colors';
import { cropIconPath } from '../crop-icons';

@Component({
  selector: 'app-perceel-detail-panel',
  imports: [MatIconModule],
  templateUrl: './perceel-detail-panel.html',
  styleUrl: './perceel-detail-panel.scss',
})
export class PerceelDetailPanelComponent {
  readonly cropIconPath = cropIconPath;

  perceel = input<Gewasperceel | null>(null);
  loading = input(false);
  error = input<string | null>(null);
  closed = output<void>();

  formatGebruik(gebruik: GewasGebruikKey): string {
    return gebruikLabel(gebruik);
  }
}
