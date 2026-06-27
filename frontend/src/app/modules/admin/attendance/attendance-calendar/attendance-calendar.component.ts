import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MessageService } from 'primeng/api';
import { AutoCompleteModule } from 'primeng/autocomplete';
import { ButtonModule } from 'primeng/button';
import { ToastModule } from 'primeng/toast';
import { CardModule } from 'primeng/card';
import { ToolbarModule } from 'primeng/toolbar';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { TagModule } from 'primeng/tag';
import { DividerModule } from 'primeng/divider';

import { AttendanceService, AttendanceRecord, AttendanceStatus } from '../../../../core/services/attendance.service';
import { StudentService, Student } from '../../../../core/services/student.service';

interface CalendarDay {
  date: Date | null;       // null = padding cell (outside this month)
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
  holiday: number;
  percentage: number;
}

@Component({
  selector: 'app-attendance-calendar',
  standalone: true,
  imports: [
    CommonModule, FormsModule,
    AutoCompleteModule, ButtonModule, ToastModule,
    CardModule, ToolbarModule, ProgressSpinnerModule,
    TagModule, DividerModule
  ],
  providers: [MessageService],
  templateUrl: './attendance-calendar.component.html'
})
export class AttendanceCalendarComponent implements OnInit {
  private attendanceService = inject(AttendanceService);
  private studentService = inject(StudentService);
  private toast = inject(MessageService);

  // Student selection
  studentSuggestions: Student[] = [];
  selectedStudent: Student | null = null;

  // Month navigation
  currentDate: Date = new Date();
  displayMonth = '';
  weekHeaders = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  // Calendar data
  calendarWeeks: CalendarDay[][] = [];
  summary: MonthlySummary = { present: 0, absent: 0, late: 0, leave: 0, holiday: 0, percentage: 0 };
  loading = false;

  // Raw attendance map: 'YYYY-MM-DD' → status
  private attendanceMap = new Map<string, AttendanceStatus>();

  ngOnInit(): void {
    this.updateDisplayMonth();
  }

  // ── Student autocomplete ───────────────────────────────────────────────────

  searchStudents(event: { query: string }): void {
    const q = event.query.trim();
    if (!q) {
      this.studentSuggestions = [];
      return;
    }
    this.studentService.searchStudents(q, 20).subscribe({
      next: (res) => {
        this.studentSuggestions = res.data.students ?? [];
      },
      error: () => {
        this.studentSuggestions = [];
      }
    });
  }

  onStudentSelect(event: { value: Student }): void {
    this.selectedStudent = event.value;
    this.loadAttendance();
  }

  onStudentClear(): void {
    this.selectedStudent = null;
    this.attendanceMap.clear();
    this.calendarWeeks = [];
    this.resetSummary();
  }

  // ── Month navigation ───────────────────────────────────────────────────────

  prevMonth(): void {
    this.currentDate = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth() - 1, 1);
    this.updateDisplayMonth();
    if (this.selectedStudent) this.loadAttendance();
  }

  nextMonth(): void {
    const now = new Date();
    const next = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth() + 1, 1);
    if (next > now) return; // Don't navigate into the future
    this.currentDate = next;
    this.updateDisplayMonth();
    if (this.selectedStudent) this.loadAttendance();
  }

  get canGoNext(): boolean {
    const now = new Date();
    return this.currentDate.getFullYear() < now.getFullYear() ||
      (this.currentDate.getFullYear() === now.getFullYear() &&
       this.currentDate.getMonth() < now.getMonth());
  }

  private updateDisplayMonth(): void {
    this.displayMonth = this.currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  }

  // ── Data loading ───────────────────────────────────────────────────────────

  loadAttendance(): void {
    if (!this.selectedStudent) return;

    this.loading = true;
    this.attendanceMap.clear();

    const month = this.currentDate.getMonth() + 1;
    const year = this.currentDate.getFullYear();

    this.attendanceService.getAttendance(this.selectedStudent.id, month, year).subscribe({
      next: (res) => {
        const records: AttendanceRecord[] = res.data.attendance ?? [];
        records.forEach(r => {
          this.attendanceMap.set(r.date, r.status);
        });
        this.buildCalendar();
        this.buildSummary();
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load attendance data' });
      }
    });
  }

  // ── Calendar grid builder ──────────────────────────────────────────────────

  private buildCalendar(): void {
    const year = this.currentDate.getFullYear();
    const month = this.currentDate.getMonth();
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);

    // JS: 0=Sun..6=Sat  →  we want Mon=0..Sun=6
    const firstDow = (firstDay.getDay() + 6) % 7; // Mon-based offset
    const daysInMonth = lastDay.getDate();

    const cells: CalendarDay[] = [];

    // Leading empty cells
    for (let i = 0; i < firstDow; i++) {
      cells.push({ date: null, dayNum: null, status: null, isToday: false, isFuture: false, isCurrentMonth: false });
    }

    // Day cells
    for (let d = 1; d <= daysInMonth; d++) {
      const date = new Date(year, month, d);
      date.setHours(0, 0, 0, 0);
      const key = this.toDateKey(date);
      const status = this.attendanceMap.get(key) ?? null;
      cells.push({
        date,
        dayNum: d,
        status,
        isToday: date.getTime() === today.getTime(),
        isFuture: date > today,
        isCurrentMonth: true
      });
    }

    // Trailing empty cells to complete last row
    const remainder = cells.length % 7;
    if (remainder !== 0) {
      for (let i = 0; i < 7 - remainder; i++) {
        cells.push({ date: null, dayNum: null, status: null, isToday: false, isFuture: false, isCurrentMonth: false });
      }
    }

    // Chunk into weeks
    this.calendarWeeks = [];
    for (let i = 0; i < cells.length; i += 7) {
      this.calendarWeeks.push(cells.slice(i, i + 7));
    }
  }

  private buildSummary(): void {
    let present = 0, absent = 0, late = 0, leave = 0, holiday = 0;
    this.attendanceMap.forEach(status => {
      if (status === 'present') present++;
      else if (status === 'absent') absent++;
      else if (status === 'late') late++;
      else if (status === 'leave') leave++;
      else if (status === 'holiday') holiday++;
    });
    const attended = present + late; // late counts as attended
    const total = present + absent + late + leave;
    const percentage = total > 0 ? Math.round((attended / total) * 100) : 0;
    this.summary = { present, absent, late, leave, holiday, percentage };
  }

  private resetSummary(): void {
    this.summary = { present: 0, absent: 0, late: 0, leave: 0, holiday: 0, percentage: 0 };
  }

  private toDateKey(date: Date): string {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }

  // ── Template helpers ───────────────────────────────────────────────────────

  getStudentLabel(student: Student): string {
    return `${student.first_name} ${student.last_name} (${student.admission_no})`;
  }

  getStatusClass(day: CalendarDay): string {
    if (!day.isCurrentMonth || day.dayNum === null) return 'day-cell day-empty';
    if (day.isFuture) return 'day-cell day-future';
    if (!day.status) return 'day-cell day-no-record';
    return `day-cell day-${day.status}`;
  }

  getStatusLabel(status: AttendanceStatus | null): string {
    if (!status) return '';
    return status.charAt(0).toUpperCase();
  }
}
