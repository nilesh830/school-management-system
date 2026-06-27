import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, ActivatedRoute, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { MessageService } from 'primeng/api';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { DropdownModule } from 'primeng/dropdown';
import { CalendarModule } from 'primeng/calendar';
import { PasswordModule } from 'primeng/password';
import { ToastModule } from 'primeng/toast';
import { InputTextareaModule } from 'primeng/inputtextarea';
import { DividerModule } from 'primeng/divider';

import { TeacherService } from '../../../../core/services/teacher.service';

@Component({
  selector: 'app-teacher-form',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, RouterLink,
    CardModule, ButtonModule, InputTextModule, DropdownModule,
    CalendarModule, PasswordModule, ToastModule, InputTextareaModule, DividerModule
  ],
  providers: [MessageService],
  template: `
    <p-toast position="top-right" />

    <p-card [header]="isEdit ? 'Edit Teacher' : 'Add Teacher'">
      <form [formGroup]="form" (ngSubmit)="submit()">

        @if (!isEdit) {
          <p-divider align="left"><b class="text-sm text-600">Login Account</b></p-divider>
          <div class="grid">
            <div class="col-12 md:col-6 field">
              <label>Email <span class="text-red-500">*</span></label>
              <input pInputText formControlName="email" type="email" class="w-full" placeholder="teacher@school.com" />
              @if (isInvalid('email')) {
                <small class="p-error">Valid email is required</small>
              }
            </div>
            <div class="col-12 md:col-6 field">
              <label>Password <span class="text-red-500">*</span></label>
              <p-password formControlName="password" [feedback]="true" [toggleMask]="true" styleClass="w-full" />
              @if (isInvalid('password')) {
                <small class="p-error">Password (min 8 characters) is required</small>
              }
            </div>
          </div>
        }

        <p-divider align="left"><b class="text-sm text-600">Teacher Details</b></p-divider>
        <div class="grid">
          <div class="col-12 md:col-4 field">
            <label>Employee ID <span class="text-red-500">*</span></label>
            <input pInputText formControlName="employee_id" class="w-full" placeholder="EMP001" />
            @if (isInvalid('employee_id')) {
              <small class="p-error">Employee ID is required</small>
            }
          </div>
          <div class="col-12 md:col-4 field">
            <label>First Name <span class="text-red-500">*</span></label>
            <input pInputText formControlName="first_name" class="w-full" />
            @if (isInvalid('first_name')) {
              <small class="p-error">First name is required</small>
            }
          </div>
          <div class="col-12 md:col-4 field">
            <label>Last Name <span class="text-red-500">*</span></label>
            <input pInputText formControlName="last_name" class="w-full" />
            @if (isInvalid('last_name')) {
              <small class="p-error">Last name is required</small>
            }
          </div>
          <div class="col-12 md:col-4 field">
            <label>Joining Date <span class="text-red-500">*</span></label>
            <p-calendar formControlName="joining_date" dateFormat="yy-mm-dd" [showIcon]="true" styleClass="w-full" />
            @if (isInvalid('joining_date')) {
              <small class="p-error">Joining date is required</small>
            }
          </div>
          <div class="col-12 md:col-4 field">
            <label>Date of Birth</label>
            <p-calendar formControlName="date_of_birth" dateFormat="yy-mm-dd" [showIcon]="true" styleClass="w-full" />
          </div>
          <div class="col-12 md:col-4 field">
            <label>Gender</label>
            <p-dropdown formControlName="gender" [options]="genderOptions" optionLabel="label" optionValue="value" placeholder="Select gender" styleClass="w-full" />
          </div>
          <div class="col-12 md:col-6 field">
            <label>Qualification</label>
            <input pInputText formControlName="qualification" class="w-full" placeholder="B.Ed, M.Sc…" />
          </div>
          <div class="col-12 md:col-6 field">
            <label>Specialization</label>
            <input pInputText formControlName="specialization" class="w-full" placeholder="Mathematics, Science…" />
          </div>
          <div class="col-12 md:col-6 field">
            <label>Phone</label>
            <input pInputText formControlName="phone" class="w-full" />
          </div>
          <div class="col-12 md:col-6 field">
            <label>Address</label>
            <textarea pInputTextarea formControlName="address" class="w-full" rows="2"></textarea>
          </div>
        </div>

        <div class="flex gap-2 mt-3">
          <p-button
            type="submit"
            [label]="isEdit ? 'Save Changes' : 'Create Teacher'"
            icon="pi pi-check"
            [loading]="loading"
            [disabled]="form.invalid"
          />
          <p-button
            type="button"
            label="Cancel"
            severity="secondary"
            routerLink="/admin/teachers"
          />
        </div>
      </form>
    </p-card>
  `
})
export class TeacherFormComponent implements OnInit {
  private fb = inject(FormBuilder);
  private http = inject(HttpClient);
  private teacherService = inject(TeacherService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private toast = inject(MessageService);

  loading = false;
  isEdit = false;
  teacherId?: number;

  genderOptions = [
    { label: 'Male', value: 'Male' },
    { label: 'Female', value: 'Female' },
    { label: 'Other', value: 'Other' },
  ];

  form = this.fb.group({
    email: ['', [Validators.email]],
    password: ['', [Validators.minLength(8)]],
    employee_id: ['', Validators.required],
    first_name: ['', Validators.required],
    last_name: ['', Validators.required],
    joining_date: [null as Date | null, Validators.required],
    date_of_birth: [null as Date | null],
    gender: [null as string | null],
    qualification: [''],
    specialization: [''],
    phone: [''],
    address: [''],
  });

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.isEdit = true;
      this.teacherId = +id;
      // On edit, email/password not required
      this.form.get('email')?.clearValidators();
      this.form.get('password')?.clearValidators();
      this.form.get('email')?.updateValueAndValidity();
      this.form.get('password')?.updateValueAndValidity();
      this.loadTeacher(this.teacherId);
    } else {
      // On create, email/password required
      this.form.get('email')?.addValidators(Validators.required);
      this.form.get('password')?.addValidators([Validators.required, Validators.minLength(8)]);
      this.form.get('email')?.updateValueAndValidity();
      this.form.get('password')?.updateValueAndValidity();
    }
  }

  private loadTeacher(id: number): void {
    this.teacherService.getTeacherById(id).subscribe({
      next: (res) => {
        const t = res.data;
        this.form.patchValue({
          employee_id: t.employee_id,
          first_name: t.first_name,
          last_name: t.last_name,
          joining_date: t.joining_date ? new Date(t.joining_date) : null,
          date_of_birth: t.date_of_birth ? new Date(t.date_of_birth) : null,
          gender: t.gender ?? null,
          qualification: t.qualification ?? '',
          specialization: t.specialization ?? '',
          phone: t.phone ?? '',
          address: t.address ?? '',
        });
      },
      error: () => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load teacher' });
      }
    });
  }

  isInvalid(field: string): boolean {
    const c = this.form.get(field);
    return !!(c && c.invalid && (c.dirty || c.touched));
  }

  private toIsoDate(d: Date | null): string | null {
    if (!d) return null;
    return d.toISOString().split('T')[0];
  }

  submit(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.loading = true;

    if (this.isEdit) {
      const payload = {
        employee_id: this.form.value.employee_id,
        first_name: this.form.value.first_name,
        last_name: this.form.value.last_name,
        joining_date: this.toIsoDate(this.form.value.joining_date ?? null),
        date_of_birth: this.toIsoDate(this.form.value.date_of_birth ?? null),
        gender: this.form.value.gender || null,
        qualification: this.form.value.qualification || null,
        specialization: this.form.value.specialization || null,
        phone: this.form.value.phone || null,
        address: this.form.value.address || null,
      };
      this.teacherService.updateTeacher(this.teacherId!, payload).subscribe({
        next: () => {
          this.toast.add({ severity: 'success', summary: 'Saved', detail: 'Teacher updated' });
          this.router.navigate(['/admin/teachers', this.teacherId]);
        },
        error: (err) => {
          this.toast.add({ severity: 'error', summary: 'Error', detail: err.error?.message || 'Failed to update teacher' });
          this.loading = false;
        }
      });
    } else {
      // Create user first, then create teacher
      this.http.post<any>('/api/v1/users', {
        email: this.form.value.email,
        password: this.form.value.password,
        first_name: this.form.value.first_name,
        last_name: this.form.value.last_name,
        role: 'teacher',
      }).subscribe({
        next: (userRes) => {
          const userId = userRes.data?.id;
          const payload = {
            user_id: userId,
            employee_id: this.form.value.employee_id,
            first_name: this.form.value.first_name,
            last_name: this.form.value.last_name,
            joining_date: this.toIsoDate(this.form.value.joining_date ?? null),
            date_of_birth: this.toIsoDate(this.form.value.date_of_birth ?? null),
            gender: this.form.value.gender || null,
            qualification: this.form.value.qualification || null,
            specialization: this.form.value.specialization || null,
            phone: this.form.value.phone || null,
            address: this.form.value.address || null,
          };
          this.teacherService.createTeacher(payload).subscribe({
            next: (res) => {
              this.toast.add({ severity: 'success', summary: 'Created', detail: 'Teacher added successfully' });
              this.router.navigate(['/admin/teachers', res.data.id]);
            },
            error: (err) => {
              this.toast.add({ severity: 'error', summary: 'Error', detail: err.error?.message || 'Failed to create teacher' });
              this.loading = false;
            }
          });
        },
        error: (err) => {
          this.toast.add({ severity: 'error', summary: 'Error', detail: err.error?.message || 'Failed to create user account' });
          this.loading = false;
        }
      });
    }
  }
}
