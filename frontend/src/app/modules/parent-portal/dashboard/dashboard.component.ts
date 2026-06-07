import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CardModule } from 'primeng/card';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-parent-dashboard',
  standalone: true,
  imports: [CommonModule, CardModule],
  template: `
    <div>
      <div class="mb-4">
        <h2 class="text-xl font-bold text-900 m-0">Hello, {{ firstName }}!</h2>
        <p class="text-600 mt-1 mb-0 text-sm">Parent portal overview.</p>
      </div>
      <p-card>
        <p class="text-600 m-0 text-sm">
          Your children's attendance, grades, fees, and leave requests will appear here in Sprint 2.
        </p>
      </p-card>
    </div>
  `
})
export class ParentDashboardComponent {
  private auth = inject(AuthService);
  get firstName(): string { return this.auth.currentUser()?.first_name ?? 'Parent'; }
}
