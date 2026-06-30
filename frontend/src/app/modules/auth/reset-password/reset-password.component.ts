import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { PasswordModule } from 'primeng/password';
import { MessageModule } from 'primeng/message';
import { HttpClient } from '@angular/common/http';

function passwordStrength(control: AbstractControl): ValidationErrors | null {
  const v: string = control.value ?? '';
  if (!/[A-Z]/.test(v)) return { strength: 'Must contain at least one uppercase letter' };
  if (!/[0-9]/.test(v)) return { strength: 'Must contain at least one number' };
  return null;
}

function matchPasswords(group: AbstractControl): ValidationErrors | null {
  const pwd = group.get('new_password')?.value;
  const confirm = group.get('confirm_password')?.value;
  return pwd === confirm ? null : { mismatch: true };
}

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, RouterLink,
    CardModule, ButtonModule, PasswordModule, MessageModule
  ],
  templateUrl: './reset-password.component.html'
})
export class ResetPasswordComponent {
  private fb = inject(FormBuilder);
  private http = inject(HttpClient);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  form = this.fb.group({
    new_password: ['', [Validators.required, Validators.minLength(8), passwordStrength]],
    confirm_password: ['', Validators.required]
  }, { validators: matchPasswords });

  loading = false;
  success = false;
  errorMessage = '';

  private get token(): string | null {
    return this.route.snapshot.queryParamMap.get('token');
  }

  private get schoolSlug(): string | null {
    return this.route.snapshot.queryParamMap.get('school_slug');
  }

  get pwdCtrl() { return this.form.controls.new_password; }
  get confirmCtrl() { return this.form.controls.confirm_password; }

  onSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    if (!this.token || !this.schoolSlug) {
      this.errorMessage = 'Invalid reset link. Please request a new one.';
      return;
    }
    this.loading = true;
    this.errorMessage = '';

    this.http.post('/api/v1/auth/reset-password', {
      token: this.token,
      school_slug: this.schoolSlug,
      password: this.form.value.new_password
    }).subscribe({
      next: () => {
        this.loading = false;
        this.success = true;
        setTimeout(() => this.router.navigate(['/login']), 3000);
      },
      error: (err) => {
        this.loading = false;
        this.errorMessage = err.error?.message || 'Reset failed. The link may have expired.';
      }
    });
  }
}
