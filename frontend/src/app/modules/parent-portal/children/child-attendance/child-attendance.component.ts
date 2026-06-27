import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { SkeletonModule } from 'primeng/skeleton';
import { MessageModule } from 'primeng/message';
import { TagModule } from 'primeng/tag';
import { ParentPortalService } from '../../parent-portal.service';

type AttendanceStatus = 'present' | 'absent' | 'late' | 'leave' | 'holiday';

interface CalendarDay {
  date: Date | null;
  dayNum: number | null;
  status: AttendanceStatus | null;
  isToday: boolean;
  isFuture: boolean;
  isCurrentMonth: boolean;
}

interface MonthlySummary {
  present: number;
  absent: number;
  late: number;
  leave: number;
  percentage: number;
}

@Component({
  selector: 'app-child-attendance',
  standalone: true,
  imports: [
    CommonModule,
    ButtonModule, CardModule, SkeletonModule, MessageModule, TagModule
  ],
  template: `
    <div>
      <!-- Page header -->
      <div class="flex align-items-center gap-2 mb-4">
        <i class="pi pi-calendar text-primary text-xl"></i>
        <h2 class="text-lg font-bold text-900 m-0">Attendance</h2>
        @if (childName) {
          <span class="text-500 text-sm">— {{ childName }}</span>
        }
      </div>

      <!-- Month navigation -->
      <div class="flex align-items-center justify-content-between mb-3">
        <p-button
          icon="pi pi-chevron-left"
          [rounded]="true"
          [text]="true"
          size="small"
          (onClick)="prevMonth()"
        />
        <span class="font-semibold text-900">{{ displayMonth }}</span>
        <p-button
          icon="pi pi-chevron-right"
          [rounded]="true"
          [text]="true"
          size="small"
          [disabled]="!canGoNext"
          (onClick)="nextMonth()"
        />
      </div>

      <!-- Loading skeleton -->
      @if (loading) {
        <p-card>
          <div class="grid" style="grid-template-columns: repeat(7, 1fr); gap: 4px">
            @for (n of skeletonCells; track n) {
              <p-skeleton height="2.5rem" borderRadius="6px" />
            }
          </div>
        </p-card>
      }

      <!-- Calendar grid -->
      @if (!loading) {
        <p-card styleClass="shadow-1">
          <!-- Day-of-week headers -->
          <div class="attendance-grid mb-2">
            @for (h of weekHeaders; track h) {
              <div class="day-header">{{ h }}</div>
            }
          </div>

          <!-- Week rows -->
          @if (calendarWeeks.length > 0) {
            @for (week of calendarWeeks; track $index) {
              <div class="attendance-grid mb-1">
                @for (day of week; track $index) {
                  <div [class]="getDayClass(day)" [title]="getDayTitle(day)">
                    @if (day.dayNum !== null) {
                      <span class="day-num">{{ day.dayNum }}</span>
                      @if (day.status) {
                        <span class="day-letter">{{ getStatusLetter(day.status) }}</span>
                      }
                    }
                  </div>
                }
              </div>
            }
          } @else {
            <p-message
              severity="info"
              text="No attendance data for this period."
              styleClass="w-full mt-2"
            />
          }
        </p-card>

        <!-- Legend -->
        <div class="flex flex-wrap gap-2 mt-3">
          @for (leg of legend; track leg.label) {
            <div class="flex align-items-center gap-1">
              <span class="legend-dot" [style.background]="leg.color"></span>
              <span class="text-xs text-600">{{ leg.label }}</span>
            </div>
          }
        </div>

        <!-- Summary strip -->
        @if (calendarWeeks.length > 0) {
          <p-card styleClass="shadow-1 mt-3">
            <div class="flex justify-content-around text-center">
              <div>
                <div class="font-bold text-lg" style="color: #22c55e">{{ summary.present }}</div>
                <div class="text-xs text-500">Present</div>
              </div>
              <div>
                <div class="font-bold text-lg" style="color: #ef4444">{{ summary.absent }}</div>
                <div class="text-xs text-500">Absent</div>
              </div>
              <div>
                <div class="font-bold text-lg" style="color: #f59e0b">{{ summary.late }}</div>
                <div class="text-xs text-500">Late</div>
              </div>
              <div>
                <div class="font-bold text-lg" style="color: #6366f1">{{ summary.leave }}</div>
                <div class="text-xs text-500">Leave</div>
              </div>
              <div>
                <div class="font-bold text-lg" [style.color]="getSummaryPctColor(summary.percentage)">
                  {{ summary.percentage }}%
                </div>
                <div class="text-xs text-500">Rate</div>
              </div>
            </div>
          </p-card>
        }
      }
    </div>

    <style>
      .attendance-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 3px;
      }
      .day-header {
        text-align: center;
        font-size: 0.65rem;
        font-weight: 600;
        color: #64748b;
        padding: 4px 0;
      }
      .day-cell {
        border-radius: 6px;
        min-height: 2.4rem;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        font-size: 0.7rem;
        cursor: default;
        padding: 2px;
      }
      .day-num { font-weight: 600; line-height: 1; }
      .day-letter { font-size: 0.55rem; line-height: 1; margin-top: 1px; font-weight: 500; }
      .day-empty { background: transparent; }
      .day-no-record { background: #f8fafc; color: #94a3b8; }
      .day-future { background: #f8fafc; color: #cbd5e1; }
      .day-present { background: #dcfce7; color: #166534; }
      .day-absent { background: #fee2e2; color: #991b1b; }
      .day-late { background: #fef3c7; color: #92400e; }
      .day-leave { background: #e0e7ff; color: #3730a3; }
      .day-holiday { background: #f3f4f6; color: #6b7280; }
      .day-today { outline: 2px solid #3b82f6; outline-offset: -2px; }
      .legend-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        display: inline-block;
      }
    </style>
  `
})
export class ChildAttendanceComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private portalService = inject(ParentPortalService);

  childId = 0;
  childName = '';
  loading = false;

  currentDate = new Date();
  displayMonth = '';
  weekHeaders = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  calendarWeeks: CalendarDay[][] = [];
  summary: MonthlySummary = { present: 0, absent: 0, late: 0, leave: 0, percentage: 0 };

  readonly skeletonCells = Array.from({ length: 35 }, (_, i) => i);
  readonly legend = [
    { label: 'Present', color: '#86efac' },
    { label: 'Absent', color: '#fca5a5' },
    { label: 'Late', color: '#fde68a' },
    { label: 'Leave', color: '#a5b4fc' },
    { label: 'Holiday', color: '#e5e7eb' },
  ];

  private attendanceMap = new Map<string, AttendanceStatus>();

  ngOnInit(): void {
    this.childId = Number(this.route.snapshot.paramMap.get('id'));
    this.updateDisplayMonth();
    this.loadAttendance();
  }

  prevMonth(): void {
    this.currentDate = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth() - 1, 1);
    this.updateDisplayMonth();
    this.loadAttendance();
  }

  nextMonth(): void {
    this.currentDate = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth() + 1, 1);
    this.updateDisplayMonth();
    this.loadAttendance();
  }

  get canGoNext(): boolean {
    const now = new Date();
    return this.currentDate.getFullYear() < now.getFullYear() ||
      (this.currentDate.getFullYear() === now.getFullYear() &&
       this.currentDate.getMonth() < now.getMonth());
  }

  loadAttendance(): void {
    this.loading = true;
    this.attendanceMap.clear();
    const month = this.currentDate.getMonth() + 1;
    const year = this.currentDate.getFullYear();

    this.portalService.getChildAttendance(this.childId, month, year).subscribe({
      next: (res) => {
        const records: any[] = res.data?.attendance ?? [];
        if (res.data?.student_name) this.childName = res.data.student_name;
        records.forEach((r: any) => {
          this.attendanceMap.set(r.date, r.status as AttendanceStatus);
        });
        this.buildCalendar();
        this.buildSummary();
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      }
    });
  }

  private updateDisplayMonth(): void {
    this.displayMonth = this.currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  }

  private buildCalendar(): void {
    const year = this.currentDate.getFullYear();
    const month = this.currentDate.getMonth();
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const firstDow = (firstDay.getDay() + 6) % 7;
    const daysInMonth = lastDay.getDate();

    const cells: CalendarDay[] = [];
    for (let i = 0; i < firstDow; i++) {
      cells.push({ date: null, dayNum: null, status: null, isToday: false, isFuture: false, isCurrentMonth: false });
    }
    for (let d = 1; d <= daysInMonth; d++) {
      const date = new Date(year, month, d);
      date.setHours(0, 0, 0, 0);
      const key = this.toDateKey(date);
      cells.push({
        date,
        dayNum: d,
        status: this.attendanceMap.get(key) ?? null,
        isToday: date.getTime() === today.getTime(),
        isFuture: date > today,
        isCurrentMonth: true
      });
    }
    const remainder = cells.length % 7;
    if (remainder !== 0) {
      for (let i = 0; i < 7 - remainder; i++) {
        cells.push({ date: null, dayNum: null, status: null, isToday: false, isFuture: false, isCurrentMonth: false });
      }
    }
    this.calendarWeeks = [];
    for (let i = 0; i < cells.length; i += 7) {
      this.calendarWeeks.push(cells.slice(i, i + 7));
    }
  }

  private buildSummary(): void {
    let present = 0, absent = 0, late = 0, leave = 0;
    this.attendanceMap.forEach(s => {
      if (s === 'present') present++;
      else if (s === 'absent') absent++;
      else if (s === 'late') late++;
      else if (s === 'leave') leave++;
    });
    const attended = present + late;
    const total = present + absent + late + leave;
    this.summary = { present, absent, late, leave, percentage: total > 0 ? Math.round((attended / total) * 100) : 0 };
  }

  private toDateKey(date: Date): string {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }

  getDayClass(day: CalendarDay): string {
    const base = 'day-cell';
    if (!day.isCurrentMonth || day.dayNum === null) return `${base} day-empty`;
    if (day.isFuture) return `${base} day-future`;
    const statusClass = day.status ? `day-${day.status}` : 'day-no-record';
    const todayClass = day.isToday ? ' day-today' : '';
    return `${base} ${statusClass}${todayClass}`;
  }

  getDayTitle(day: CalendarDay): string {
    if (!day.date || !day.isCurrentMonth) return '';
    const dateStr = day.date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    return day.status ? `${dateStr}: ${day.status}` : dateStr;
  }

  getStatusLetter(status: AttendanceStatus): string {
    return status.charAt(0).toUpperCase();
  }

  getSummaryPctColor(pct: number): string {
    if (pct >= 85) return '#22c55e';
    if (pct >= 70) return '#f59e0b';
    return '#ef4444';
  }
}
