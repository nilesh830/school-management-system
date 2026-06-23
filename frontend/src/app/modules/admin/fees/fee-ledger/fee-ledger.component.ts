import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap, takeUntil } from 'rxjs/operators';
import { MessageService } from 'primeng/api';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { TagModule } from 'primeng/tag';
import { ToolbarModule } from 'primeng/toolbar';
import { ToastModule } from 'primeng/toast';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { TooltipModule } from 'primeng/tooltip';

import { FeeStructureService, FeeRecord, FeePayment, FeeDiscount } from '../../../../core/services/fee-structure.service';
import { StudentService, Student } from '../../../../core/services/student.service';

@Component({
  selector: 'app-fee-ledger',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    TableModule,
    ButtonModule,
    InputTextModule,
    TagModule,
    ToolbarModule,
    ToastModule,
    ProgressSpinnerModule,
    TooltipModule,
  ],
  providers: [MessageService],
  templateUrl: './fee-ledger.component.html',
})
export class FeeLedgerComponent implements OnInit, OnDestroy {
  private feeService = inject(FeeStructureService);
  private studentService = inject(StudentService);
  private toast = inject(MessageService);
  private router = inject(Router);
  private destroy$ = new Subject<void>();

  // Student search
  searchQuery = '';
  searchResults: Student[] = [];
  selectedStudent: Student | null = null;
  searching = false;
  private searchSubject = new Subject<string>();

  // Fee records
  feeRecords: FeeRecord[] = [];
  loadingRecords = false;

  // Row expansion
  expandedRows: { [key: number]: boolean } = {};

  ngOnInit(): void {
    this.searchSubject
      .pipe(
        debounceTime(400),
        distinctUntilChanged(),
        switchMap((query) => {
          if (!query || query.length < 2) {
            this.searchResults = [];
            this.searching = false;
            return [];
          }
          this.searching = true;
          return this.studentService.searchStudents(query, 10);
        }),
        takeUntil(this.destroy$)
      )
      .subscribe({
        next: (res: any) => {
          this.searchResults = res?.data?.students ?? [];
          this.searching = false;
        },
        error: () => {
          this.searching = false;
          this.searchResults = [];
        },
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  onSearchInput(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.searchQuery = value;
    if (!value || value.length < 2) {
      this.searchResults = [];
      this.selectedStudent = null;
      this.feeRecords = [];
      this.expandedRows = {};
      return;
    }
    this.searchSubject.next(value);
  }

  selectStudent(student: Student): void {
    this.selectedStudent = student;
    this.searchQuery = `${student.first_name} ${student.last_name} (${student.admission_no})`;
    this.searchResults = [];
    this.expandedRows = {};
    this.loadFeeRecords(student.id);
  }

  loadFeeRecords(studentId: number): void {
    this.loadingRecords = true;
    this.feeRecords = [];
    this.feeService.getFeeRecords(studentId).subscribe({
      next: (res: any) => {
        this.feeRecords = res?.data?.fee_records ?? [];
        this.loadingRecords = false;
      },
      error: () => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load fee records' });
        this.loadingRecords = false;
      },
    });
  }

  getBalanceDue(record: FeeRecord): number {
    const paid = record.payments.reduce((sum: number, p: FeePayment) => sum + p.amount_paid, 0);
    return Math.max(0, record.net_amount - paid);
  }

  getTotalPaid(record: FeeRecord): number {
    return record.payments.reduce((sum: number, p: FeePayment) => sum + p.amount_paid, 0);
  }

  getTotalDiscount(record: FeeRecord): number {
    return (record.discounts ?? []).reduce((sum: number, d: FeeDiscount) => sum + d.amount, 0);
  }

  getDiscountTypeLabel(type: string): string {
    const map: Record<string, string> = {
      scholarship: 'Scholarship',
      sibling: 'Sibling',
      staff: 'Staff',
      custom: 'Custom',
    };
    return map[type] ?? type;
  }

  getStatusSeverity(status: string): 'warning' | 'info' | 'success' | 'secondary' | 'danger' {
    const map: Record<string, 'warning' | 'info' | 'success' | 'secondary' | 'danger'> = {
      pending: 'warning',
      partial: 'info',
      paid: 'success',
      waived: 'secondary',
    };
    return map[status] ?? 'danger';
  }

  getMethodLabel(method: string): string {
    const map: Record<string, string> = {
      cash: 'Cash',
      bank_transfer: 'Bank Transfer',
      cheque: 'Cheque',
      online: 'Online',
    };
    return map[method] ?? method;
  }

  isPayDisabled(record: FeeRecord): boolean {
    return record.status === 'paid' || record.status === 'waived';
  }

  navigateTo(path: string): void {
    this.router.navigate([path]);
  }

  navigateToPayment(studentId: number): void {
    this.router.navigate(['/admin/fees/payment'], { queryParams: { student_id: studentId } });
  }

  expandAll(): void {
    this.expandedRows = {};
    this.feeRecords.forEach((r) => {
      this.expandedRows[r.id] = true;
    });
  }

  collapseAll(): void {
    this.expandedRows = {};
  }

  collapseRow(id: number): void {
    const rest = { ...this.expandedRows };
    delete rest[id];
    this.expandedRows = rest;
  }

  downloadReceipt(paymentId: number): void {
    this.feeService.downloadReceipt(paymentId).subscribe({
      next: (blob: Blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `receipt-${paymentId}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
      },
      error: () => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to download receipt' });
      },
    });
  }
}
