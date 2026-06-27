import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { AvatarModule } from 'primeng/avatar';
import { MenuModule } from 'primeng/menu';
import { TabMenuModule } from 'primeng/tabmenu';
import { BadgeModule } from 'primeng/badge';
import { AuthService } from '../../../core/services/auth.service';
import { ParentPortalService } from '../parent-portal.service';
import { NotificationBellComponent } from '../notifications/notification-bell.component';

@Component({
  selector: 'app-parent-layout',
  standalone: true,
  imports: [
    CommonModule, RouterOutlet, RouterLink, RouterLinkActive,
    ButtonModule, AvatarModule, MenuModule, TabMenuModule, BadgeModule,
    NotificationBellComponent
  ],
  templateUrl: './parent-layout.component.html',
  styleUrl: './parent-layout.component.scss'
})
export class ParentLayoutComponent implements OnInit {
  auth = inject(AuthService);
  private portalService = inject(ParentPortalService);

  noticeCount = 0;

  ngOnInit(): void {
    // Non-blocking: fetch notice count for the nav badge.
    this.portalService.getNotices().subscribe({
      next: (res) => {
        const notices = res?.data?.notices ?? res?.data ?? [];
        this.noticeCount = Array.isArray(notices) ? notices.length : 0;
      },
      error: () => {
        this.noticeCount = 0;
      }
    });
  }

  navItems = [
    { label: 'Home', icon: 'pi pi-home', route: '/parent/dashboard' },
    { label: 'Children', icon: 'pi pi-users', route: '/parent/children' },
    { label: 'Leave', icon: 'pi pi-file-check', route: '/parent/leave-applications' },
    { label: 'Notices', icon: 'pi pi-bell', route: '/parent/notices' },
    { label: 'Messages', icon: 'pi pi-envelope', route: '/parent/messages' },
  ];

  profileMenuItems = [
    { label: 'My Profile', icon: 'pi pi-user', routerLink: '/parent/profile' },
    { separator: true },
    { label: 'Sign Out', icon: 'pi pi-sign-out', command: () => this.auth.logout() }
  ];

  get initials(): string {
    const u = this.auth.currentUser();
    return u ? `${u.first_name[0]}${u.last_name[0]}`.toUpperCase() : 'P';
  }

  get fullName(): string {
    const u = this.auth.currentUser();
    return u ? `${u.first_name} ${u.last_name}` : '';
  }
}
