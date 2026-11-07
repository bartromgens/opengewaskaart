import { Component } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-back-to-map',
  imports: [MatButtonModule, MatIconModule, RouterLink],
  template: `
    <a mat-button routerLink="/" class="ogk-back-link">
      <mat-icon>arrow_back</mat-icon>
      Terug naar kaart
    </a>
  `,
  styles: `
    :host {
      display: block;
    }
  `,
})
export class BackToMapComponent {}
