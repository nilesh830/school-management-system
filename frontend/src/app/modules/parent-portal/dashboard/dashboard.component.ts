import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { CardModule } from 'primeng/card';
import { KnobModule } from 'primeng/knob';
import { BadgeModule } from 'primeng/badge';
import { ButtonModule } from 'primeng/button';
import { MessageModule } from 'primeng/message';
import { SkeletonModule } from 'primeng/skeleton';
import { TagModule } from 'primeng/tag';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../../core/services/auth.service';
import { ParentPortalService } from '../parent-portal.service';

@Component({
  selector: 'app-parent-dashboard',
  standalone: true,
  imports: [
    CommonModule, RouterLink, FormsModule,
    CardModule, KnobModule, BadgeModule, ButtonModule,
    MessageModule, SkeletonModule, TagModule
  ],
  template: `
    <div>
      <!-- Greeting -->
      <div class="mb-4">
        <h2 class="text-xl font-bold text-900 m-0">Hello, {{ firstName }}!</h2>
        <p class="text-600 mt-1 mb-0 text-sm">Here's an overview of your children.</p>
      </div>

      <!-- Loading skeletons -->
      @if (loading) {
        <div class="flex flex-column gap-3">
          @for (n of [1, 2]; track n) {
            <p-card>
              <p-skeleton width="60%" height="1.2rem" styleClass="mb-3" />
              <p-skeleton width="40%" height="0.9rem" styleClass="mb-4" />
              <div class="flex gap-3">
                <p-skeleton shape="circle" size="4rem" />
                <div class="flex flex-column gap-2 flex-1">
                  <p-skeleton width="80%" height="0.8rem" />
                  <p-skeleton width="60%" height="0.8rem" />
                  <p-skeleton width="70%" height="0.8rem" />
                </div>
              </div>
            </p-card>
          }
        </div>
      }

      <!-- No children linked -->
      @if (!loading && children.length === 0) {
        <p-message
          severity="info"
          text="No children linked. Contact your school admin."
          styleClass="w-full"
        />
      }

      <!-- Children cards -->
      @if (!loading && children.length > 0) {
        <div class="flex flex-column gap-3">
          @for (child of children; track child.student_id) {
            <p-card styleClass="shadow-1">
              <!-- Card header: name + class -->
              <ng-template pTemplate="header">
                <div class="flex align-items-center justify-content-between px-4 pt-3 pb-2" style="border-bottom: 1px solid #e2e8f0">
                  <div>
                    <div class="font-bold text-900 text-base">{{ child.full_name }}</div>
                    <div class="text-sm text-500 mt-1">{{ child.class_name }} — {{ child.section_name }}</div>
                  </div>
                  <i class="pi pi-user-circle text-3xl text-400"></i>
                </div>
              </ng-template>

              <!-- Stats row -->
              <div class="flex align-items-center gap-3">
                <!-- Attendance knob -->
                <div class="flex flex-column align-items-center gap-1" style="min-width: 80px">
                  <p-knob
                    [(ngModel)]="child.attendance_pct"
                    [readonly]="true"
                    [size]="72"
                    [min]="0"
                    [max]="100"
                    valueTemplate="{value}%"
                    [strokeWidth]="8"
                    [valueColor]="getAttendanceColor(child.attendance_pct)"
                    rangeColor="#e2e8f0"
                  />
                  <span class="text-xs text-500">Attendance</span>
                </div>

                <!-- Fee + grade info -->
                <div class="flex flex-column gap-2 flex-1">
                  <!-- Pending fees -->
                  <div class="flex align-items-center justify-content-between">
                    <span class="text-sm text-600">Pending Fees</span>
                    @if (child.pending_fees > 0) {
                      <span class="font-bold text-sm" style="color: #ef4444">
                        ₹{{ child.pending_fees | number:'1.0-0' }}
                      </span>
                    } @else {
                      <span class="font-bold text-sm" style="color: #22c55e">Nil</span>
                    }
                  </div>

                  <!-- Latest grade -->
                  @if (child.latest_exam) {
                    <div class="flex align-items-center justify-content-between">
                      <span class="text-sm text-600">{{ child.latest_exam }}</span>
                      <p-badge
                        [value]="child.latest_grade ?? 'N/A'"
                        [severity]="getGradeSeverity(child.latest_grade)"
                      />
                    </div>
                  }
                </div>
              </div>

              <!-- Footer actions -->
              <ng-template pTemplate="footer">
                <div class="flex gap-2 pt-1">
                  <p-button
                    label="Attendance"
                    icon="pi pi-calendar"
                    size="small"
                    [text]="true"
                    [routerLink]="['/parent/children', child.student_id, 'attendance']"
                  />
                  <p-button
                    label="Grades"
                    icon="pi pi-chart-bar"
                    size="small"
                    [text]="true"
                    [routerLink]="['/parent/children', child.student_id, 'grades']"
                  />
                  <p-button
                    label="Fees"
                    icon="pi pi-credit-card"
                    size="small"
                    [text]="true"
                    [routerLink]="['/parent/children', child.student_id, 'fees']"
                  />
                </div>
              </ng-template>
            </p-card>
          }
        </div>
      }
    </div>
  `
})
export class ParentDashboardComponent implements OnInit {
  private auth = inject(AuthService);
  private portalService = inject(ParentPortalService);

  children: any[] = [];
  loading = false;

  get firstName(): string {
    return this.auth.currentUser()?.first_name ?? 'Parent';
  }

  ngOnInit(): void {
    this.loadDashboard();
  }

  loadDashboard(): void {
    this.loading = true;
    this.portalService.getDashboard().subscribe({
      next: (res) => {
        this.children = res.data?.children ?? [];
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      }
    });
  }

  getAttendanceColor(pct: number): string {
    if (pct >= 85) return '#22c55e';   // green
    if (pct >= 70) return '#f59e0b';   // amber
    return '#ef4444';                   // red
  }

  getGradeSeverity(grade: string | null | undefined): 'success' | 'warning' | 'danger' | 'info' {
    if (!grade) return 'info';
    const g = grade.toUpperCase();
    if (g === 'A+' || g === 'A') return 'success';
    if (g === 'B' || g === 'B+') return 'info';
    if (g === 'C') return 'warning';
    return 'danger';
  }
}
