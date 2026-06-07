import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { PasswordModule } from 'primeng/password';
import { DropdownModule } from 'primeng/dropdown';
import { ToastModule } from 'primeng/toast';
import { MessageService } from 'primeng/api';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-create-user',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, RouterLink,
    CardModule, ButtonModule, InputTextModule, PasswordModule,
    DropdownModule, ToastModule
  ],
  providers: [MessageService],
  templateUrl: './create-user.component.html'
})
export class CreateUserComponent {
  private fb = inject(FormBuilder);
  private http = inject(HttpClient);
  private router = inject(Router);
  private toast = inject(MessageService);

  roles = [
    { label: 'Administrator', value: 'admin' },
    { label: 'Teacher', value: 'teacher' },
    { label: 'Student', value: 'student' },
    { label: 'Parent / Guardian', value: 'parent' }
  ];

  form = this.fb.group({
    first_name: ['', Validators.required],
    last_name: ['', Validators.required],
    email: ['', [Validators.required, Validators.email]],
    role: ['', Validators.required],
    password: ['', [Validators.required, Validators.minLength(8)]]
  });

  loading = false;

  get f() { return this.form.controls; }

  generatePassword(): void {
    const upper = 'ABCDEFGHJKMNPQRSTUVWXYZ';
    const lower = 'abcdefghjkmnpqrstuvwxyz';
    const digits = '23456789';
    const special = '!@#$';
    const all = upper + lower + digits + special;
    const rand = (s: string) => s[Math.floor(Math.random() * s.length)];
    // Guarantee at least one of each required character type
    const pwd = [
      rand(upper), rand(lower), rand(digits), rand(special),
      ...Array.from({ length: 8 }, () => rand(all))
    ].sort(() => Math.random() - 0.5).join('');
    this.f.password.setValue(pwd);
  }

  onSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.loading = true;

    this.http.post('/api/v1/users', this.form.value).subscribe({
      next: () => {
        this.loading = false;
        this.toast.add({
          severity: 'success',
          summary: 'User Created',
          detail: 'The user account has been created successfully.'
        });
        setTimeout(() => this.router.navigate(['/admin/dashboard']), 1800);
      },
      error: (err) => {
        this.loading = false;
        this.toast.add({
          severity: 'error',
          summary: 'Error',
          detail: err.error?.message || 'Failed to create user. Please try again.'
        });
      }
    });
  }
}
