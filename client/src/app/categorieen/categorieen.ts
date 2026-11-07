import { DecimalPipe } from '@angular/common';
import { Component, OnInit, ViewChild, inject, signal } from '@angular/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { HttpErrorResponse } from '@angular/common/http';

import { ApiService, CategorieSummary } from '../api.service';
import { BackToMapComponent } from '../shared/back-to-map';

@Component({
  selector: 'app-categorieen',
  imports: [
    BackToMapComponent,
    MatProgressSpinnerModule,
    MatTableModule,
    MatSortModule,
    DecimalPipe,
  ],
  templateUrl: './categorieen.html',
  styleUrl: './categorieen.scss',
})
export class CategorieenComponent implements OnInit {
  private api = inject(ApiService);

  readonly loading = signal(true);
  readonly error = signal<string | null>(null);

  readonly displayedColumns: string[] = ['category', 'parcel_count', 'area_m2'];

  readonly dataSource = new MatTableDataSource<CategorieSummary>([]);

  @ViewChild(MatSort)
  set sortHeader(s: MatSort | undefined) {
    if (s) {
      this.dataSource.sort = s;
    }
  }

  ngOnInit(): void {
    this.api.getCategorieen().subscribe({
      next: (rows) => {
        this.dataSource.data = rows;
        this.loading.set(false);
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

  areaHa(row: CategorieSummary): number | null {
    if (row.area_m2 == null) {
      return null;
    }
    return row.area_m2 / 10_000;
  }
}
