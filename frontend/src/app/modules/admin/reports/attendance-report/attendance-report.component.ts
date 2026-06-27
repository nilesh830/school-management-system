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
import { ChartModule } from 'primeng/chart';
import { ProgressSpinnerModule } from 'primeng/progressspinner';

import {
  ReportService,
  AttendanceReport,
  AttendanceReportStudent,
  ExportFormat
} from '../../../../core/services/report.service';
import { ClassesService, Section } from '../../../../core/services/classes.service';

interface SectionOption {
  label: string;
  value: number;
}

@Component({
  selector: 'app-report-attendance',
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
    ChartModule,
    ProgressSpinnerModule
  ],
  providers: [MessageService],
  templateUrl: './attendance-report.component.html'
})
export class ReportAttendanceComponent implements OnInit {
  private reportService = inject(ReportService);
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

  students: AttendanceReportStudent[] = [];
  classAverage = 0;
  loading = false;
  hasRun = false;
  exporting: ExportFormat | null = null;

  chartData: any = null;
  chartOptions: any = {
    plugins: { legend: { display: false } },
    scales: { y: { beginAtZero: true, max: 100, ticks: { callback: (v: number) => v + '%' } } },
    responsive: true,
    maintainAspectRatio: false
  };

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
    this.loading = true;
    this.hasRun = false;

    this.reportService.getAttendanceReport(sectionId, this.formatDate(fromDate), this.formatDate(toDate)).subscribe({
      next: (res) => {
        this.loading = false;
        this.hasRun = true;
        this.applyReport(res.data);
      },
      error: () => {
        this.loading = false;
        this.hasRun = true;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to generate report' });
      }
    });
  }

  private applyReport(data: AttendanceReport): void {
    this.students = data.students ?? [];
    this.classAverage = data.class_average ?? 0;
    this.buildChart();
  }

  private buildChart(): void {
    if (!this.students.length) {
      this.chartData = null;
      return;
    }
    this.chartData = {
      labels: this.students.map(s => this.studentLabel(s)),
      datasets: [{
        label: 'Attendance %',
        data: this.students.map(s => s.percentage),
        backgroundColor: this.students.map(s => this.barColor(s.percentage))
      }]
    };
  }

  private barColor(pct: number): string {
    if (pct >= 75) return '#22c55e';
    if (pct >= 50) return '#f59e0b';
    return '#ef4444';
  }

  studentLabel(s: AttendanceReportStudent): string {
    return s.name ?? s.student_name ?? `#${s.student_id}`;
  }

  getPercentageClass(pct: number): string {
    if (pct >= 75) return 'text-green-600 font-bold';
    if (pct >= 50) return 'text-orange-500 font-bold';
    return 'text-red-600 font-bold';
  }

  export(format: ExportFormat): void {
    if (this.filterForm.invalid) {
      this.filterForm.markAllAsTouched();
      return;
    }
    const { sectionId, fromDate, toDate } = this.filterForm.value;
    const from = this.formatDate(fromDate);
    const to = this.formatDate(toDate);

    this.exporting = format;
    this.reportService.exportAttendanceReport(format, sectionId, from, to).subscribe({
      next: (blob) => {
        const ext = format === 'pdf' ? 'pdf' : 'xlsx';
        this.downloadBlob(blob, `attendance-report-${from}-to-${to}.${ext}`);
        this.exporting = null;
      },
      error: () => {
        this.exporting = null;
        this.toast.add({ severity: 'error', summary: 'Export failed', detail: 'Could not export the report' });
      }
    });
  }

  private downloadBlob(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
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
