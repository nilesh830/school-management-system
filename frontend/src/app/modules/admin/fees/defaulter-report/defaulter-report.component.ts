import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MessageService } from 'primeng/api';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { DropdownModule } from 'primeng/dropdown';
import { TagModule } from 'primeng/tag';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { ToolbarModule } from 'primeng/toolbar';
import { ToastModule } from 'primeng/toast';
import { TooltipModule } from 'primeng/tooltip';

import { FeeStructureService } from '../../../../core/services/fee-structure.service';

@Component({
  selector: 'app-defaulter-report',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    TableModule,
    ButtonModule,
    DropdownModule,
    TagModule,
    CardModule,
    InputTextModule,
    ToolbarModule,
    ToastModule,
    TooltipModule,
  ],
  providers: [MessageService],
  templateUrl: './defaulter-report.component.html',
})
export class DefaulterReportComponent implements OnInit {
  private feeStructureService = inject(FeeStructureService);
  private http = inject(HttpClient);
  private toast = inject(MessageService);

  defaulters = signal<any[]>([]);
  loading = signal(false);
  classes = signal<any[]>([]);

  selectedClassId: number | null = null;

  totalBalanceDue = computed(() =>
    this.defaulters().reduce((sum, row) => sum + (row.balance_due ?? 0), 0)
  );

  ngOnInit(): void {
    this.loadClasses();
    this.loadDefaulters();
  }

  loadClasses(): void {
    this.http.get<any>('/api/v1/classes').subscribe({
      next: (res) => {
        this.classes.set(res?.data?.classes ?? res?.data ?? []);
      },
      error: () => {
        // Non-fatal — filter simply won't populate
      },
    });
  }

  loadDefaulters(): void {
    this.loading.set(true);
    this.feeStructureService.getDefaulters(this.selectedClassId ?? undefined).subscribe({
      next: (res) => {
        this.defaulters.set(res?.data?.defaulters ?? []);
        this.loading.set(false);
      },
      error: () => {
        this.toast.add({
          severity: 'error',
          summary: 'Error',
          detail: 'Failed to load defaulter report',
        });
        this.loading.set(false);
      },
    });
  }

  getSeverity(daysOverdue: number): 'danger' | 'warning' | 'info' {
    if (daysOverdue > 30) return 'danger';
    if (daysOverdue > 7) return 'warning';
    return 'info';
  }

  exportCsv(): void {
    const rows = this.defaulters();
    if (rows.length === 0) {
      this.toast.add({
        severity: 'warn',
        summary: 'No Data',
        detail: 'No defaulters to export',
      });
      return;
    }

    const headers = [
      'Student Name',
      'Roll Number',
      'Fee Type',
      'Due Date',
      'Net Amount',
      'Total Paid',
      'Balance Due',
      'Days Overdue',
    ];

    const csvLines = [
      headers.join(','),
      ...rows.map((row) =>
        [
          this.escapeCsvField(row.student_name),
          this.escapeCsvField(row.roll_number),
          this.escapeCsvField(row.fee_type),
          this.escapeCsvField(row.due_date),
          row.net_amount ?? 0,
          row.total_paid ?? 0,
          row.balance_due ?? 0,
          row.days_overdue ?? 0,
        ].join(',')
      ),
    ];

    const csvContent = csvLines.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `fee-defaulters-${new Date().toISOString().slice(0, 10)}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  private escapeCsvField(value: any): string {
    if (value === null || value === undefined) return '';
    const str = String(value);
    if (str.includes(',') || str.includes('"') || str.includes('\n')) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  }
}
