import { Routes } from '@angular/router';
import { TeacherLayoutComponent } from './teacher-layout/teacher-layout.component';

export const TEACHER_ROUTES: Routes = [
  {
    path: '',
    component: TeacherLayoutComponent,
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      {
        path: 'dashboard',
        loadComponent: () => import('./dashboard/dashboard.component').then(m => m.TeacherDashboardComponent)
      },
      {
        path: 'profile',
        loadComponent: () => import('../../shared/components/profile/profile.component').then(m => m.ProfileComponent)
      },
      // Attendance — reuse admin components (backend enforces role-based access)
      { path: 'attendance', redirectTo: 'attendance/mark', pathMatch: 'full' },
      {
        path: 'attendance/mark',
        loadComponent: () => import('../admin/attendance/attendance-mark/attendance-mark.component')
          .then(m => m.AttendanceMarkComponent)
      },
      {
        path: 'attendance/view',
        loadComponent: () => import('../admin/attendance/attendance-calendar/attendance-calendar.component')
          .then(m => m.AttendanceCalendarComponent)
      },
      {
        path: 'attendance/report',
        loadComponent: () => import('../admin/attendance/attendance-report/attendance-report.component')
          .then(m => m.AttendanceReportComponent)
      },
      // Timetable
      {
        path: 'timetable',
        loadComponent: () => import('../admin/timetable/timetable-view/timetable-view.component')
          .then(m => m.TimetableViewComponent)
      }
    ]
  }
];
