import { Routes } from '@angular/router';
import { superAdminGuard } from '../../core/guards/superadmin.guard';
import { SuperadminLayoutComponent } from './superadmin-layout/superadmin-layout.component';

export const SUPERADMIN_ROUTES: Routes = [
  {
    path: 'login',
    loadComponent: () =>
      import('./login/sa-login.component').then(m => m.SaLoginComponent)
  },
  {
    path: '',
    component: SuperadminLayoutComponent,
    canActivate: [superAdminGuard],
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./dashboard/sa-dashboard.component').then(m => m.SaDashboardComponent)
      },
      {
        path: 'schools',
        loadComponent: () =>
          import('./schools/school-list/school-list.component').then(m => m.SchoolListComponent)
      },
      {
        path: 'schools/new',
        loadComponent: () =>
          import('./schools/school-new/school-new.component').then(m => m.SchoolNewComponent)
      },
      {
        path: 'schools/:id',
        loadComponent: () =>
          import('./schools/school-detail/school-detail.component').then(m => m.SchoolDetailComponent)
      }
    ]
  }
];
