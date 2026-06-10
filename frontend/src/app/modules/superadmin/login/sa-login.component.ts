import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { MessageService } from 'primeng/api';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { PasswordModule } from 'primeng/password';
import { ButtonModule } from 'primeng/button';
import { ToastModule } from 'primeng/toast';
import { SuperAdminAuthService } from '../../../core/services/superadmin-auth.service';

@Component({
  selector: 'app-sa-login',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    CardModule,
    InputTextModule,
    PasswordModule,
    ButtonModule,
    ToastModule
  ],
  providers: [MessageService],
  templateUrl: './sa-login.component.html',
  styleUrl: './sa-login.component.scss'
})
export class SaLoginComponent implements OnInit {
  private fb = inject(FormBuilder);
  private saAuth = inject(SuperAdminAuthService);
  private router = inject(Router);
  private toast = inject(MessageService);

  form = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]]
  });

  loading = false;

  get emailCtrl() { return this.form.controls.email; }
  get passwordCtrl() { return this.form.controls.password; }

  ngOnInit(): void {
    if (this.saAuth.isAuthenticated()) {
      this.router.navigate(['/superadmin/dashboard']);
    }
  }

  onSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.loading = true;
    const { email, password } = this.form.value;

    this.saAuth.login(email!, password!).subscribe({
      next: () => {
        this.loading = false;
        this.router.navigate(['/superadmin/dashboard']);
      },
      error: (err) => {
        this.loading = false;
        const detail = err.error?.message || 'Invalid credentials. Please try again.';
        this.toast.add({ severity: 'error', summary: 'Login Failed', detail });
      }
    });
  }
}
