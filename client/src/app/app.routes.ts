import { Routes } from '@angular/router';

import { adminGuard } from './admin.guard';
import { HomeComponent } from './home/home';

export const routes: Routes = [
  { path: '', component: HomeComponent },
  {
    path: 'gewassen',
    loadComponent: () => import('./gewassen/gewassen').then((m) => m.GewassenComponent),
  },
  {
    path: 'logs',
    loadComponent: () => import('./logs/logs').then((m) => m.LogsComponent),
    canActivate: [adminGuard],
  },
];
