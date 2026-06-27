import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MessageService, ConfirmationService } from 'primeng/api';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { ToolbarModule } from 'primeng/toolbar';
import { TagModule } from 'primeng/tag';
import { ToastModule } from 'primeng/toast';
import { InputTextModule } from 'primeng/inputtext';
import { DropdownModule } from 'primeng/dropdown';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { debounceTime, forkJoin, Subject } from 'rxjs';

import { UsersService } from '../../../../core/services/users.service';
import { AuthService } from '../../../../core/services/auth.service';
import { User } from '../../../../core/models/user.model';

interface RoleCount {
  label: string;
  role: string;
  count: number;
  icon: string;
  color: string;
}

@Component({
  selector: 'app-user-list',
  standalone: true,
  imports: [
    CommonModule, RouterLink, FormsModule,
    TableModule, ButtonModule, CardModule, ToolbarModule,
    TagModule, ToastModule, InputTextModule, DropdownModule, ConfirmDialogModule
  ],
  providers: [MessageService, ConfirmationService],
  template: `
    <p-toast position="top-right" />
    <p-confirmDialog />

    <!-- Summary cards -->
    <div class="grid mb-3">
      <div class="col-6 md:col-2">
        <div class="surface-card border-round p-3 text-center border-1 surface-border">
          <div class="text-2xl font-bold text-900">{{ totalUsers }}</div>
          <div class="text-600 text-sm mt-1"><i class="pi pi-users mr-1"></i>Total</div>
        </div>
      </div>
      @for (rc of roleCounts; track rc.role) {
        <div class="col-6 md:col-2">
          <div class="surface-card border-round p-3 text-center border-1 surface-border">
            <div class="text-2xl font-bold" [style.color]="rc.color">{{ rc.count }}</div>
            <div class="text-600 text-sm mt-1"><i class="pi {{ rc.icon }} mr-1"></i>{{ rc.label }}</div>
          </div>
        </div>
      }
    </div>

    <p-card>
      <p-toolbar styleClass="mb-4">
        <ng-template pTemplate="left">
          <h2 class="text-xl font-bold text-900 m-0">Users</h2>
        </ng-template>
        <ng-template pTemplate="right">
          <div class="flex flex-wrap gap-2 align-items-center">
            <span class="p-input-icon-left">
              <i class="pi pi-search"></i>
              <input
                pInputText
                type="text"
                [(ngModel)]="searchTerm"
                (ngModelChange)="onSearchChange()"
                placeholder="Search name or email…"
                class="w-16rem"
              />
            </span>
            <p-dropdown
              [options]="roleOptions"
              [(ngModel)]="roleFilter"
              (onChange)="onFilterChange()"
              optionLabel="label"
              optionValue="value"
              placeholder="All roles"
              [showClear]="true"
              styleClass="w-10rem"
              appendTo="body"
            />
            <p-dropdown
              [options]="statusOptions"
              [(ngModel)]="statusFilter"
              (onChange)="onFilterChange()"
              optionLabel="label"
              optionValue="value"
              placeholder="All status"
              [showClear]="true"
              styleClass="w-9rem"
              appendTo="body"
            />
            <p-button label="Create User" icon="pi pi-user-plus" routerLink="/admin/users/new" />
          </div>
        </ng-template>
      </p-toolbar>

      <p-table
        [value]="users"
        [lazy]="true"
        (onLazyLoad)="loadUsers($event)"
        [totalRecords]="totalRecords"
        [rows]="rows"
        [paginator]="true"
        [loading]="loading"
        dataKey="id"
        responsiveLayout="scroll"
        [rowHover]="true"
        styleClass="p-datatable-sm"
      >
        <ng-template pTemplate="header">
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Role</th>
            <th>Status</th>
            <th>Created</th>
            <th>Last Login</th>
            <th>Actions</th>
          </tr>
        </ng-template>

        <ng-template pTemplate="body" let-user>
          <tr>
            <td class="font-medium text-900">{{ user.full_name || (user.first_name + ' ' + user.last_name) }}</td>
            <td>{{ user.email }}</td>
            <td>
              <p-tag [value]="user.role | titlecase" [severity]="roleSeverity(user.role)" />
            </td>
            <td>
              <p-tag
                [value]="user.is_active ? 'Active' : 'Inactive'"
                [severity]="user.is_active ? 'success' : 'danger'"
              />
            </td>
            <td>{{ user.created_at ? (user.created_at | date:'mediumDate') : '—' }}</td>
            <td>{{ user.last_login ? (user.last_login | date:'short') : 'Never' }}</td>
            <td>
              <div class="flex gap-1">
                <p-button
                  icon="pi pi-pencil"
                  [rounded]="true" [text]="true"
                  severity="secondary" size="small"
                  pTooltip="Edit"
                  [routerLink]="['/admin/users', user.id, 'edit']"
                />
                @if (user.is_active) {
                  <p-button
                    icon="pi pi-ban"
                    [rounded]="true" [text]="true"
                    severity="danger" size="small"
                    pTooltip="Deactivate"
                    [disabled]="user.id === currentUserId"
                    (onClick)="confirmDeactivate(user)"
                  />
                } @else {
                  <p-button
                    icon="pi pi-check-circle"
                    [rounded]="true" [text]="true"
                    severity="success" size="small"
                    pTooltip="Reactivate"
                    (onClick)="confirmActivate(user)"
                  />
                }
              </div>
            </td>
          </tr>
        </ng-template>

        <ng-template pTemplate="emptymessage">
          <tr>
            <td colspan="7" class="text-center text-600 py-4">
              No users found.
              <a routerLink="/admin/users/new" class="text-primary ml-1">Create the first user.</a>
            </td>
          </tr>
        </ng-template>
      </p-table>
    </p-card>
  `
})
export class UserListComponent implements OnInit {
  private usersService = inject(UsersService);
  private auth = inject(AuthService);
  private toast = inject(MessageService);
  private confirm = inject(ConfirmationService);

  users: User[] = [];
  totalRecords = 0;
  totalUsers = 0;
  loading = false;
  rows = 20;

  searchTerm = '';
  roleFilter: string | null = null;
  statusFilter: boolean | null = null;

  currentUserId = this.auth.currentUser()?.id ?? -1;

  roleOptions = [
    { label: 'Administrator', value: 'admin' },
    { label: 'Teacher', value: 'teacher' },
    { label: 'Student', value: 'student' },
    { label: 'Parent', value: 'parent' }
  ];

  statusOptions = [
    { label: 'Active', value: true },
    { label: 'Inactive', value: false }
  ];

  roleCounts: RoleCount[] = [
    { label: 'Admins', role: 'admin', count: 0, icon: 'pi-shield', color: '#ef4444' },
    { label: 'Teachers', role: 'teacher', count: 0, icon: 'pi-id-card', color: '#22c55e' },
    { label: 'Students', role: 'student', count: 0, icon: 'pi-graduation-cap', color: '#3b82f6' },
    { label: 'Parents', role: 'parent', count: 0, icon: 'pi-users', color: '#f59e0b' }
  ];

  private currentPage = 1;
  private searchSubject = new Subject<string>();

  ngOnInit(): void {
    this.searchSubject.pipe(debounceTime(300)).subscribe(() => {
      this.currentPage = 1;
      this.loadUsers();
    });
    this.loadUsers();
    this.loadCounts();
  }

  onSearchChange(): void {
    this.searchSubject.next(this.searchTerm);
  }

  onFilterChange(): void {
    this.currentPage = 1;
    this.loadUsers();
  }

  loadUsers(event?: any): void {
    this.loading = true;
    const page = event ? Math.floor(event.first / event.rows) + 1 : this.currentPage;
    const perPage = event?.rows ?? this.rows;

    this.usersService
      .getUsers(page, perPage, this.roleFilter, this.searchTerm, this.statusFilter)
      .subscribe({
        next: (res) => {
          this.users = res.data.users;
          this.totalRecords = res.data.meta.total;
          this.loading = false;
        },
        error: () => {
          this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load users' });
          this.loading = false;
        }
      });
  }

  /** Per-role totals for the summary cards (one lightweight count call each). */
  loadCounts(): void {
    forkJoin({
      total: this.usersService.getUsers(1, 1),
      admin: this.usersService.getUsers(1, 1, 'admin'),
      teacher: this.usersService.getUsers(1, 1, 'teacher'),
      student: this.usersService.getUsers(1, 1, 'student'),
      parent: this.usersService.getUsers(1, 1, 'parent')
    }).subscribe({
      next: (res) => {
        this.totalUsers = res.total.data.meta.total;
        const byRole: Record<string, number> = {
          admin: res.admin.data.meta.total,
          teacher: res.teacher.data.meta.total,
          student: res.student.data.meta.total,
          parent: res.parent.data.meta.total
        };
        this.roleCounts.forEach((rc) => (rc.count = byRole[rc.role] ?? 0));
      },
      error: () => {
        /* counts are non-critical; ignore failures */
      }
    });
  }

  roleSeverity(role: string): 'success' | 'secondary' | 'info' | 'warning' | 'danger' | 'contrast' {
    switch (role) {
      case 'admin': return 'danger';
      case 'teacher': return 'success';
      case 'student': return 'info';
      case 'parent': return 'warning';
      default: return 'secondary';
    }
  }

  confirmDeactivate(user: User): void {
    this.confirm.confirm({
      message: `Deactivate ${user.full_name || user.email}? They will no longer be able to sign in.`,
      header: 'Confirm Deactivation',
      icon: 'pi pi-exclamation-triangle',
      acceptButtonStyleClass: 'p-button-danger',
      accept: () => this.deactivate(user)
    });
  }

  private deactivate(user: User): void {
    this.usersService.deactivateUser(user.id).subscribe({
      next: () => {
        this.toast.add({ severity: 'success', summary: 'Deactivated', detail: `${user.email} deactivated` });
        this.loadUsers();
        this.loadCounts();
      },
      error: (err) => {
        this.toast.add({
          severity: 'error',
          summary: 'Error',
          detail: err?.error?.message || 'Failed to deactivate user'
        });
      }
    });
  }

  confirmActivate(user: User): void {
    this.confirm.confirm({
      message: `Reactivate ${user.full_name || user.email}? They will be able to sign in again.`,
      header: 'Confirm Reactivation',
      icon: 'pi pi-check-circle',
      accept: () => this.activate(user)
    });
  }

  private activate(user: User): void {
    this.usersService.activateUser(user.id).subscribe({
      next: () => {
        this.toast.add({ severity: 'success', summary: 'Reactivated', detail: `${user.email} reactivated` });
        this.loadUsers();
        this.loadCounts();
      },
      error: (err) => {
        this.toast.add({
          severity: 'error',
          summary: 'Error',
          detail: err?.error?.message || 'Failed to reactivate user'
        });
      }
    });
  }
}
