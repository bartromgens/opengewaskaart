import { DecimalPipe } from '@angular/common';
import { Component, OnInit, ViewChild, inject, signal } from '@angular/core';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { HttpErrorResponse } from '@angular/common/http';

import { ApiService, GewasSummary } from '../api.service';
import { gebruikLabel } from '../crop-colors';
import { cropIconPath } from '../crop-icons';
import { BackToMapComponent } from '../shared/back-to-map';

@Component({
  selector: 'app-gewassen',
  imports: [
    BackToMapComponent,
    MatCheckboxModule,
    MatProgressSpinnerModule,
    MatTableModule,
    MatSortModule,
    DecimalPipe,
  ],
  templateUrl: './gewassen.html',
  styleUrl: './gewassen.scss',
})
export class GewassenComponent implements OnInit {
  readonly cropIconPath = cropIconPath;

  private api = inject(ApiService);

  private static readonly FILTER_UNCLASSIFIED = 'gewassen-unclassified';

  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  /** Show only gewassen without a GewasGebruik row (gebruik was defaulted). */
  readonly filterUnclassifiedOnly = signal(false);

  readonly displayedColumns: string[] = [
    'gewas',
    'gewascode',
    'geclassificeerd',
    'gebruik',
    'category',
    'parcel_count',
    'area_m2',
  ];

  readonly dataSource = new MatTableDataSource<GewasSummary>([]);

  /**
   * Table + MatSort render only after loading=false (@if in template), so
   * ngAfterViewInit runs too early. Connect sort when the view child appears.
   */
  @ViewChild(MatSort)
  set sortHeader(s: MatSort | undefined) {
    if (s) {
      this.dataSource.sort = s;
    }
  }

  ngOnInit(): void {
    this.dataSource.filterPredicate = (row, filter) => {
      if (filter === GewassenComponent.FILTER_UNCLASSIFIED) {
        return !row.gebruik_geclassificeerd;
      }
      return true;
    };

    this.api.getGewassen().subscribe({
      next: (rows) => {
        this.dataSource.data = rows;
        this.loading.set(false);
        queueMicrotask(() => this.applyClassificationFilter());
      },
      error: (err: unknown) => {
        const msg =
          err instanceof HttpErrorResponse && err.message
            ? err.message
            : 'Kon de gegevens niet laden.';
        this.error.set(msg);
        this.loading.set(false);
      },
    });
  }

  areaHa(row: GewasSummary): number | null {
    if (row.area_m2 == null) {
      return null;
    }
    return row.area_m2 / 10_000;
  }

  formatGebruik(row: GewasSummary): string {
    return gebruikLabel(row.gebruik);
  }

  onFilterUnclassifiedChange(checked: boolean): void {
    this.filterUnclassifiedOnly.set(checked);
    this.applyClassificationFilter();
  }

  private applyClassificationFilter(): void {
    this.dataSource.filter = this.filterUnclassifiedOnly()
      ? GewassenComponent.FILTER_UNCLASSIFIED
      : '';
  }
}
