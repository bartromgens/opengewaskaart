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
    path: 'categorieen',
    loadComponent: () => import('./categorieen/categorieen').then((m) => m.CategorieenComponent),
  },
  {
    path: 'over',
    loadComponent: () => import('./over/over').then((m) => m.OverComponent),
  },
  {
    path: 'logs',
    loadComponent: () => import('./logs/logs').then((m) => m.LogsComponent),
    canActivate: [adminGuard],
  },
];
