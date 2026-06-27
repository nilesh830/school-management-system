import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap, takeUntil } from 'rxjs/operators';
import { MessageService } from 'primeng/api';
import { TableModule } from 'primeng/table';
import { DialogModule } from 'primeng/dialog';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { InputNumberModule } from 'primeng/inputnumber';
import { InputTextareaModule } from 'primeng/inputtextarea';
import { DropdownModule } from 'primeng/dropdown';
import { TagModule } from 'primeng/tag';
import { ToolbarModule } from 'primeng/toolbar';
import { ToastModule } from 'primeng/toast';
import { CalendarModule } from 'primeng/calendar';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { TooltipModule } from 'primeng/tooltip';

import { FeeStructureService, FeeRecord, FeePayment } from '../../../../core/services/fee-structure.service';
import { StudentService, Student } from '../../../../core/services/student.service';

@Component({
  selector: 'app-fee-payment',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    TableModule,
    DialogModule,
    ButtonModule,
    InputTextModule,
    InputNumberModule,
    InputTextareaModule,
    DropdownModule,
    TagModule,
    ToolbarModule,
    ToastModule,
    CalendarModule,
    ProgressSpinnerModule,
    TooltipModule,
  ],
  providers: [MessageService],
  templateUrl: './fee-payment.component.html',
})
export class FeePaymentComponent implements OnInit, OnDestroy {
  private feeService = inject(FeeStructureService);
  private studentService = inject(StudentService);
  private fb = inject(FormBuilder);
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

  // Payment dialog
  dialogVisible = false;
  saving = false;
  selectedRecord: FeeRecord | null = null;
  balanceDue = 0;

  paymentMethodOptions = [
    { label: 'Cash', value: 'cash' },
    { label: 'Bank Transfer', value: 'bank_transfer' },
    { label: 'Cheque', value: 'cheque' },
    { label: 'Online', value: 'online' },
  ];

  // Discount dialog
  discountDialogVisible = false;
  savingDiscount = false;
  discountRecord: FeeRecord | null = null;

  discountTypeOptions = [
    { label: 'Scholarship', value: 'scholarship' },
    { label: 'Sibling', value: 'sibling' },
    { label: 'Staff', value: 'staff' },
    { label: 'Custom', value: 'custom' },
  ];

  discountForm: FormGroup = this.fb.group({
    discount_type: ['scholarship', Validators.required],
    amount: [null, [Validators.required, Validators.min(0.01)]],
    reason: ['', Validators.maxLength(500)],
  });

  paymentForm: FormGroup = this.fb.group({
    amount_paid: [null, [Validators.required, Validators.min(0.01)]],
    payment_method: ['cash', Validators.required],
    payment_date: [new Date(), Validators.required],
    transaction_reference: [''],
    remarks: [''],
  });

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
      return;
    }
    this.searchSubject.next(value);
  }

  selectStudent(student: Student): void {
    this.selectedStudent = student;
    this.searchQuery = `${student.first_name} ${student.last_name} (${student.admission_no})`;
    this.searchResults = [];
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

  openPayDialog(record: FeeRecord): void {
    this.selectedRecord = record;
    this.balanceDue = this.getBalanceDue(record);
    this.paymentForm.reset({
      amount_paid: this.balanceDue,
      payment_method: 'cash',
      payment_date: new Date(),
      transaction_reference: '',
      remarks: '',
    });
    this.paymentForm.get('amount_paid')?.setValidators([
      Validators.required,
      Validators.min(0.01),
      Validators.max(this.balanceDue),
    ]);
    this.paymentForm.get('amount_paid')?.updateValueAndValidity();
    this.dialogVisible = true;
  }

  closeDialog(): void {
    this.dialogVisible = false;
    this.selectedRecord = null;
    this.paymentForm.reset();
  }

  submitPayment(): void {
    if (this.paymentForm.invalid || !this.selectedRecord) return;

    this.saving = true;
    const raw = this.paymentForm.value;
    const payload = {
      fee_record_id: this.selectedRecord.id,
      amount_paid: raw.amount_paid,
      payment_method: raw.payment_method,
      payment_date: this.formatDate(raw.payment_date),
      transaction_reference: raw.transaction_reference || null,
      remarks: raw.remarks || null,
    };

    this.feeService.recordPayment(payload).subscribe({
      next: (res: any) => {
        const receiptNo = res?.data?.receipt_no ?? '';
        this.toast.add({
          severity: 'success',
          summary: 'Payment Recorded',
          detail: `Receipt: ${receiptNo}`,
          life: 5000,
        });
        this.saving = false;
        this.dialogVisible = false;
        if (this.selectedStudent) {
          this.loadFeeRecords(this.selectedStudent.id);
        }
      },
      error: (err: any) => {
        const detail = err?.error?.message ?? 'Failed to record payment';
        this.toast.add({ severity: 'error', summary: 'Error', detail });
        this.saving = false;
      },
    });
  }

  getTotalDiscount(record: FeeRecord): number {
    return (record.discounts ?? []).reduce((sum, d) => sum + d.amount, 0);
  }

  openDiscountDialog(record: FeeRecord): void {
    this.discountRecord = record;
    this.discountForm.reset({ discount_type: 'scholarship', amount: null, reason: '' });
    this.discountDialogVisible = true;
  }

  closeDiscountDialog(): void {
    this.discountDialogVisible = false;
    this.discountRecord = null;
    this.discountForm.reset();
  }

  submitDiscount(): void {
    if (this.discountForm.invalid || !this.discountRecord) return;
    this.savingDiscount = true;
    const raw = this.discountForm.value;
    const payload: { discount_type: string; amount: number; reason?: string } = {
      discount_type: raw.discount_type,
      amount: raw.amount,
    };
    if (raw.reason && raw.reason.trim()) {
      payload.reason = raw.reason.trim();
    }
    this.feeService.applyDiscount(this.discountRecord.id, payload).subscribe({
      next: () => {
        this.toast.add({
          severity: 'success',
          summary: 'Discount Applied',
          detail: `₹${raw.amount.toFixed(2)} discount applied successfully.`,
          life: 4000,
        });
        this.savingDiscount = false;
        this.discountDialogVisible = false;
        if (this.selectedStudent) {
          this.loadFeeRecords(this.selectedStudent.id);
        }
      },
      error: (err: any) => {
        const detail = err?.error?.message ?? 'Failed to apply discount';
        this.toast.add({ severity: 'error', summary: 'Error', detail });
        this.savingDiscount = false;
      },
    });
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

  isPayDisabled(record: FeeRecord): boolean {
    return record.status === 'paid' || record.status === 'waived';
  }

  navigateTo(path: string): void {
    this.router.navigate([path]);
  }

  private formatDate(date: Date): string {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }
}
