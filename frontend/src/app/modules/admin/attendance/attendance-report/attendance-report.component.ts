import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MessageService } from 'primeng/api';
import { DropdownModule } from 'primeng/dropdown';
import { CalendarModule } from 'primeng/calendar';
import { ButtonModule } from 'primeng/button';
import { ToastModule } from 'primeng/toast';
import { MessageModule } from 'primeng/message';
import { CardModule } from 'primeng/card';
import { ToolbarModule } from 'primeng/toolbar';
import { TableModule } from 'primeng/table';
import { ProgressSpinnerModule } from 'primeng/progressspinner';

import { AttendanceService, AttendanceReportData, StudentSummary } from '../../../../core/services/attendance.service';
import { ClassesService, Section } from '../../../../core/services/classes.service';

interface SectionOption {
  label: string;
  value: number;
}

interface ReportRow extends StudentSummary {
  percentage: number;
}

@Component({
  selector: 'app-attendance-report',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    DropdownModule,
    CalendarModule,
    ButtonModule,
    ToastModule,
    MessageModule,
    CardModule,
    ToolbarModule,
    TableModule,
    ProgressSpinnerModule
  ],
  providers: [MessageService],
  templateUrl: './attendance-report.component.html'
})
export class AttendanceReportComponent implements OnInit {
  private attendanceService = inject(AttendanceService);
  private classesService = inject(ClassesService);
  private toast = inject(MessageService);
  private fb = inject(FormBuilder);

  filterForm: FormGroup = this.fb.group({
    sectionId: [null, Validators.required],
    fromDate: [null, Validators.required],
    toDate: [null, Validators.required]
  });

  sectionOptions: SectionOption[] = [];
  sectionsLoading = false;

  reportRows: ReportRow[] = [];
  reportData: AttendanceReportData | null = null;
  loading = false;
  hasRun = false;

  // Summary totals
  totalPresent = 0;
  totalAbsent = 0;
  averagePercentage = 0;

  ngOnInit(): void {
    this.loadSections();
  }

  loadSections(): void {
    this.sectionsLoading = true;
    this.classesService.getSections(undefined, 1, 200).subscribe({
      next: (res) => {
        this.sectionsLoading = false;
        const sections: Section[] = res.data.sections ?? [];
        this.sectionOptions = sections.map(s => ({
          label: `${s.class_name} – Section ${s.name}`,
          value: s.id
        }));
      },
      error: () => {
        this.sectionsLoading = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load sections' });
      }
    });
  }

  runReport(): void {
    if (this.filterForm.invalid) {
      this.filterForm.markAllAsTouched();
      return;
    }

    const { sectionId, fromDate, toDate } = this.filterForm.value;
    const from = this.formatDate(fromDate);
    const to = this.formatDate(toDate);

    this.loading = true;
    this.hasRun = false;

    this.attendanceService.getReport(sectionId, from, to).subscribe({
      next: (res) => {
        this.loading = false;
        this.hasRun = true;
        this.reportData = res.data;
        this.buildRows(res.data.student_summaries);
      },
      error: () => {
        this.loading = false;
        this.hasRun = true;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to generate report' });
      }
    });
  }

  private buildRows(summaries: StudentSummary[]): void {
    this.reportRows = summaries.map(s => {
      const denom = s.present + s.absent + s.late + s.leave;
      const pct = denom > 0 ? ((s.present + s.late) / denom) * 100 : 0;
      return { ...s, percentage: Math.round(pct * 10) / 10 };
    });

    this.totalPresent = this.reportRows.reduce((acc, r) => acc + r.present, 0);
    this.totalAbsent = this.reportRows.reduce((acc, r) => acc + r.absent, 0);

    if (this.reportRows.length > 0) {
      const sum = this.reportRows.reduce((acc, r) => acc + r.percentage, 0);
      this.averagePercentage = Math.round((sum / this.reportRows.length) * 10) / 10;
    } else {
      this.averagePercentage = 0;
    }
  }

  getPercentageClass(pct: number): string {
    if (pct >= 75) return 'text-green-600 font-bold';
    if (pct >= 50) return 'text-orange-500 font-bold';
    return 'text-red-600 font-bold';
  }

  exportCsv(): void {
    if (!this.reportRows.length) return;

    const header = 'Student ID,Present,Absent,Late,Leave,Holiday,Percentage';
    const rows = this.reportRows.map(r =>
      `${r.student_id},${r.present},${r.absent},${r.late},${r.leave},${r.holiday},${r.percentage}`
    );
    const csv = [header, ...rows].join('\n');

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `attendance-report-${this.formatDate(this.filterForm.value.fromDate)}-to-${this.formatDate(this.filterForm.value.toDate)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  private formatDate(date: Date): string {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }
}
