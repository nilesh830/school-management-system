import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const roleGuard = (allowedRoles: string[]): CanActivateFn => {
  return () => {
    const auth = inject(AuthService);
    const router = inject(Router);
    const user = auth.currentUser();

    if (!user) {
      router.navigate(['/login']);
      return false;
    }
    if (!allowedRoles.includes(user.role)) {
      router.navigate(['/unauthorized']);
      return false;
    }
    return true;
  };
};
