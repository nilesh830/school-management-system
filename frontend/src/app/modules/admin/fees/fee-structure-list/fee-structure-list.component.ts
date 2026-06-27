import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { MessageService } from 'primeng/api';
import { TableModule } from 'primeng/table';
import { DialogModule } from 'primeng/dialog';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { InputNumberModule } from 'primeng/inputnumber';
import { DropdownModule } from 'primeng/dropdown';
import { CheckboxModule } from 'primeng/checkbox';
import { TagModule } from 'primeng/tag';
import { ToolbarModule } from 'primeng/toolbar';
import { ToastModule } from 'primeng/toast';
import { CalendarModule } from 'primeng/calendar';
import { ProgressSpinnerModule } from 'primeng/progressspinner';

import { FeeStructureService, FeeStructure } from '../../../../core/services/fee-structure.service';

@Component({
  selector: 'app-fee-structure-list',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    TableModule,
    DialogModule,
    ButtonModule,
    InputTextModule,
    InputNumberModule,
    DropdownModule,
    CheckboxModule,
    TagModule,
    ToolbarModule,
    ToastModule,
    CalendarModule,
    ProgressSpinnerModule,
  ],
  providers: [MessageService],
  templateUrl: './fee-structure-list.component.html',
})
export class FeeStructureListComponent implements OnInit {
  private feeStructureService = inject(FeeStructureService);
  private fb = inject(FormBuilder);
  private toast = inject(MessageService);
  private router = inject(Router);

  feeStructures: FeeStructure[] = [];
  loading = false;
  dialogVisible = false;
  saving = false;
  isEdit = false;
  editingId: number | null = null;

  frequencyOptions = [
    { label: 'Monthly', value: 'monthly' },
    { label: 'Quarterly', value: 'quarterly' },
    { label: 'Annual', value: 'annual' },
    { label: 'One Time', value: 'one_time' },
  ];

  form: FormGroup = this.fb.group({
    fee_type: ['', Validators.required],
    class_id: [null, Validators.required],
    academic_year_id: [null, Validators.required],
    amount: [null, [Validators.required, Validators.min(0)]],
    due_date: [null],
    is_recurring: [false],
    frequency: [null, Validators.required],
  });

  ngOnInit(): void {
    this.loadFeeStructures();
  }

  loadFeeStructures(): void {
    this.loading = true;
    this.feeStructureService.getFeeStructures().subscribe({
      next: (res) => {
        this.feeStructures = res.data?.fee_structures ?? res.data ?? [];
        this.loading = false;
      },
      error: () => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load fee structures' });
        this.loading = false;
      },
    });
  }

  openDialog(fs?: FeeStructure): void {
    this.form.reset({ is_recurring: false });
    this.isEdit = false;
    this.editingId = null;

    if (fs) {
      this.isEdit = true;
      this.editingId = fs.id;
      this.form.patchValue({
        fee_type: fs.fee_type,
        class_id: fs.class_id,
        academic_year_id: fs.academic_year_id,
        amount: fs.amount,
        due_date: fs.due_date ? new Date(fs.due_date) : null,
        is_recurring: fs.is_recurring,
        frequency: fs.frequency,
      });
    }

    this.dialogVisible = true;
  }

  closeDialog(): void {
    this.dialogVisible = false;
    this.form.reset({ is_recurring: false });
  }

  saveFeeStructure(): void {
    if (this.form.invalid) return;

    this.saving = true;
    const raw = this.form.value;
    const payload: Partial<FeeStructure> = {
      fee_type: raw.fee_type,
      class_id: raw.class_id,
      academic_year_id: raw.academic_year_id,
      amount: raw.amount,
      due_date: raw.due_date ? this.formatDate(raw.due_date) : null,
      is_recurring: raw.is_recurring ?? false,
      frequency: raw.frequency,
    };

    const request$ = this.isEdit && this.editingId !== null
      ? this.feeStructureService.updateFeeStructure(this.editingId, payload)
      : this.feeStructureService.createFeeStructure(payload);

    request$.subscribe({
      next: () => {
        this.saving = false;
        this.dialogVisible = false;
        this.toast.add({
          severity: 'success',
          summary: 'Success',
          detail: this.isEdit ? 'Fee structure updated successfully' : 'Fee structure created successfully',
        });
        this.loadFeeStructures();
      },
      error: () => {
        this.saving = false;
        this.toast.add({
          severity: 'error',
          summary: 'Error',
          detail: this.isEdit ? 'Failed to update fee structure' : 'Failed to create fee structure',
        });
      },
    });
  }

  deleteFeeStructure(fs: FeeStructure): void {
    if (!window.confirm(`Delete fee structure "${fs.fee_type}"? This cannot be undone.`)) return;

    this.feeStructureService.deleteFeeStructure(fs.id).subscribe({
      next: () => {
        this.toast.add({ severity: 'success', summary: 'Deleted', detail: 'Fee structure deleted' });
        this.loadFeeStructures();
      },
      error: () => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to delete fee structure' });
      },
    });
  }

  getFrequencyLabel(freq: string): string {
    const opt = this.frequencyOptions.find(o => o.value === freq);
    return opt ? opt.label : freq;
  }

  getStatusSeverity(isActive: boolean): 'success' | 'danger' {
    return isActive ? 'success' : 'danger';
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
