import { Routes } from '@angular/router';
import { AdminLayoutComponent } from './admin-layout/admin-layout.component';

export const ADMIN_ROUTES: Routes = [
  {
    path: '',
    component: AdminLayoutComponent,
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      {
        path: 'dashboard',
        loadComponent: () => import('./dashboard/dashboard.component').then(m => m.AdminDashboardComponent)
      },
      {
        path: 'users/new',
        loadComponent: () => import('./users/create-user/create-user.component').then(m => m.CreateUserComponent)
      },
      {
        path: 'students',
        loadComponent: () => import('./students/student-list/student-list.component').then(m => m.StudentListComponent)
      },
      {
        path: 'students/new',
        loadComponent: () => import('./students/student-new/student-new.component').then(m => m.StudentNewComponent)
      },
      {
        path: 'students/:id',
        loadComponent: () => import('./students/student-detail/student-detail.component').then(m => m.StudentDetailComponent)
      },
      {
        path: 'profile',
        loadComponent: () => import('../../shared/components/profile/profile.component').then(m => m.ProfileComponent)
      }
    ]
  }
];
