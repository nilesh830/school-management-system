import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { AvatarModule } from 'primeng/avatar';
import { MenuModule } from 'primeng/menu';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-student-layout',
  standalone: true,
  imports: [
    CommonModule, RouterOutlet, RouterLink, RouterLinkActive,
    ButtonModule, AvatarModule, MenuModule
  ],
  templateUrl: './student-layout.component.html',
  styleUrl: './student-layout.component.scss'
})
export class StudentLayoutComponent {
  auth = inject(AuthService);

  navItems = [
    { label: 'Dashboard', icon: 'pi-home', route: '/student/dashboard' },
    { label: 'My Grades', icon: 'pi-star', route: '/student/grades' },
    { label: 'Attendance', icon: 'pi-calendar', route: '/student/attendance' },
    { label: 'Timetable', icon: 'pi-calendar-clock', route: '/student/timetable' },
    { label: 'Library', icon: 'pi-book', route: '/student/library' },
  ];

  profileMenuItems = [
    { label: 'My Profile', icon: 'pi pi-user', routerLink: '/student/profile' },
    { separator: true },
    { label: 'Sign Out', icon: 'pi pi-sign-out', command: () => this.auth.logout() }
  ];

  get initials(): string {
    const u = this.auth.currentUser();
    return u ? `${u.first_name[0]}${u.last_name[0]}`.toUpperCase() : 'S';
  }

  get fullName(): string {
    const u = this.auth.currentUser();
    return u ? `${u.first_name} ${u.last_name}` : '';
  }
}
