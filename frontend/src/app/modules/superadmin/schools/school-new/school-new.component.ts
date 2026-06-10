import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MessageService } from 'primeng/api';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { PasswordModule } from 'primeng/password';
import { ButtonModule } from 'primeng/button';
import { DropdownModule } from 'primeng/dropdown';
import { ToastModule } from 'primeng/toast';
import { ToolbarModule } from 'primeng/toolbar';
import { SchoolsService } from '../../../../core/services/schools.service';

const MONTH_OPTIONS = [
  { label: 'January', value: 1 },
  { label: 'February', value: 2 },
  { label: 'March', value: 3 },
  { label: 'April', value: 4 },
  { label: 'May', value: 5 },
  { label: 'June', value: 6 },
  { label: 'July', value: 7 },
  { label: 'August', value: 8 },
  { label: 'September', value: 9 },
  { label: 'October', value: 10 },
  { label: 'November', value: 11 },
  { label: 'December', value: 12 }
];

@Component({
  selector: 'app-school-new',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
    CardModule,
    InputTextModule,
    PasswordModule,
    ButtonModule,
    DropdownModule,
    ToastModule,
    ToolbarModule
  ],
  providers: [MessageService],
  templateUrl: './school-new.component.html'
})
export class SchoolNewComponent {
  private fb = inject(FormBuilder);
  private schoolsService = inject(SchoolsService);
  private router = inject(Router);
  private toast = inject(MessageService);

  readonly monthOptions = MONTH_OPTIONS;

  form = this.fb.group({
    name: ['', Validators.required],
    slug: ['', [
      Validators.required,
      Validators.pattern(/^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$/)
    ]],
    admin_email: ['', [Validators.required, Validators.email]],
    admin_password: ['', [Validators.required, Validators.minLength(8)]],
    address: [''],
    phone: [''],
    academic_year_start_month: [null as number | null]
  });

  loading = false;

  get nameCtrl() { return this.form.controls.name; }
  get slugCtrl() { return this.form.controls.slug; }
  get adminEmailCtrl() { return this.form.controls.admin_email; }
  get adminPasswordCtrl() { return this.form.controls.admin_password; }

  onSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.loading = true;
    const val = this.form.value;

    const payload: any = {
      name: val.name!,
      slug: val.slug!,
      admin_email: val.admin_email!,
      admin_password: val.admin_password!
    };
    if (val.address) payload.address = val.address;
    if (val.phone) payload.phone = val.phone;
    if (val.academic_year_start_month != null) {
      payload.academic_year_start_month = val.academic_year_start_month;
    }

    this.schoolsService.createSchool(payload).subscribe({
      next: (res) => {
        this.loading = false;
        this.toast.add({ severity: 'success', summary: 'Success', detail: 'School created successfully' });
        setTimeout(() => this.router.navigate(['/superadmin/schools', res.data.id]), 1000);
      },
      error: (err) => {
        this.loading = false;
        if (err.status === 409) {
          this.slugCtrl.setErrors({ slugTaken: true });
          this.toast.add({ severity: 'error', summary: 'Conflict', detail: 'Slug is already taken' });
        } else {
          const detail = err.error?.message || 'Failed to create school';
          this.toast.add({ severity: 'error', summary: 'Error', detail });
        }
      }
    });
  }
}
