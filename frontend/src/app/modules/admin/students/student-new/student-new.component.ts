import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
  AbstractControl,
  ValidationErrors
} from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MessageService } from 'primeng/api';

import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { StepperModule } from 'primeng/stepper';
import { CalendarModule } from 'primeng/calendar';
import { DropdownModule } from 'primeng/dropdown';
import { InputTextModule } from 'primeng/inputtext';
import { InputTextareaModule } from 'primeng/inputtextarea';
import { InputNumberModule } from 'primeng/inputnumber';
import { ToastModule } from 'primeng/toast';
import { DividerModule } from 'primeng/divider';

import { StudentService, StudentPayload } from '../../../../core/services/student.service';
import { ClassesService } from '../../../../core/services/classes.service';

/** Rejects dates in the future */
function noFutureDate(control: AbstractControl): ValidationErrors | null {
  if (!control.value) return null;
  const selected = control.value instanceof Date ? control.value : new Date(control.value);
  const today = new Date();
  today.setHours(23, 59, 59, 999);
  return selected > today ? { futureDate: true } : null;
}

/** Format a JS Date to YYYY-MM-DD string */
function toIsoDate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

@Component({
  selector: 'app-student-new',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
    ButtonModule,
    CardModule,
    StepperModule,
    CalendarModule,
    DropdownModule,
    InputTextModule,
    InputTextareaModule,
    InputNumberModule,
    ToastModule,
    DividerModule
  ],
  providers: [MessageService],
  templateUrl: './student-new.component.html'
})
export class StudentNewComponent implements OnInit {
  private fb = inject(FormBuilder);
  private studentService = inject(StudentService);
  private classesService = inject(ClassesService);
  private router = inject(Router);
  private toast = inject(MessageService);

  activeStep = 0;
  loading = false;
  maxDate = new Date();

  sectionOptions: { label: string; value: number }[] = [];
  loadingSections = false;

  genderOptions = [
    { label: 'Male', value: 'Male' },
    { label: 'Female', value: 'Female' },
    { label: 'Other', value: 'Other' }
  ];

  bloodGroupOptions = [
    { label: 'A+', value: 'A+' },
    { label: 'A-', value: 'A-' },
    { label: 'B+', value: 'B+' },
    { label: 'B-', value: 'B-' },
    { label: 'AB+', value: 'AB+' },
    { label: 'AB-', value: 'AB-' },
    { label: 'O+', value: 'O+' },
    { label: 'O-', value: 'O-' }
  ];

  // ── Step 1: Personal Info ────────────────────────────────────────────────
  step1 = this.fb.group({
    first_name: ['', [Validators.required, Validators.minLength(1), Validators.maxLength(100)]],
    last_name: ['', [Validators.required, Validators.minLength(1), Validators.maxLength(100)]],
    date_of_birth: [null as Date | null, [Validators.required, noFutureDate]],
    gender: ['', Validators.required],
    blood_group: [null as string | null]
  });

  // ── Step 2: Admission Info ───────────────────────────────────────────────
  step2 = this.fb.group({
    admission_no: ['', [Validators.required, Validators.maxLength(20)]],
    admission_date: [null as Date | null, [Validators.required, noFutureDate]],
    section_id: [null as number | null]  // optional initial placement
  });

  // ── Step 3: Contact Details ──────────────────────────────────────────────
  step3 = this.fb.group({
    address: [null as string | null],
    phone: [null as string | null, Validators.maxLength(20)],
    user_id: [null as number | null]
  });

  // ── Convenience getters ──────────────────────────────────────────────────
  get f1() { return this.step1.controls; }
  get f2() { return this.step2.controls; }
  get f3() { return this.step3.controls; }

  ngOnInit(): void {
    this.loadingSections = true;
    this.classesService.getSections(undefined, 1, 100).subscribe({
      next: (res) => {
        this.sectionOptions = (res.data.sections ?? []).map((s) => ({
          label: s.class_name ? `${s.class_name} — ${s.name}` : s.name,
          value: s.id
        }));
        this.loadingSections = false;
      },
      error: () => {
        this.loadingSections = false;
      }
    });
  }

  // ── Navigation ───────────────────────────────────────────────────────────
  nextStep(nextCallback: () => void): void {
    const current = this.activeStep === 0 ? this.step1 : this.step2;
    if (current.invalid) {
      current.markAllAsTouched();
      return;
    }
    this.activeStep++;
    nextCallback();
  }

  prevStep(prevCallback: () => void): void {
    this.activeStep--;
    prevCallback();
  }

  // ── Submit ───────────────────────────────────────────────────────────────
  onSubmit(): void {
    this.step3.markAllAsTouched();
    if (this.step1.invalid || this.step2.invalid || this.step3.invalid) {
      return;
    }

    const s1 = this.step1.getRawValue();
    const s2 = this.step2.getRawValue();
    const s3 = this.step3.getRawValue();

    const payload: StudentPayload = {
      first_name: s1.first_name!,
      last_name: s1.last_name!,
      date_of_birth: toIsoDate(s1.date_of_birth!),
      gender: s1.gender as 'Male' | 'Female' | 'Other',
      blood_group: s1.blood_group ?? null,
      admission_no: s2.admission_no!,
      admission_date: toIsoDate(s2.admission_date!),
      section_id: s2.section_id ?? null,
      address: s3.address ?? null,
      phone: s3.phone ?? null,
      user_id: s3.user_id ?? null
    };

    this.loading = true;
    this.studentService.createStudent(payload).subscribe({
      next: () => {
        this.loading = false;
        this.toast.add({
          severity: 'success',
          summary: 'Enrolled',
          detail: 'Student enrolled successfully',
          life: 2500
        });
        setTimeout(() => this.router.navigate(['/admin/students']), 2000);
      },
      error: (err) => {
        this.loading = false;
        const status = err?.status;
        const body = err?.error;

        if (status === 409) {
          this.toast.add({
            severity: 'error',
            summary: 'Duplicate',
            detail: 'Admission number already exists'
          });
          return;
        }

        if (status === 422 && body?.errors) {
          const msgs = Object.entries(body.errors as Record<string, string[]>)
            .map(([field, errs]) => `${field}: ${errs.join(', ')}`)
            .join('\n');
          this.toast.add({
            severity: 'error',
            summary: 'Validation Error',
            detail: msgs
          });
          return;
        }

        this.toast.add({
          severity: 'error',
          summary: 'Error',
          detail: body?.message || 'Failed to enroll student. Please try again.'
        });
      }
    });
  }

  // ── Helper: is a control invalid and touched ─────────────────────────────
  isInvalid(control: AbstractControl): boolean {
    return control.invalid && (control.dirty || control.touched);
  }
}
