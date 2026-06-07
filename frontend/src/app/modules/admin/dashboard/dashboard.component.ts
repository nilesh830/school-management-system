import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink, CardModule, ButtonModule],
  template: `
    <div>
      <div class="mb-4">
        <h2 class="text-2xl font-bold text-900 m-0">Welcome back, {{ firstName }}!</h2>
        <p class="text-600 mt-1 mb-0">Here's what's happening in your school today.</p>
      </div>

      <div class="grid">
        <div class="col-12 md:col-6 lg:col-3">
          <p-card styleClass="h-full">
            <div class="flex align-items-center gap-3">
              <div class="w-3rem h-3rem border-circle bg-blue-100 flex align-items-center justify-content-center">
                <i class="pi pi-users text-blue-600 text-xl"></i>
              </div>
              <div>
                <div class="text-500 text-sm">Total Students</div>
                <div class="text-2xl font-bold text-900">—</div>
              </div>
            </div>
          </p-card>
        </div>
        <div class="col-12 md:col-6 lg:col-3">
          <p-card styleClass="h-full">
            <div class="flex align-items-center gap-3">
              <div class="w-3rem h-3rem border-circle bg-green-100 flex align-items-center justify-content-center">
                <i class="pi pi-id-card text-green-600 text-xl"></i>
              </div>
              <div>
                <div class="text-500 text-sm">Total Teachers</div>
                <div class="text-2xl font-bold text-900">—</div>
              </div>
            </div>
          </p-card>
        </div>
        <div class="col-12 md:col-6 lg:col-3">
          <p-card styleClass="h-full">
            <div class="flex align-items-center gap-3">
              <div class="w-3rem h-3rem border-circle bg-orange-100 flex align-items-center justify-content-center">
                <i class="pi pi-building text-orange-600 text-xl"></i>
              </div>
              <div>
                <div class="text-500 text-sm">Classes</div>
                <div class="text-2xl font-bold text-900">—</div>
              </div>
            </div>
          </p-card>
        </div>
        <div class="col-12 md:col-6 lg:col-3">
          <p-card styleClass="h-full">
            <div class="flex align-items-center gap-3">
              <div class="w-3rem h-3rem border-circle bg-purple-100 flex align-items-center justify-content-center">
                <i class="pi pi-chart-bar text-purple-600 text-xl"></i>
              </div>
              <div>
                <div class="text-500 text-sm">Attendance Today</div>
                <div class="text-2xl font-bold text-900">—</div>
              </div>
            </div>
          </p-card>
        </div>
      </div>

      <div class="mt-4">
        <p-card header="Quick Actions">
          <div class="flex flex-wrap gap-3">
            <p-button label="Create User" icon="pi pi-user-plus" routerLink="/admin/users/new" />
            <p-button label="Add Student" icon="pi pi-graduation-cap" severity="secondary" routerLink="/admin/students/new" />
          </div>
        </p-card>
      </div>
    </div>
  `
})
export class AdminDashboardComponent {
  private auth = inject(AuthService);
  get firstName(): string { return this.auth.currentUser()?.first_name ?? 'Admin'; }
}
