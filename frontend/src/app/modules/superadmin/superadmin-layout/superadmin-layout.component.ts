import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { AvatarModule } from 'primeng/avatar';
import { MenuModule } from 'primeng/menu';
import { SuperAdminAuthService } from '../../../core/services/superadmin-auth.service';

@Component({
  selector: 'app-superadmin-layout',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    ButtonModule,
    AvatarModule,
    MenuModule
  ],
  templateUrl: './superadmin-layout.component.html',
  styleUrl: './superadmin-layout.component.scss'
})
export class SuperadminLayoutComponent {
  saAuth = inject(SuperAdminAuthService);

  navItems = [
    { label: 'Dashboard', icon: 'pi-home', route: '/superadmin/dashboard' },
    { label: 'Schools', icon: 'pi-building', route: '/superadmin/schools' }
  ];

  get initials(): string {
    const u = this.saAuth.superAdmin();
    return u ? `${u.first_name[0]}${u.last_name[0]}`.toUpperCase() : 'SA';
  }

  get fullName(): string {
    const u = this.saAuth.superAdmin();
    return u ? `${u.first_name} ${u.last_name}` : '';
  }
}
