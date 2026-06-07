import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CardModule } from 'primeng/card';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-student-dashboard',
  standalone: true,
  imports: [CommonModule, CardModule],
  template: `
    <div>
      <div class="mb-4">
        <h2 class="text-2xl font-bold text-900 m-0">Welcome, {{ firstName }}!</h2>
        <p class="text-600 mt-1 mb-0">Your student dashboard.</p>
      </div>
      <p-card>
        <p class="text-600 m-0">Student features (grades, attendance, timetable) will be available in Sprint 2.</p>
      </p-card>
    </div>
  `
})
export class StudentDashboardComponent {
  private auth = inject(AuthService);
  get firstName(): string { return this.auth.currentUser()?.first_name ?? 'Student'; }
}
