import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { roleGuard } from './core/guards/role.guard';

export const routes: Routes = [
  { path: '', redirectTo: '/login', pathMatch: 'full' },
  {
    path: 'login',
    loadComponent: () => import('./modules/auth/login/login.component').then(m => m.LoginComponent)
  },
  {
    path: 'forgot-password',
    loadComponent: () => import('./modules/auth/forgot-password/forgot-password.component').then(m => m.ForgotPasswordComponent)
  },
  {
    path: 'reset-password',
    loadComponent: () => import('./modules/auth/reset-password/reset-password.component').then(m => m.ResetPasswordComponent)
  },
  {
    path: 'unauthorized',
    loadComponent: () => import('./shared/components/unauthorized/unauthorized.component').then(m => m.UnauthorizedComponent)
  },
  {
    path: 'admin',
    canActivate: [authGuard, roleGuard(['admin'])],
    loadChildren: () => import('./modules/admin/admin.routes').then(m => m.ADMIN_ROUTES)
  },
  {
    path: 'teacher',
    canActivate: [authGuard, roleGuard(['admin', 'teacher'])],
    loadChildren: () => import('./modules/teacher/teacher.routes').then(m => m.TEACHER_ROUTES)
  },
  {
    path: 'student',
    canActivate: [authGuard, roleGuard(['student'])],
    loadChildren: () => import('./modules/student/student.routes').then(m => m.STUDENT_ROUTES)
  },
  {
    path: 'parent',
    canActivate: [authGuard, roleGuard(['parent'])],
    loadChildren: () => import('./modules/parent-portal/parent-portal.routes').then(m => m.PARENT_ROUTES)
  },
  {
    path: 'superadmin',
    loadChildren: () => import('./modules/superadmin/superadmin.routes').then(m => m.SUPERADMIN_ROUTES)
  },
  { path: '**', redirectTo: '/login' }
];
