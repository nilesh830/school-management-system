import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { PasswordModule } from 'primeng/password';
import { MessageModule } from 'primeng/message';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, RouterLink,
    CardModule, InputTextModule, PasswordModule, MessageModule
  ],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss'
})
export class LoginComponent implements OnInit {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);

  form = this.fb.group({
    school_slug: ['', [Validators.required, Validators.pattern(/^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$|^[a-z0-9]{2,50}$/)]],
    email: ['', [Validators.required, Validators.email]],
    password: ['', Validators.required]
  });

  loading = false;
  errorMessage = '';

  get slugCtrl() { return this.form.controls.school_slug; }
  get emailCtrl() { return this.form.controls.email; }
  get passwordCtrl() { return this.form.controls.password; }

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
    this.errorMessage = '';

    const { email, password, school_slug } = this.form.value;
    this.auth.login(email!, password!, school_slug!).subscribe({
      next: () => {
        this.loading = false;
        this.auth.redirectToDashboard();
      },
      error: (err) => {
        this.loading = false;
        this.errorMessage = err.error?.message || 'Login failed. Please try again.';
      }
    });
  }
}
