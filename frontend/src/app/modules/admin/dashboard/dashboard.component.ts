import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { ChartModule } from 'primeng/chart';
import { MessageModule } from 'primeng/message';
import { TagModule } from 'primeng/tag';
import { TableModule } from 'primeng/table';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { AuthService } from '../../../core/services/auth.service';
import { DashboardService, AdminKpis } from '../../../core/services/dashboard.service';

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    CardModule,
    ButtonModule,
    ChartModule,
    MessageModule,
    TagModule,
    TableModule,
    ProgressSpinnerModule
  ],
  template: `
    <div>
      <div class="mb-4">
        <h2 class="text-2xl font-bold text-900 m-0">Welcome back, {{ firstName }}!</h2>
        <p class="text-600 mt-1 mb-0">Here's what's happening in your school today.</p>
      </div>

      @if (loading) {
        <div class="flex justify-content-center align-items-center py-8">
          <p-progressSpinner strokeWidth="4" styleClass="w-4rem h-4rem" />
        </div>
      }

      @if (!loading && loadFailed) {
        <p-message severity="error" text="Failed to load dashboard data. Please try again." styleClass="w-full" />
      }

      @if (!loading && kpis) {
        <!-- ── KPI cards ──────────────────────────────────────────────────── -->
        <div class="grid">
          <div class="col-12 md:col-6 lg:col-3">
            <p-card styleClass="h-full">
              <div class="flex align-items-center gap-3">
                <div class="w-3rem h-3rem border-circle bg-blue-100 flex align-items-center justify-content-center">
                  <i class="pi pi-users text-blue-600 text-xl"></i>
                </div>
                <div>
                  <div class="text-500 text-sm">Total Students</div>
                  <div class="text-2xl font-bold text-900">{{ kpis.total_students }}</div>
                  <div class="text-500 text-xs mt-1">{{ kpis.total_teachers }} teachers</div>
                </div>
              </div>
            </p-card>
          </div>

          <div class="col-12 md:col-6 lg:col-3">
            <p-card styleClass="h-full">
              <div class="flex align-items-center gap-3">
                <div class="w-3rem h-3rem border-circle bg-green-100 flex align-items-center justify-content-center">
                  <i class="pi pi-check-circle text-green-600 text-xl"></i>
                </div>
                <div>
                  <div class="text-500 text-sm">Today's Attendance</div>
                  <div class="text-2xl font-bold" [ngClass]="getAttendanceClass(kpis.attendance_today.percentage)">
                    {{ kpis.attendance_today.percentage | number:'1.0-1' }}%
                  </div>
                  <div class="text-500 text-xs mt-1">
                    Present: {{ kpis.attendance_today.present }} | Absent: {{ kpis.attendance_today.absent }}
                  </div>
                </div>
              </div>
            </p-card>
          </div>

          <div class="col-12 md:col-6 lg:col-3">
            <p-card styleClass="h-full">
              <div class="flex align-items-center gap-3">
                <div class="w-3rem h-3rem border-circle bg-teal-100 flex align-items-center justify-content-center">
                  <i class="pi pi-indian-rupee text-teal-600 text-xl"></i>
                </div>
                <div>
                  <div class="text-500 text-sm">Fees Collected (Month)</div>
                  <div class="text-2xl font-bold text-900">₹{{ kpis.fee_collection_this_month.collected | number:'1.0-0' }}</div>
                  <div class="text-500 text-xs mt-1">₹{{ kpis.fee_collection_this_month.pending | number:'1.0-0' }} pending</div>
                </div>
              </div>
            </p-card>
          </div>

          <div class="col-12 md:col-6 lg:col-3">
            <p-card styleClass="h-full">
              <div class="flex align-items-center gap-3">
                <div class="w-3rem h-3rem border-circle bg-orange-100 flex align-items-center justify-content-center">
                  <i class="pi pi-bell text-orange-600 text-xl"></i>
                </div>
                <div>
                  <div class="text-500 text-sm">Pending Actions</div>
                  <div class="text-2xl font-bold text-900">{{ pendingActions }}</div>
                  <div class="text-500 text-xs mt-1">
                    {{ kpis.pending_leave_applications }} leaves | {{ kpis.fee_defaulters_count }} defaulters
                  </div>
                </div>
              </div>
            </p-card>
          </div>
        </div>

        <!-- ── Charts row ─────────────────────────────────────────────────── -->
        <div class="grid mt-2">
          <div class="col-12 md:col-6">
            <p-card header="Fee Collection (This Month)">
              @if (feeChartData) {
                <p-chart
                  type="doughnut"
                  [data]="feeChartData"
                  [options]="doughnutOptions"
                  [style]="{ height: '280px' }"
                />
              } @else {
                <p-message severity="info" text="No fee data for this month." styleClass="w-full" />
              }
            </p-card>
          </div>

          <div class="col-12 md:col-6">
            <p-card header="Today's Attendance Breakdown">
              @if (attendanceChartData) {
                <p-chart
                  type="doughnut"
                  [data]="attendanceChartData"
                  [options]="doughnutOptions"
                  [style]="{ height: '280px' }"
                />
              } @else {
                <p-message severity="info" text="No attendance data for today." styleClass="w-full" />
              }
              <!--
                NOTE (attendance-trend gap): the backend GET /dashboard/admin endpoint does NOT
                return a 30-day attendance trend array, only today's present/absent/late snapshot.
                We render today's breakdown doughnut rather than fabricating trend data.
              -->
            </p-card>
          </div>
        </div>

        <!-- ── Alerts panel ───────────────────────────────────────────────── -->
        <div class="grid mt-2">
          <div class="col-12 lg:col-6">
            <p-card>
              <ng-template pTemplate="header">
                <div class="flex align-items-center justify-content-between px-3 pt-3">
                  <span class="text-lg font-semibold text-900">
                    <i class="pi pi-exclamation-triangle text-orange-500 mr-2"></i>Low Attendance (&lt; 75%)
                  </span>
                  <p-tag
                    [value]="kpis.low_attendance_students.length + ' student(s)'"
                    [severity]="kpis.low_attendance_students.length ? 'warning' : 'success'"
                  />
                </div>
              </ng-template>

              @if (kpis.low_attendance_students.length === 0) {
                <p class="text-600 m-0 px-1">No students below the 75% attendance threshold.</p>
              } @else {
                <p-table
                  [value]="kpis.low_attendance_students"
                  styleClass="p-datatable-sm"
                  responsiveLayout="scroll"
                >
                  <ng-template pTemplate="header">
                    <tr>
                      <th>Student</th>
                      <th class="text-center">Attendance %</th>
                    </tr>
                  </ng-template>
                  <ng-template pTemplate="body" let-s>
                    <tr>
                      <td>{{ s.name }}</td>
                      <td class="text-center">
                        <span class="text-red-600 font-bold">{{ s.percentage | number:'1.0-1' }}%</span>
                      </td>
                    </tr>
                  </ng-template>
                </p-table>
              }

              <div class="flex align-items-center gap-2 mt-3 p-3 border-round surface-100">
                <i class="pi pi-money-bill text-2xl text-red-500"></i>
                <div>
                  <div class="text-500 text-sm">Fee Defaulters</div>
                  <div class="text-xl font-bold text-red-500">{{ kpis.fee_defaulters_count }}</div>
                </div>
                <p-button
                  label="View"
                  icon="pi pi-arrow-right"
                  [text]="true"
                  size="small"
                  styleClass="ml-auto"
                  routerLink="/admin/fees/defaulters"
                />
              </div>
            </p-card>
          </div>

          <div class="col-12 lg:col-6">
            <p-card header="Recent Announcements">
              @if (kpis.recent_announcements.length === 0) {
                <p class="text-600 m-0">No recent announcements.</p>
              } @else {
                <ul class="list-none p-0 m-0">
                  @for (a of kpis.recent_announcements; track a.id) {
                    <li class="flex align-items-start gap-2 py-2 border-bottom-1 surface-border">
                      <i class="pi pi-megaphone text-primary mt-1"></i>
                      <div class="flex-1">
                        <div class="font-medium text-900">{{ a.title }}</div>
                        @if (a.published_at) {
                          <div class="text-500 text-xs">{{ a.published_at | date:'mediumDate' }}</div>
                        }
                      </div>
                    </li>
                  }
                </ul>
              }
            </p-card>
          </div>
        </div>
      }

      <!-- ── Quick actions ──────────────────────────────────────────────── -->
      <div class="mt-4">
        <p-card header="Quick Actions">
          <div class="flex flex-wrap gap-3">
            <p-button label="Create User" icon="pi pi-user-plus" routerLink="/admin/users/new" />
            <p-button label="Add Student" icon="pi pi-graduation-cap" severity="secondary" routerLink="/admin/students/new" />
            <p-button label="Reports" icon="pi pi-chart-bar" severity="secondary" [outlined]="true" routerLink="/admin/reports/attendance" />
          </div>
        </p-card>
      </div>
    </div>
  `
})
export class AdminDashboardComponent implements OnInit {
  private auth = inject(AuthService);
  private dashboardService = inject(DashboardService);

  get firstName(): string { return this.auth.currentUser()?.first_name ?? 'Admin'; }

  kpis: AdminKpis | null = null;
  loading = false;
  loadFailed = false;

  feeChartData: any = null;
  attendanceChartData: any = null;
  doughnutOptions: any = {
    plugins: { legend: { position: 'bottom' } },
    responsive: true,
    maintainAspectRatio: false
  };

  get pendingActions(): number {
    if (!this.kpis) return 0;
    return this.kpis.pending_leave_applications + this.kpis.fee_defaulters_count;
  }

  ngOnInit(): void {
    this.loadKpis();
  }

  private loadKpis(): void {
    this.loading = true;
    this.loadFailed = false;
    this.dashboardService.getAdminKpis().subscribe({
      next: (res) => {
        this.loading = false;
        this.kpis = res.data;
        this.buildCharts(res.data);
      },
      error: () => {
        this.loading = false;
        this.loadFailed = true;
      }
    });
  }

  private buildCharts(kpis: AdminKpis): void {
    const fee = kpis.fee_collection_this_month;
    if (fee && (fee.collected > 0 || fee.pending > 0)) {
      this.feeChartData = {
        labels: ['Collected', 'Pending'],
        datasets: [{
          data: [fee.collected, fee.pending],
          backgroundColor: ['#22c55e', '#f59e0b']
        }]
      };
    }

    const att = kpis.attendance_today;
    if (att && (att.present > 0 || att.absent > 0 || att.late > 0)) {
      this.attendanceChartData = {
        labels: ['Present', 'Absent', 'Late'],
        datasets: [{
          data: [att.present, att.absent, att.late],
          backgroundColor: ['#22c55e', '#ef4444', '#f59e0b']
        }]
      };
    }
  }

  getAttendanceClass(pct: number): string {
    if (pct >= 75) return 'text-green-600';
    if (pct >= 50) return 'text-orange-500';
    return 'text-red-600';
  }
}
