import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup } from '@angular/forms';
import { MessageService } from 'primeng/api';
import { DropdownModule } from 'primeng/dropdown';
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
  FeesReport,
  FeeTypeBreakdown,
  FeeDefaulter,
  ExportFormat
} from '../../../../core/services/report.service';
import { ClassesService, ClassRecord, AcademicYear } from '../../../../core/services/classes.service';

interface Option {
  label: string;
  value: number;
}

@Component({
  selector: 'app-report-fees',
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
    ChartModule,
    ProgressSpinnerModule
  ],
  providers: [MessageService],
  templateUrl: './fees-report.component.html'
})
export class ReportFeesComponent implements OnInit {
  private reportService = inject(ReportService);
  private classesService = inject(ClassesService);
  private toast = inject(MessageService);
  private fb = inject(FormBuilder);

  filterForm: FormGroup = this.fb.group({
    classId: [null],
    academicYearId: [null]
  });

  classOptions: Option[] = [];
  classesLoading = false;
  yearOptions: Option[] = [];
  yearsLoading = false;

  byFeeType: FeeTypeBreakdown[] = [];
  defaulters: FeeDefaulter[] = [];
  totalCollected = 0;
  totalPending = 0;
  loading = false;
  hasRun = false;
  exporting: ExportFormat | null = null;

  chartData: any = null;
  doughnutOptions: any = {
    plugins: { legend: { position: 'bottom' } },
    responsive: true,
    maintainAspectRatio: false
  };

  get grandTotal(): number {
    return this.totalCollected + this.totalPending;
  }

  get collectionRate(): number {
    return this.grandTotal > 0 ? (this.totalCollected / this.grandTotal) * 100 : 0;
  }

  ngOnInit(): void {
    this.loadClasses();
    this.loadAcademicYears();
  }

  loadClasses(): void {
    this.classesLoading = true;
    this.classesService.getClasses(1, 200).subscribe({
      next: (res) => {
        this.classesLoading = false;
        const classes: ClassRecord[] = res.data.classes ?? [];
        this.classOptions = classes.map(c => ({ label: c.name, value: c.id }));
      },
      error: () => {
        this.classesLoading = false;
        // Non-fatal — class filter is optional
      }
    });
  }

  loadAcademicYears(): void {
    this.yearsLoading = true;
    this.classesService.getAcademicYears().subscribe({
      next: (res) => {
        this.yearsLoading = false;
        const years: AcademicYear[] = res.data.academic_years ?? [];
        this.yearOptions = years.map(y => ({ label: y.name, value: y.id }));
      },
      error: () => {
        this.yearsLoading = false;
        // Non-fatal — academic year filter is optional
      }
    });
  }

  runReport(): void {
    const { classId, academicYearId } = this.filterForm.value;
    this.loading = true;
    this.hasRun = false;

    this.reportService.getFeesReport(classId ?? undefined, academicYearId ?? undefined).subscribe({
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

  private applyReport(data: FeesReport): void {
    this.byFeeType = data.by_fee_type ?? [];
    this.defaulters = data.defaulters ?? [];
    this.totalCollected = data.totals?.collected ?? 0;
    this.totalPending = data.totals?.pending ?? 0;
    this.buildChart();
  }

  private buildChart(): void {
    if (this.totalCollected === 0 && this.totalPending === 0) {
      this.chartData = null;
      return;
    }
    this.chartData = {
      labels: ['Collected', 'Pending'],
      datasets: [{
        data: [this.totalCollected, this.totalPending],
        backgroundColor: ['#22c55e', '#f59e0b']
      }]
    };
  }

  export(format: ExportFormat): void {
    const { classId, academicYearId } = this.filterForm.value;

    this.exporting = format;
    this.reportService.exportFeesReport(format, classId ?? undefined, academicYearId ?? undefined).subscribe({
      next: (blob) => {
        const ext = format === 'pdf' ? 'pdf' : 'xlsx';
        const scope = classId ? `class-${classId}` : 'all-classes';
        this.downloadBlob(blob, `fees-report-${scope}.${ext}`);
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
