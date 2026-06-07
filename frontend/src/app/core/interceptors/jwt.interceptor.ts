import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

const PUBLIC_URLS = ['/auth/login', '/auth/forgot-password', '/auth/reset-password'];

export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);

  // Skip token injection for public endpoints
  if (PUBLIC_URLS.some(url => req.url.includes(url))) {
    return next(req);
  }

  // Don't override if caller already set Authorization (e.g., refresh call with refresh token)
  const token = auth.getAccessToken();
  const authReq = token && !req.headers.has('Authorization')
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(authReq).pipe(
    catchError(error => {
      // Auto-refresh on 401 — but not for the refresh or logout endpoint itself
      if (error.status === 401 && !req.url.includes('/auth/refresh') && !req.url.includes('/auth/logout')) {
        const refreshToken = auth.getRefreshToken();
        if (!refreshToken) {
          auth.logout();
          return throwError(() => error);
        }

        return auth.refreshToken().pipe(
          switchMap(() => {
            const newToken = auth.getAccessToken()!;
            const retried = req.clone({ setHeaders: { Authorization: `Bearer ${newToken}` } });
            return next(retried);
          }),
          catchError(refreshError => {
            auth.logout();
            return throwError(() => refreshError);
          })
        );
      }
      return throwError(() => error);
    })
  );
};
