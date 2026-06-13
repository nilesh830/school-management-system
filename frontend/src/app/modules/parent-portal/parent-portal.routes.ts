import { Routes } from '@angular/router';
import { ParentLayoutComponent } from './parent-layout/parent-layout.component';

export const PARENT_ROUTES: Routes = [
  {
    path: '',
    component: ParentLayoutComponent,
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      {
        path: 'dashboard',
        loadComponent: () => import('./dashboard/dashboard.component').then(m => m.ParentDashboardComponent)
      },
      {
        path: 'profile',
        loadComponent: () => import('../../shared/components/profile/profile.component').then(m => m.ProfileComponent)
      },
      // Child sub-pages (Sprint 5+)
      {
        path: 'children/:id/attendance',
        loadComponent: () => import('./coming-soon.component').then(m => m.ComingSoonComponent)
      },
      {
        path: 'children/:id/grades',
        loadComponent: () => import('./coming-soon.component').then(m => m.ComingSoonComponent)
      },
      {
        path: 'children/:id/fees',
        loadComponent: () => import('./coming-soon.component').then(m => m.ComingSoonComponent)
      },
      {
        path: 'leave-applications',
        loadComponent: () => import('./coming-soon.component').then(m => m.ComingSoonComponent)
      },
      {
        path: 'messages',
        loadComponent: () => import('./coming-soon.component').then(m => m.ComingSoonComponent)
      },
      {
        path: 'notices',
        loadComponent: () => import('./coming-soon.component').then(m => m.ComingSoonComponent)
      }
    ]
  }
];
