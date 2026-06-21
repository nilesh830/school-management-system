import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { AvatarModule } from 'primeng/avatar';
import { MenuModule } from 'primeng/menu';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-admin-layout',
  standalone: true,
  imports: [
    CommonModule, RouterOutlet, RouterLink, RouterLinkActive,
    ButtonModule, AvatarModule, MenuModule
  ],
  templateUrl: './admin-layout.component.html',
  styleUrl: './admin-layout.component.scss'
})
export class AdminLayoutComponent {
  auth = inject(AuthService);

  navItems = [
    { label: 'Dashboard', icon: 'pi-home', route: '/admin/dashboard' },
    { label: 'Create User', icon: 'pi-user-plus', route: '/admin/users/new' },
    { label: 'Students', icon: 'pi-graduation-cap', route: '/admin/students' },
    { label: 'Teachers', icon: 'pi-id-card', route: '/admin/teachers' },
    { label: 'Classes', icon: 'pi-building', route: '/admin/classes' },
    { label: 'Subjects', icon: 'pi-book', route: '/admin/subjects' },
    { label: 'Timetable', icon: 'pi-calendar', route: '/admin/timetable' },
    { label: 'Attendance', icon: 'pi-calendar-clock', route: '/admin/attendance' },
    { label: 'Exams', icon: 'pi-file-edit', route: '/admin/exams' },
    { label: 'Fees', icon: 'pi-indian-rupee', route: '/admin/fees' },
    { label: 'Fee Defaulters', icon: 'pi-exclamation-triangle', route: '/admin/fees/defaulters' },
    { label: 'Reports', icon: 'pi-chart-bar', route: '/admin/reports' },
  ];

  profileMenuItems = [
    { label: 'My Profile', icon: 'pi pi-user', routerLink: '/admin/profile' },
    { separator: true },
    { label: 'Sign Out', icon: 'pi pi-sign-out', command: () => this.auth.logout() }
  ];

  get initials(): string {
    const u = this.auth.currentUser();
    return u ? `${u.first_name[0]}${u.last_name[0]}`.toUpperCase() : 'A';
  }

  get fullName(): string {
    const u = this.auth.currentUser();
    return u ? `${u.first_name} ${u.last_name}` : '';
  }
}
