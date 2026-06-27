import { Component, Input, Output, EventEmitter, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { InputTextareaModule } from 'primeng/inputtextarea';
import { DropdownModule } from 'primeng/dropdown';
import { MessageModule } from 'primeng/message';
import { ParentPortalService } from '../parent-portal.service';

@Component({
  selector: 'app-new-thread-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    ButtonModule,
    InputTextModule,
    InputTextareaModule,
    DropdownModule,
    MessageModule
  ],
  template: `
    <form [formGroup]="form" (ngSubmit)="onSubmit()">
      <!-- Child selector -->
      <div class="field mb-3">
        <label class="block text-sm font-medium text-700 mb-1">Regarding Child <span class="text-red-500">*</span></label>
        <p-dropdown
          formControlName="child_id"
          [options]="children"
          optionLabel="full_name"
          optionValue="student_id"
          placeholder="Select child"
          styleClass="w-full"
        />
        @if (form.get('child_id')?.invalid && form.get('child_id')?.touched) {
          <small class="text-red-500">Please select a child.</small>
        }
      </div>

      <!-- Subject -->
      <div class="field mb-3">
        <label class="block text-sm font-medium text-700 mb-1">Subject <span class="text-red-500">*</span></label>
        <input
          pInputText
          formControlName="subject"
          placeholder="Message subject"
          class="w-full"
        />
        @if (form.get('subject')?.invalid && form.get('subject')?.touched) {
          <small class="text-red-500">Subject is required.</small>
        }
      </div>

      <!-- First message -->
      <div class="field mb-3">
        <label class="block text-sm font-medium text-700 mb-1">Message <span class="text-red-500">*</span></label>
        <textarea
          pInputTextarea
          formControlName="message"
          rows="4"
          placeholder="Write your message..."
          class="w-full"
        ></textarea>
        @if (form.get('message')?.invalid && form.get('message')?.touched) {
          <small class="text-red-500">Message is required.</small>
        }
      </div>

      @if (apiError) {
        <p-message severity="error" [text]="apiError" styleClass="w-full mb-3" />
      }

      <div class="flex justify-content-end gap-2">
        <p-button
          label="Cancel"
          severity="secondary"
          [text]="true"
          type="button"
          (onClick)="onCancel()"
        />
        <p-button
          label="Send"
          icon="pi pi-send"
          type="submit"
          [loading]="submitting"
          [disabled]="form.invalid"
        />
      </div>
    </form>
  `
})
export class NewThreadDialogComponent {
  @Input() children: any[] = [];
  @Output() created = new EventEmitter<void>();
  @Output() cancelled = new EventEmitter<void>();

  private fb = inject(FormBuilder);
  private portalService = inject(ParentPortalService);

  submitting = false;
  apiError = '';

  form = this.fb.group({
    child_id: [null as number | null, Validators.required],
    subject: ['', Validators.required],
    message: ['', Validators.required]
  });

  onSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.submitting = true;
    this.apiError = '';

    this.portalService.createThread(this.form.value).subscribe({
      next: () => {
        this.submitting = false;
        this.created.emit();
      },
      error: (err: any) => {
        this.submitting = false;
        this.apiError = err?.error?.message ?? 'Failed to send message.';
      }
    });
  }

  onCancel(): void {
    this.cancelled.emit();
  }
}
