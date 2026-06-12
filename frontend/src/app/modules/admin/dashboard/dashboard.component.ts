import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { ChartModule } from 'primeng/chart';
import { MessageModule } from 'primeng/message';
import { AuthService } from '../../../core/services/auth.service';
import { AttendanceService, TodaySummaryData } from '../../../core/services/attendance.service';

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink, CardModule, ButtonModule, ChartModule, MessageModule],
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

        <!-- Live Attendance Today card -->
        <div class="col-12 md:col-6 lg:col-3">
          <p-card styleClass="h-full">
            <div class="flex align-items-center gap-3">
              <div class="w-3rem h-3rem border-circle bg-purple-100 flex align-items-center justify-content-center">
                <i class="pi pi-chart-bar text-purple-600 text-xl"></i>
              </div>
              <div>
                <div class="text-500 text-sm">Attendance Today</div>
                @if (todaySummaryLoading) {
                  <div class="text-2xl font-bold text-900">...</div>
                } @else if (todaySummary) {
                  <div class="text-2xl font-bold text-900">{{ todaySummary.present }}</div>
                  <div class="text-500 text-xs mt-1">Present today</div>
                  <div class="text-500 text-xs">Absent: {{ todaySummary.absent }} | Late: {{ todaySummary.late }}</div>
                } @else {
                  <div class="text-2xl font-bold text-900">—</div>
                }
              </div>
            </div>
          </p-card>
        </div>
      </div>

      <!-- Attendance Doughnut Chart -->
      <div class="grid mt-2">
        <div class="col-12 md:col-6">
          <p-card header="Today's Attendance Breakdown">
            @if (todaySummaryLoading) {
              <div class="flex justify-content-center align-items-center py-4">
                <i class="pi pi-spin pi-spinner text-3xl text-500"></i>
              </div>
            } @else if (todaySummary && todaySummary.total > 0) {
              <p-chart
                type="doughnut"
                [data]="attendanceChartData"
                [options]="attendanceChartOptions"
                [style]="{'height': '280px'}"
              />
            } @else {
              <p-message severity="info" text="No attendance data for today." styleClass="w-full" />
            }
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
export class AdminDashboardComponent implements OnInit {
  private auth = inject(AuthService);
  private attendanceService = inject(AttendanceService);

  get firstName(): string { return this.auth.currentUser()?.first_name ?? 'Admin'; }

  todaySummary: TodaySummaryData | null = null;
  todaySummaryLoading = false;

  attendanceChartData: any = null;
  attendanceChartOptions: any = {
    plugins: {
      legend: {
        position: 'bottom'
      }
    },
    responsive: true,
    maintainAspectRatio: false
  };

  ngOnInit(): void {
    this.loadTodaySummary();
  }

  private loadTodaySummary(): void {
    this.todaySummaryLoading = true;
    this.attendanceService.getTodaySummary().subscribe({
      next: (res) => {
        this.todaySummaryLoading = false;
        this.todaySummary = res.data;
        if (res.data && res.data.total > 0) {
          this.buildChartData(res.data);
        }
      },
      error: () => {
        this.todaySummaryLoading = false;
        // Non-fatal — dashboard still renders without attendance data
      }
    });
  }

  private buildChartData(summary: TodaySummaryData): void {
    this.attendanceChartData = {
      labels: ['Present', 'Absent', 'Late', 'Leave/Holiday'],
      datasets: [{
        data: [
          summary.present,
          summary.absent,
          summary.late,
          summary.leave + summary.holiday
        ],
        backgroundColor: ['#22c55e', '#ef4444', '#f59e0b', '#94a3b8']
      }]
    };
  }
}
