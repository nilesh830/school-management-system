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
      // ── Students ───────────────────────────────────────────────────────────
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
      // ── Teachers (SMS-014 / SMS-015 / SMS-016 / SMS-017 / SMS-018) ─────────
      {
        path: 'teachers',
        loadComponent: () => import('./teachers/teacher-list/teacher-list.component').then(m => m.TeacherListComponent)
      },
      {
        path: 'teachers/new',
        loadComponent: () => import('./teachers/teacher-form/teacher-form.component').then(m => m.TeacherFormComponent)
      },
      {
        path: 'teachers/:id/edit',
        loadComponent: () => import('./teachers/teacher-form/teacher-form.component').then(m => m.TeacherFormComponent)
      },
      {
        path: 'teachers/:id',
        loadComponent: () => import('./teachers/teacher-detail/teacher-detail.component').then(m => m.TeacherDetailComponent)
      },
      // ── Classes & Sections (SMS-019 / SMS-020 / SMS-021) ───────────────────
      {
        path: 'classes',
        loadComponent: () => import('./classes/classes-list/classes-list.component').then(m => m.ClassesListComponent)
      },
      {
        path: 'classes/:id',
        loadComponent: () => import('./classes/class-detail/class-detail.component').then(m => m.ClassDetailComponent)
      },
      // ── Subjects (SMS-019) ─────────────────────────────────────────────────
      {
        path: 'subjects',
        loadComponent: () => import('./classes/subjects-list/subjects-list.component').then(m => m.SubjectsListComponent)
      },
      // ── Timetable (SMS-022) ────────────────────────────────────────────────
      {
        path: 'timetable',
        loadComponent: () => import('./timetable/timetable-view/timetable-view.component').then(m => m.TimetableViewComponent)
      },
      // ── Attendance (SMS-024 / SMS-025) ────────────────────────────────────────
      {
        path: 'attendance',
        redirectTo: 'attendance/mark',
        pathMatch: 'full'
      },
      {
        path: 'attendance/mark',
        loadComponent: () => import('./attendance/attendance-mark/attendance-mark.component')
          .then(m => m.AttendanceMarkComponent)
      },
      {
        path: 'attendance/view',
        loadComponent: () => import('./attendance/attendance-calendar/attendance-calendar.component')
          .then(m => m.AttendanceCalendarComponent)
      },
      {
        path: 'attendance/report',
        loadComponent: () => import('./attendance/attendance-report/attendance-report.component')
          .then(m => m.AttendanceReportComponent)
      },
      // ── Profile ────────────────────────────────────────────────────────────
      {
        path: 'profile',
        loadComponent: () => import('../../shared/components/profile/profile.component').then(m => m.ProfileComponent)
      }
    ]
  }
];
