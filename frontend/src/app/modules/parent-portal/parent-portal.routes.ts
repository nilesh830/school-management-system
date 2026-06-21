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
      // Child sub-pages (Sprint 7)
      {
        path: 'children/:id/attendance',
        loadComponent: () => import('./children/child-attendance/child-attendance.component').then(m => m.ChildAttendanceComponent)
      },
      {
        path: 'children/:id/grades',
        loadComponent: () => import('./children/child-grades/child-grades.component').then(m => m.ChildGradesComponent)
      },
      {
        path: 'children/:id/fees',
        loadComponent: () => import('./children/child-fees/child-fees.component').then(m => m.ChildFeesComponent)
      },
      // Sprint 8
      {
        path: 'leave-applications',
        loadComponent: () => import('./leave/leave-list.component').then(m => m.LeaveListComponent)
      },
      {
        path: 'messages',
        loadComponent: () => import('./messages/thread-list.component').then(m => m.ThreadListComponent)
      },
      {
        path: 'messages/:threadId',
        loadComponent: () => import('./messages/thread-detail.component').then(m => m.ThreadDetailComponent)
      },
      {
        path: 'profile',
        loadComponent: () => import('./profile/parent-profile.component').then(m => m.ParentProfileComponent)
      },
      {
        path: 'notices',
        loadComponent: () => import('./notices/notice-board.component').then(m => m.NoticeBoardComponent)
      }
    ]
  }
];
