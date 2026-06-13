import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { AvatarModule } from 'primeng/avatar';
import { MenuModule } from 'primeng/menu';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-teacher-layout',
  standalone: true,
  imports: [
    CommonModule, RouterOutlet, RouterLink, RouterLinkActive,
    ButtonModule, AvatarModule, MenuModule
  ],
  templateUrl: './teacher-layout.component.html',
  styleUrl: './teacher-layout.component.scss'
})
export class TeacherLayoutComponent {
  auth = inject(AuthService);

  navItems = [
    { label: 'Dashboard', icon: 'pi-home', route: '/teacher/dashboard' },
    { label: 'My Students', icon: 'pi-graduation-cap', route: '/teacher/students' },
    { label: 'Attendance', icon: 'pi-calendar-clock', route: '/teacher/attendance' },
    { label: 'Grades', icon: 'pi-pencil', route: '/teacher/grades' },
    { label: 'Leave Requests', icon: 'pi-file-check', route: '/teacher/leave-requests' },
    { label: 'Timetable', icon: 'pi-calendar-clock', route: '/teacher/timetable' },
  ];

  profileMenuItems = [
    { label: 'My Profile', icon: 'pi pi-user', routerLink: '/teacher/profile' },
    { separator: true },
    { label: 'Sign Out', icon: 'pi pi-sign-out', command: () => this.auth.logout() }
  ];

  get initials(): string {
    const u = this.auth.currentUser();
    return u ? `${u.first_name[0]}${u.last_name[0]}`.toUpperCase() : 'T';
  }

  get fullName(): string {
    const u = this.auth.currentUser();
    return u ? `${u.first_name} ${u.last_name}` : '';
  }
}
