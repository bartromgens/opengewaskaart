import { Component, computed, input, output } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import {
  MatAutocompleteModule,
  MatAutocompleteSelectedEvent,
} from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { startWith } from 'rxjs/operators';

import type { GewasSummary } from '../api.service';

const MAX_OPTIONS = 50;

@Component({
  selector: 'app-gewas-filter',
  imports: [
    ReactiveFormsModule,
    MatAutocompleteModule,
    MatButtonModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
  ],
  templateUrl: './gewas-filter.html',
  styleUrl: './gewas-filter.scss',
})
export class GewasFilterComponent {
  gewassen = input.required<GewasSummary[]>();
  selected = input.required<GewasSummary[]>();
  colors = input.required<ReadonlyMap<number, string>>();
  selectedChange = output<GewasSummary[]>();

  queryCtrl = new FormControl('', { nonNullable: true });

  private query = toSignal(
    this.queryCtrl.valueChanges.pipe(startWith(this.queryCtrl.value), takeUntilDestroyed()),
    { initialValue: '' },
  );

  filteredOptions = computed(() => {
    const all = this.gewassen();
    const sel = this.selected();
    const q = (this.query() ?? '').trim().toLowerCase();
    const selectedCodes = new Set(sel.map((s) => s.gewascode));

    const match = (row: GewasSummary): boolean => {
      if (selectedCodes.has(row.gewascode)) {
        return false;
      }
      if (q.length === 0) {
        return true;
      }
      if (row.gewas.toLowerCase().includes(q)) {
        return true;
      }
      return String(row.gewascode).includes(q);
    };

    return all.filter(match).slice(0, MAX_OPTIONS);
  });

  onOptionSelected(event: MatAutocompleteSelectedEvent): void {
    const code = event.option.value as number;
    if (!Number.isFinite(code)) {
      return;
    }
    const row = this.gewassen().find((g) => g.gewascode === code);
    if (!row || this.selected().some((s) => s.gewascode === code)) {
      return;
    }
    this.selectedChange.emit([...this.selected(), row]);
    this.queryCtrl.setValue('');
  }

  removeGewas(gewascode: number): void {
    this.selectedChange.emit(this.selected().filter((s) => s.gewascode !== gewascode));
  }

  clearAll(): void {
    this.selectedChange.emit([]);
    this.queryCtrl.setValue('');
  }

  displayCode(_: number): string {
    return '';
  }
}
