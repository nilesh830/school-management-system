import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { SuperAdminAuthService } from '../services/superadmin-auth.service';

export const superAdminGuard: CanActivateFn = () => {
  const saAuth = inject(SuperAdminAuthService);
  const router = inject(Router);

  if (saAuth.isAuthenticated()) {
    return true;
  }
  router.navigate(['/superadmin/login']);
  return false;
};
