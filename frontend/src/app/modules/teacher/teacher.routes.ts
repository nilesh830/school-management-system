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
      // Students — teacher-specific READ-ONLY roster (no enroll/edit/transfer)
      {
        path: 'students',
        loadComponent: () => import('./students/teacher-students.component')
          .then(m => m.TeacherStudentsComponent)
      },
      // Grades / Exams — teacher-specific list (no create/edit/finalize);
      // marks-entry & class-results are shared, role-aware leaf pages.
      {
        path: 'grades',
        loadComponent: () => import('./grades/teacher-grades.component')
          .then(m => m.TeacherGradesComponent)
      },
      {
        path: 'grades/:examId/marks',
        loadComponent: () => import('../admin/exams/marks-entry/marks-entry.component')
          .then(m => m.MarksEntryComponent)
      },
      {
        path: 'grades/:examId/results',
        loadComponent: () => import('../admin/exams/class-results/class-results.component')
          .then(m => m.ClassResultsComponent)
      },
      // Leave Requests — teacher-specific review list
      {
        path: 'leave-requests',
        loadComponent: () => import('./leave-requests/teacher-leave-requests.component')
          .then(m => m.TeacherLeaveRequestsComponent)
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
