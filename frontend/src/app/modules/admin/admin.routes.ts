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
        path: 'users',
        loadComponent: () => import('./users/user-list/user-list.component').then(m => m.UserListComponent)
      },
      {
        path: 'users/new',
        loadComponent: () => import('./users/create-user/create-user.component').then(m => m.CreateUserComponent)
      },
      {
        path: 'users/:id/edit',
        loadComponent: () => import('./users/create-user/create-user.component').then(m => m.CreateUserComponent)
      },
      // ── Academic Years (SMS-023) ─────────────────────────────────────────────
      {
        path: 'academic-years',
        loadComponent: () => import('./academic-years/academic-year-list.component').then(m => m.AcademicYearListComponent)
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
      // ── Exams (SMS-029 / SMS-030) ─────────────────────────────────────────────
      {
        path: 'exams',
        loadComponent: () => import('./exams/exam-list/exam-list.component')
          .then(m => m.ExamListComponent)
      },
      {
        path: 'exams/:examId/marks',
        loadComponent: () => import('./exams/marks-entry/marks-entry.component')
          .then(m => m.MarksEntryComponent)
      },
      {
        path: 'exams/:examId/results',
        loadComponent: () => import('./exams/class-results/class-results.component')
          .then(m => m.ClassResultsComponent)
      },
      // ── Fees (SMS-035 / SMS-037) ──────────────────────────────────────────────
      {
        path: 'fees',
        loadComponent: () => import('./fees/fee-structure-list/fee-structure-list.component')
          .then(m => m.FeeStructureListComponent)
      },
      {
        path: 'fees/payment',
        loadComponent: () => import('./fees/fee-payment/fee-payment.component')
          .then(m => m.FeePaymentComponent)
      },
      {
        path: 'fees/ledger',
        loadComponent: () => import('./fees/fee-ledger/fee-ledger.component')
          .then(m => m.FeeLedgerComponent)
      },
      {
        path: 'fees/defaulters',
        loadComponent: () => import('./fees/defaulter-report/defaulter-report.component')
          .then(m => m.DefaulterReportComponent)
      },
      // ── Announcements (SMS-051 / SMS-052) ─────────────────────────────────────
      {
        path: 'announcements',
        loadComponent: () => import('./announcements/announcement-list/announcement-list.component')
          .then(m => m.AnnouncementListComponent)
      },
      // ── Library (SMS-053 / SMS-054 / SMS-055) ─────────────────────────────────
      {
        path: 'library',
        loadComponent: () => import('./library/book-catalog/book-catalog.component')
          .then(m => m.BookCatalogComponent)
      },
      {
        path: 'library/issues',
        loadComponent: () => import('./library/book-issues/book-issues.component')
          .then(m => m.BookIssuesComponent)
      },
      // ── Reports & Analytics (SMS-056 / SMS-057 / SMS-058 / SMS-059 / SMS-060) ─
      {
        path: 'reports',
        redirectTo: 'reports/attendance',
        pathMatch: 'full'
      },
      {
        path: 'reports/attendance',
        loadComponent: () => import('./reports/attendance-report/attendance-report.component')
          .then(m => m.ReportAttendanceComponent)
      },
      {
        path: 'reports/grades',
        loadComponent: () => import('./reports/grades-report/grades-report.component')
          .then(m => m.ReportGradesComponent)
      },
      {
        path: 'reports/fees',
        loadComponent: () => import('./reports/fees-report/fees-report.component')
          .then(m => m.ReportFeesComponent)
      },
      // ── Transport (SMS-061 / SMS-062) ─────────────────────────────────────────
      {
        path: 'transport',
        loadComponent: () => import('./transport/transport-management/transport-management.component')
          .then(m => m.TransportManagementComponent)
      },
      // ── Leave Requests (SMS-046/SMS-047) ──────────────────────────────────────
      {
        path: 'leave-requests',
        loadComponent: () => import('./leave-review/leave-review.component').then(m => m.LeaveReviewComponent)
      },
      // ── Profile ────────────────────────────────────────────────────────────
      {
        path: 'profile',
        loadComponent: () => import('../../shared/components/profile/profile.component').then(m => m.ProfileComponent)
      }
    ]
  }
];
