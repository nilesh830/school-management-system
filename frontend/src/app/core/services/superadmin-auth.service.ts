import { Injectable, signal, computed, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';
import { ApiResponse } from '../models/user.model';

export interface SuperAdmin {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
}

export interface SuperAdminLoginData {
  access_token: string;
  refresh_token: string;
  super_admin: SuperAdmin;
}

@Injectable({ providedIn: 'root' })
export class SuperAdminAuthService {
  private readonly SA_ACCESS_KEY = 'sms_sa_access_token';
  private readonly SA_REFRESH_KEY = 'sms_sa_refresh_token';
  private readonly SA_USER_KEY = 'sms_sa_user';

  private http = inject(HttpClient);
  private router = inject(Router);

  private _superAdmin = signal<SuperAdmin | null>(this._loadSuperAdmin());
  readonly superAdmin = this._superAdmin.asReadonly();
  readonly isAuthenticated = computed(() => !!this._superAdmin());

  login(email: string, password: string): Observable<ApiResponse<SuperAdminLoginData>> {
    return this.http
      .post<ApiResponse<SuperAdminLoginData>>('/api/v1/superadmin/auth/login', { email, password })
      .pipe(
        tap(resp => {
          if (resp.success) {
            localStorage.setItem(this.SA_ACCESS_KEY, resp.data.access_token);
            localStorage.setItem(this.SA_REFRESH_KEY, resp.data.refresh_token);
            localStorage.setItem(this.SA_USER_KEY, JSON.stringify(resp.data.super_admin));
            this._superAdmin.set(resp.data.super_admin);
          }
        })
      );
  }

  logout(): void {
    const token = this.getAccessToken();
    if (token) {
      this.http
        .delete('/api/v1/superadmin/auth/logout', {
          headers: new HttpHeaders({ Authorization: `Bearer ${token}` })
        })
        .subscribe({ error: () => {} });
    }
    this._clearSession();
    this.router.navigate(['/superadmin/login']);
  }

  getAccessToken(): string | null {
    return localStorage.getItem(this.SA_ACCESS_KEY);
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(this.SA_REFRESH_KEY);
  }

  private _clearSession(): void {
    localStorage.removeItem(this.SA_ACCESS_KEY);
    localStorage.removeItem(this.SA_REFRESH_KEY);
    localStorage.removeItem(this.SA_USER_KEY);
    this._superAdmin.set(null);
  }

  private _loadSuperAdmin(): SuperAdmin | null {
    try {
      const stored = localStorage.getItem(this.SA_USER_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  }
}
