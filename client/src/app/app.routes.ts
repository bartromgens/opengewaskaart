import { Routes } from '@angular/router';

import { adminGuard } from './admin.guard';
import { HomeComponent } from './home/home';

export const routes: Routes = [
  { path: '', component: HomeComponent },
  {
    path: 'gewassen',
    title: 'Gewassen',
    loadComponent: () => import('./gewassen/gewassen').then((m) => m.GewassenComponent),
  },
  {
    path: 'categorieen',
    title: 'Categorieën',
    loadComponent: () => import('./categorieen/categorieen').then((m) => m.CategorieenComponent),
  },
  {
    path: 'over',
    title: 'Over',
    loadComponent: () => import('./over/over').then((m) => m.OverComponent),
  },
  {
    path: 'logs',
    title: 'Logs',
    loadComponent: () => import('./logs/logs').then((m) => m.LogsComponent),
    canActivate: [adminGuard],
  },
];
