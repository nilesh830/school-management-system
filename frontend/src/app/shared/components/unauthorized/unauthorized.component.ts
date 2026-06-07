import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-unauthorized',
  standalone: true,
  imports: [CommonModule, RouterLink, ButtonModule],
  template: `
    <div class="flex flex-column align-items-center justify-content-center min-h-screen gap-4 text-center p-4">
      <div class="w-5rem h-5rem border-circle bg-red-100 flex align-items-center justify-content-center">
        <i class="pi pi-lock text-4xl text-red-500"></i>
      </div>
      <div>
        <h1 class="text-4xl font-bold text-900 m-0 mb-2">Access Denied</h1>
        <p class="text-600 m-0">You don't have permission to view this page.</p>
      </div>
      <div class="flex gap-3">
        <p-button label="Go Back" icon="pi pi-arrow-left" severity="secondary" [outlined]="true" (onClick)="goBack()" />
        <p-button label="Go to Dashboard" icon="pi pi-home" (onClick)="dashboard()" />
      </div>
    </div>
  `
})
export class UnauthorizedComponent {
  private auth = inject(AuthService);

  goBack(): void { window.history.back(); }
  dashboard(): void { this.auth.redirectToDashboard(); }
}
