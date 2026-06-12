import { Component, inject, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MessageService } from 'primeng/api';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { SkeletonModule } from 'primeng/skeleton';
import { ToastModule } from 'primeng/toast';
import { SchoolsService, School } from '../../../core/services/schools.service';
import { SuperAdminAuthService } from '../../../core/services/superadmin-auth.service';

@Component({
  selector: 'app-sa-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    CardModule,
    ButtonModule,
    TagModule,
    SkeletonModule,
    ToastModule
  ],
  providers: [MessageService],
  templateUrl: './sa-dashboard.component.html'
})
export class SaDashboardComponent implements OnInit {
  private schoolsService = inject(SchoolsService);
  private toast = inject(MessageService);
  saAuth = inject(SuperAdminAuthService);

  schools = signal<School[]>([]);
  loading = signal(false);

  totalSchools = computed(() => this.schools().length);
  activeSchools = computed(() => this.schools().filter(s => s.is_active).length);
  inactiveSchools = computed(() => this.schools().filter(s => !s.is_active).length);

  get firstName(): string {
    return this.saAuth.superAdmin()?.first_name ?? 'Super Admin';
  }

  ngOnInit(): void {
    this.loadSchools();
  }

  loadSchools(): void {
    this.loading.set(true);
    this.schoolsService.getSchools(1, 100).subscribe({
      next: (res) => {
        this.schools.set(res.data.schools);
        this.loading.set(false);
      },
      error: () => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load schools' });
        this.loading.set(false);
      }
    });
  }
}
