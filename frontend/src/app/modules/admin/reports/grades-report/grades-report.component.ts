import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MessageService } from 'primeng/api';
import { DropdownModule } from 'primeng/dropdown';
import { ButtonModule } from 'primeng/button';
import { ToastModule } from 'primeng/toast';
import { MessageModule } from 'primeng/message';
import { CardModule } from 'primeng/card';
import { ToolbarModule } from 'primeng/toolbar';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ChartModule } from 'primeng/chart';
import { ProgressSpinnerModule } from 'primeng/progressspinner';

import {
  ReportService,
  GradesReport,
  GradeStudentResult,
  ExportFormat
} from '../../../../core/services/report.service';
import { ExamService, Exam } from '../../../../core/services/exam.service';
import { ClassesService, Section } from '../../../../core/services/classes.service';

interface Option {
  label: string;
  value: number;
}

@Component({
  selector: 'app-report-grades',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    DropdownModule,
    ButtonModule,
    ToastModule,
    MessageModule,
    CardModule,
    ToolbarModule,
    TableModule,
    TagModule,
    ChartModule,
    ProgressSpinnerModule
  ],
  providers: [MessageService],
  templateUrl: './grades-report.component.html'
})
export class ReportGradesComponent implements OnInit {
  private reportService = inject(ReportService);
  private examService = inject(ExamService);
  private classesService = inject(ClassesService);
  private toast = inject(MessageService);
  private fb = inject(FormBuilder);

  filterForm: FormGroup = this.fb.group({
    examId: [null, Validators.required],
    sectionId: [null]
  });

  examOptions: Option[] = [];
  examsLoading = false;
  sectionOptions: Option[] = [];
  sectionsLoading = false;

  students: GradeStudentResult[] = [];
  gradeDistribution: Record<string, number> = {};
  loading = false;
  hasRun = false;
  exporting: ExportFormat | null = null;

  expandedRows: { [key: number]: boolean } = {};

  chartData: any = null;
  chartOptions: any = {
    plugins: { legend: { display: false } },
    scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
    responsive: true,
    maintainAspectRatio: false
  };

  private readonly gradeOrder = ['A+', 'A', 'B', 'C', 'D', 'E', 'F'];

  get totalStudents(): number {
    return this.students.length;
  }

  get passCount(): number {
    return this.students.filter(s => (s.overall_percentage ?? 0) >= 35).length;
  }

  get failCount(): number {
    return this.students.filter(s => (s.overall_percentage ?? 0) < 35).length;
  }

  get classAvgPercentage(): number {
    if (!this.students.length) return 0;
    return this.students.reduce((sum, s) => sum + (s.overall_percentage ?? 0), 0) / this.students.length;
  }

  ngOnInit(): void {
    this.loadExams();
    this.loadSections();
  }

  loadExams(): void {
    this.examsLoading = true;
    this.examService.getExams().subscribe({
      next: (res) => {
        this.examsLoading = false;
        const exams: Exam[] = res.data?.exams ?? [];
        this.examOptions = exams.map(e => ({
          label: e.term ? `${e.name} (${e.term})` : e.name,
          value: e.id
        }));
      },
      error: () => {
        this.examsLoading = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load exams' });
      }
    });
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
        // Non-fatal — section filter is optional
      }
    });
  }

  runReport(): void {
    if (this.filterForm.invalid) {
      this.filterForm.markAllAsTouched();
      return;
    }

    const { examId, sectionId } = this.filterForm.value;
    this.loading = true;
    this.hasRun = false;
    this.expandedRows = {};

    this.reportService.getGradesReport(examId, sectionId ?? undefined).subscribe({
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

  private applyReport(data: GradesReport): void {
    this.students = data.students ?? [];
    this.gradeDistribution = data.grade_distribution ?? {};
    this.buildChart();
  }

  private buildChart(): void {
    const counts: Record<string, number> = {};
    this.gradeOrder.forEach(g => (counts[g] = this.gradeDistribution[g] ?? 0));
    this.chartData = {
      labels: this.gradeOrder,
      datasets: [{
        label: 'Students',
        data: this.gradeOrder.map(g => counts[g]),
        backgroundColor: ['#22c55e', '#4ade80', '#60a5fa', '#facc15', '#fb923c', '#f87171', '#ef4444']
      }]
    };
  }

  getGradeSeverity(grade: string): 'success' | 'info' | 'warning' | 'danger' | undefined {
    if (['A+', 'A'].includes(grade)) return 'success';
    if (grade === 'B') return 'info';
    if (['C', 'D'].includes(grade)) return 'warning';
    return 'danger';
  }

  export(format: ExportFormat): void {
    if (this.filterForm.invalid) {
      this.filterForm.markAllAsTouched();
      return;
    }
    const { examId, sectionId } = this.filterForm.value;

    this.exporting = format;
    this.reportService.exportGradesReport(format, examId, sectionId ?? undefined).subscribe({
      next: (blob) => {
        const ext = format === 'pdf' ? 'pdf' : 'xlsx';
        this.downloadBlob(blob, `grades-report-exam-${examId}.${ext}`);
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
}
