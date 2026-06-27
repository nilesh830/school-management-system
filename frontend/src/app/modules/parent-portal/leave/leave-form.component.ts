import { Component, Input, Output, EventEmitter, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { DropdownModule } from 'primeng/dropdown';
import { CalendarModule } from 'primeng/calendar';
import { InputTextareaModule } from 'primeng/inputtextarea';
import { SelectButtonModule } from 'primeng/selectbutton';
import { MessageModule } from 'primeng/message';
import { ParentPortalService } from '../parent-portal.service';

@Component({
  selector: 'app-leave-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    ButtonModule,
    DropdownModule,
    CalendarModule,
    InputTextareaModule,
    SelectButtonModule,
    MessageModule
  ],
  template: `
    <form [formGroup]="form" (ngSubmit)="onSubmit()">
      <!-- Child selector -->
      <div class="field mb-3">
        <label class="block text-sm font-medium text-700 mb-1">Child <span class="text-red-500">*</span></label>
        <p-dropdown
          formControlName="student_id"
          [options]="children"
          optionLabel="full_name"
          optionValue="student_id"
          placeholder="Select child"
          styleClass="w-full"
        />
        @if (form.get('student_id')?.invalid && form.get('student_id')?.touched) {
          <small class="text-red-500">Please select a child.</small>
        }
      </div>

      <!-- Leave type -->
      <div class="field mb-3">
        <label class="block text-sm font-medium text-700 mb-1">Leave Type <span class="text-red-500">*</span></label>
        <p-selectButton
          formControlName="leave_type"
          [options]="leaveTypeOptions"
          optionLabel="label"
          optionValue="value"
          styleClass="w-full"
        />
      </div>

      <!-- Date range -->
      <div class="grid mb-3">
        <div class="col-6">
          <div class="field">
            <label class="block text-sm font-medium text-700 mb-1">From Date <span class="text-red-500">*</span></label>
            <p-calendar
              formControlName="from_date"
              [minDate]="today"
              dateFormat="yy-mm-dd"
              [showIcon]="true"
              styleClass="w-full"
              inputStyleClass="w-full"
            />
            @if (form.get('from_date')?.invalid && form.get('from_date')?.touched) {
              <small class="text-red-500">From date is required.</small>
            }
          </div>
        </div>
        <div class="col-6">
          <div class="field">
            <label class="block text-sm font-medium text-700 mb-1">To Date <span class="text-red-500">*</span></label>
            <p-calendar
              formControlName="to_date"
              [minDate]="form.get('from_date')?.value || today"
              dateFormat="yy-mm-dd"
              [showIcon]="true"
              styleClass="w-full"
              inputStyleClass="w-full"
            />
            @if (form.get('to_date')?.invalid && form.get('to_date')?.touched) {
              <small class="text-red-500">To date is required.</small>
            }
          </div>
        </div>
      </div>

      <!-- Reason -->
      <div class="field mb-3">
        <label class="block text-sm font-medium text-700 mb-1">Reason <span class="text-red-500">*</span></label>
        <textarea
          pInputTextarea
          formControlName="reason"
          rows="4"
          placeholder="Describe the reason (minimum 10 characters)"
          class="w-full"
        ></textarea>
        @if (form.get('reason')?.invalid && form.get('reason')?.touched) {
          <small class="text-red-500">
            @if (form.get('reason')?.errors?.['required']) { Reason is required. }
            @else if (form.get('reason')?.errors?.['minlength']) { Minimum 10 characters required. }
          </small>
        }
      </div>

      <!-- API error -->
      @if (apiError) {
        <p-message severity="error" [text]="apiError" styleClass="w-full mb-3" />
      }

      <!-- Actions -->
      <div class="flex justify-content-end gap-2">
        <p-button
          label="Cancel"
          severity="secondary"
          [text]="true"
          type="button"
          (onClick)="onCancel()"
        />
        <p-button
          label="Submit Application"
          icon="pi pi-check"
          type="submit"
          [loading]="submitting"
          [disabled]="form.invalid"
        />
      </div>
    </form>
  `
})
export class LeaveFormComponent implements OnInit {
  @Input() children: any[] = [];
  @Output() submitted = new EventEmitter<void>();
  @Output() cancelled = new EventEmitter<void>();

  private fb = inject(FormBuilder);
  private portalService = inject(ParentPortalService);

  today = new Date();
  submitting = false;
  apiError = '';

  leaveTypeOptions = [
    { label: 'Sick', value: 'sick' },
    { label: 'Family', value: 'family' },
    { label: 'Personal', value: 'personal' },
    { label: 'Other', value: 'other' }
  ];

  form = this.fb.group({
    student_id: [null as number | null, Validators.required],
    leave_type: ['sick', Validators.required],
    from_date: [null as Date | null, Validators.required],
    to_date: [null as Date | null, Validators.required],
    reason: ['', [Validators.required, Validators.minLength(10)]]
  });

  ngOnInit(): void {}

  onSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.submitting = true;
    this.apiError = '';

    const raw = this.form.value;
    const payload = {
      student_id: raw.student_id,
      leave_type: raw.leave_type,
      from_date: this.formatDate(raw.from_date!),
      to_date: this.formatDate(raw.to_date!),
      reason: raw.reason
    };

    this.portalService.submitLeave(payload).subscribe({
      next: () => {
        this.submitting = false;
        this.submitted.emit();
      },
      error: (err: any) => {
        this.submitting = false;
        this.apiError = err?.error?.message ?? 'Failed to submit leave application.';
      }
    });
  }

  onCancel(): void {
    this.cancelled.emit();
  }

  private formatDate(date: Date): string {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }
}
