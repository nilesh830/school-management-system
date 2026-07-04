import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MessageService, ConfirmationService } from 'primeng/api';
import { AutoCompleteModule } from 'primeng/autocomplete';
import { CalendarModule } from 'primeng/calendar';
import { SelectButtonModule } from 'primeng/selectbutton';
import { ButtonModule } from 'primeng/button';
import { ToastModule } from 'primeng/toast';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { MessageModule } from 'primeng/message';
import { CardModule } from 'primeng/card';
import { ToolbarModule } from 'primeng/toolbar';
import { TableModule } from 'primeng/table';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { DividerModule } from 'primeng/divider';

import {
  AttendanceService,
  AttendanceStatus,
  AttendanceRangePayload,
} from '../../../../core/services/attendance.service';
import { StudentService, Student } from '../../../../core/services/student.service';

interface DayRow {
  date: Date;
  key: string;            // 'YYYY-MM-DD'
  weekday: string;        // 'Mon' etc.
  status: AttendanceStatus;
  existing: boolean;      // a row already existed for this day (edit vs create)
  locked: boolean;        // cannot be marked (future / outside allowed window)
  lockReason: string;     // shown in the row when locked
}

@Component({
  selector: 'app-attendance-student-bulk',
  standalone: true,
  imports: [
    CommonModule, FormsModule,
    AutoCompleteModule, CalendarModule, SelectButtonModule,
    ButtonModule, ToastModule, ConfirmDialogModule,
    MessageModule, CardModule, ToolbarModule, TableModule,
    ProgressSpinnerModule, DividerModule
  ],
  providers: [MessageService, ConfirmationService],
  templateUrl: './attendance-student-bulk.component.html'
})
export class AttendanceStudentBulkComponent {
  private attendanceService = inject(AttendanceService);
  private studentService = inject(StudentService);
  private toast = inject(MessageService);
  private confirm = inject(ConfirmationService);

  // Student selection
  studentSuggestions: Student[] = [];
  selectedStudent: Student | null = null;

  // Week selection — user picks any date; we snap to that date's Mon–Sun week.
  // The picker stays disabled until a student is chosen, then the selectable
  // window is max(admission date, 2 months ago) → today. So a recent joiner is
  // capped at their joining date; an older student is capped at the last 2 months.
  weekAnchor: Date = new Date();
  maxDate: Date = new Date();
  minDate: Date = new Date();
  windowNote = '';
  weekLabel = '';

  // Editable rows
  dayRows: DayRow[] = [];
  loading = false;
  submitting = false;

  statusOptions = [
    { label: 'Present', value: 'present' },
    { label: 'Absent', value: 'absent' },
    { label: 'Late', value: 'late' },
    { label: 'Leave', value: 'leave' },
    { label: 'Holiday', value: 'holiday' }
  ];

  // ── Student autocomplete ────────────────────────────────────────────────────

  searchStudents(event: { query: string }): void {
    const q = event.query.trim();
    if (!q) {
      this.studentSuggestions = [];
      return;
    }
    this.studentService.searchStudents(q, 20).subscribe({
      next: (res) => { this.studentSuggestions = res.data.students ?? []; },
      error: () => { this.studentSuggestions = []; }
    });
  }

  onStudentSelect(event: { value: Student }): void {
    this.selectedStudent = event.value;
    this.computeDateBounds();
    this.weekAnchor = new Date(this.maxDate); // start on the current week
    this.loadWeek();
  }

  onStudentClear(): void {
    this.selectedStudent = null;
    this.dayRows = [];
    this.windowNote = '';
  }

  /**
   * Selectable window for the chosen student:
   *   lower bound = later of (admission date, today − 2 months)
   *   upper bound = today
   */
  private computeDateBounds(): void {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    this.maxDate = today;

    const twoMonthsAgo = new Date(today.getFullYear(), today.getMonth() - 2, today.getDate());
    twoMonthsAgo.setHours(0, 0, 0, 0);

    let lower = twoMonthsAgo;
    let cappedByAdmission = false;
    const admission = this.parseDate(this.selectedStudent?.admission_date);
    if (admission && admission > lower) {
      lower = admission;
      cappedByAdmission = true;
    }
    this.minDate = lower;

    this.windowNote = cappedByAdmission
      ? `Markable from admission date (${this.formatDisplay(lower)}) to ${this.formatDisplay(today)}.`
      : `Markable for the last 2 months (${this.formatDisplay(lower)} to ${this.formatDisplay(today)}).`;
  }

  // ── Week handling ────────────────────────────────────────────────────────────

  onWeekChange(): void {
    if (this.selectedStudent) this.loadWeek();
  }

  /** Build the 7 Mon–Sun rows for the week containing weekAnchor, then fetch existing rows. */
  loadWeek(): void {
    if (!this.selectedStudent || !this.weekAnchor) return;

    const monday = this.mondayOf(this.weekAnchor);
    const names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

    const rows: DayRow[] = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + i);
      d.setHours(0, 0, 0, 0);

      let locked = false;
      let lockReason = '';
      if (d > this.maxDate) {
        locked = true;
        lockReason = 'Future date';
      } else if (d < this.minDate) {
        locked = true;
        lockReason = 'Outside allowed window';
      }

      rows.push({
        date: d,
        key: this.toDateKey(d),
        weekday: names[i],
        status: 'present',
        existing: false,
        locked,
        lockReason
      });
    }
    this.dayRows = rows;
    this.weekLabel = `${this.formatDisplay(rows[0].date)} — ${this.formatDisplay(rows[6].date)}`;

    // Preload existing statuses across the week span
    this.loading = true;
    this.attendanceService
      .getStudentRange(this.selectedStudent.id, rows[0].key, rows[6].key)
      .subscribe({
        next: (res) => {
          const map = new Map<string, AttendanceStatus>();
          (res.data.attendance ?? []).forEach(r => map.set(r.date, r.status));
          this.dayRows = this.dayRows.map(row => {
            const found = map.get(row.key);
            return found ? { ...row, status: found, existing: true } : row;
          });
          this.loading = false;
        },
        error: () => {
          this.loading = false;
          this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load existing attendance' });
        }
      });
  }

  markAllPresent(): void {
    this.dayRows = this.dayRows.map(r => r.locked ? r : { ...r, status: 'present' });
  }

  get markableRows(): DayRow[] {
    return this.dayRows.filter(r => !r.locked);
  }

  // ── Submit ───────────────────────────────────────────────────────────────────

  confirmSubmit(): void {
    if (!this.selectedStudent) return;
    const count = this.markableRows.length;
    if (!count) {
      this.toast.add({ severity: 'warn', summary: 'Nothing to save', detail: 'No markable days in this week.' });
      return;
    }

    this.confirm.confirm({
      message: `Save attendance for ${this.selectedStudent.first_name} ${this.selectedStudent.last_name} across ${count} day(s) (${this.weekLabel})?`,
      header: 'Confirm Bulk Attendance',
      icon: 'pi pi-check-circle',
      acceptLabel: 'Yes, Save',
      rejectLabel: 'Cancel',
      acceptButtonStyleClass: 'p-button-success',
      accept: () => this.submit()
    });
  }

  private submit(): void {
    if (!this.selectedStudent) return;
    this.submitting = true;

    const payload: AttendanceRangePayload = {
      student_id: this.selectedStudent.id,
      entries: this.markableRows.map(r => ({ date: r.key, status: r.status }))
    };

    this.attendanceService.markStudentRange(payload).subscribe({
      next: (res) => {
        this.submitting = false;
        const d = res.data;
        this.toast.add({
          severity: 'success',
          summary: 'Attendance Saved',
          detail: `${d.records_created} created, ${d.records_updated} updated.`
        });
        this.loadWeek(); // refresh so rows now show as existing
      },
      error: (err) => {
        this.submitting = false;
        const msg = err?.error?.message ?? 'Failed to save attendance';
        this.toast.add({ severity: 'error', summary: 'Error', detail: msg });
      }
    });
  }

  // ── Helpers ────────────────────────────────────────────────────────────────

  getStatusSeverity(status: string): string {
    switch (status) {
      case 'present': return 'success';
      case 'absent': return 'danger';
      case 'late': return 'warning';
      case 'leave': return 'info';
      default: return 'secondary';
    }
  }

  /** Monday of the week containing the given date (Mon-based). */
  private mondayOf(date: Date): Date {
    const d = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const offset = (d.getDay() + 6) % 7; // 0=Sun..6=Sat → Mon-based offset
    d.setDate(d.getDate() - offset);
    d.setHours(0, 0, 0, 0);
    return d;
  }

  /** Parse a 'YYYY-MM-DD' string to a local midnight Date, or null. */
  private parseDate(s: string | undefined | null): Date | null {
    if (!s) return null;
    const parts = s.split('-').map(Number);
    if (parts.length < 3 || parts.some(isNaN)) return null;
    const d = new Date(parts[0], parts[1] - 1, parts[2]);
    d.setHours(0, 0, 0, 0);
    return d;
  }

  private toDateKey(date: Date): string {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }

  private formatDisplay(date: Date): string {
    return date.toLocaleDateString('en-US', { day: 'numeric', month: 'short' });
  }
}
