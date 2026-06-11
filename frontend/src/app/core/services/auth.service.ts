import { Injectable, signal, computed } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';
import { User, ApiResponse } from '../models/user.model';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly ACCESS_TOKEN_KEY = 'sms_access_token';
  private readonly REFRESH_TOKEN_KEY = 'sms_refresh_token';
  private readonly USER_KEY = 'sms_user';

  private _currentUser = signal<User | null>(this._loadUser());

  readonly currentUser = this._currentUser.asReadonly();
  readonly isAuthenticated = computed(() => !!this._currentUser());

  constructor(private http: HttpClient, private router: Router) {}

  login(email: string, password: string, schoolSlug: string): Observable<ApiResponse<{ access_token: string; refresh_token: string; user: User }>> {
    return this.http.post<ApiResponse<any>>('/api/v1/auth/login', {
      email,
      password,
      school_slug: schoolSlug,
    }).pipe(
      tap(resp => {
        if (resp.success) {
          localStorage.setItem(this.ACCESS_TOKEN_KEY, resp.data.access_token);
          localStorage.setItem(this.REFRESH_TOKEN_KEY, resp.data.refresh_token);
          localStorage.setItem(this.USER_KEY, JSON.stringify(resp.data.user));
          localStorage.setItem('sms_school_slug', schoolSlug);
          this._currentUser.set(resp.data.user);
        }
      })
    );
  }

  logout(): void {
    if (this.getAccessToken()) {
      this.http.delete('/api/v1/auth/logout').subscribe({ error: () => {} });
    }
    this._clearSession();
    this.router.navigate(['/login']);
  }

  // Sends refresh token in Authorization header (interceptor skips if header already set)
  refreshToken(): Observable<ApiResponse<{ access_token: string }>> {
    const refreshToken = this.getRefreshToken();
    return this.http.post<ApiResponse<any>>('/api/v1/auth/refresh', {}, {
      headers: new HttpHeaders({ Authorization: `Bearer ${refreshToken}` })
    }).pipe(
      tap(resp => {
        if (resp.success && resp.data.access_token) {
          localStorage.setItem(this.ACCESS_TOKEN_KEY, resp.data.access_token);
        }
      })
    );
  }

  getAccessToken(): string | null {
    return localStorage.getItem(this.ACCESS_TOKEN_KEY);
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(this.REFRESH_TOKEN_KEY);
  }

  updateCurrentUser(user: Partial<User>): void {
    const merged = { ...this._currentUser()!, ...user };
    localStorage.setItem(this.USER_KEY, JSON.stringify(merged));
    this._currentUser.set(merged);
  }

  redirectToDashboard(): void {
    const roleRoutes: Record<string, string> = {
      admin: '/admin/dashboard',
      teacher: '/teacher/dashboard',
      student: '/student/dashboard',
      parent: '/parent/dashboard',
      super_admin: '/superadmin/dashboard',
    };
    const role = this._currentUser()?.role ?? '';
    this.router.navigate([roleRoutes[role] ?? '/login']);
  }

  private _clearSession(): void {
    localStorage.removeItem(this.ACCESS_TOKEN_KEY);
    localStorage.removeItem(this.REFRESH_TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    this._currentUser.set(null);
  }

  private _loadUser(): User | null {
    try {
      const stored = localStorage.getItem('sms_user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  }
}
