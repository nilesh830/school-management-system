import { Routes } from '@angular/router';
import { StudentLayoutComponent } from './student-layout/student-layout.component';

export const STUDENT_ROUTES: Routes = [
  {
    path: '',
    component: StudentLayoutComponent,
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      {
        path: 'dashboard',
        loadComponent: () => import('./dashboard/dashboard.component').then(m => m.StudentDashboardComponent)
      },
      {
        path: 'profile',
        loadComponent: () => import('../../shared/components/profile/profile.component').then(m => m.ProfileComponent)
      },
      // Attendance — student views their own attendance calendar
      {
        path: 'attendance',
        loadComponent: () => import('../admin/attendance/attendance-calendar/attendance-calendar.component')
          .then(m => m.AttendanceCalendarComponent)
      }
    ]
  }
];
