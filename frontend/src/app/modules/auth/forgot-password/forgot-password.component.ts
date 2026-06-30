import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, RouterLink,
    CardModule, ButtonModule, InputTextModule, MessageModule
  ],
  templateUrl: './forgot-password.component.html'
})
export class ForgotPasswordComponent implements OnInit {
  private fb = inject(FormBuilder);
  private http = inject(HttpClient);

  form = this.fb.group({
    school_slug: ['', [Validators.required, Validators.pattern(/^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$|^[a-z0-9]{2,50}$/)]],
    email: ['', [Validators.required, Validators.email]]
  });

  loading = false;
  submitted = false;

  get slugCtrl() { return this.form.controls.school_slug; }
  get emailCtrl() { return this.form.controls.email; }

  ngOnInit(): void {
    const savedSlug = localStorage.getItem('sms_school_slug');
    if (savedSlug) {
      this.form.patchValue({ school_slug: savedSlug });
    }
  }

  onSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.loading = true;

    const { email, school_slug } = this.form.value;
    this.http.post('/api/v1/auth/forgot-password', { email, school_slug }).subscribe({
      next: () => {
        this.loading = false;
        this.submitted = true;
      },
      error: () => {
        this.loading = false;
        // Always show success — prevents email enumeration
        this.submitted = true;
      }
    });
  }
}
