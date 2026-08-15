import { Component, input, output } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

import type { Gewasperceel } from '../api.service';

@Component({
  selector: 'app-perceel-detail-panel',
  imports: [MatIconModule],
  templateUrl: './perceel-detail-panel.html',
  styleUrl: './perceel-detail-panel.scss',
})
export class PerceelDetailPanelComponent {
  perceel = input<Gewasperceel | null>(null);
  loading = input(false);
  error = input<string | null>(null);
  closed = output<void>();
}
