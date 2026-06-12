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
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { debounceTime, Subject } from 'rxjs';

import { TeacherService, Teacher } from '../../../../core/services/teacher.service';

@Component({
  selector: 'app-teacher-list',
  standalone: true,
  imports: [
    CommonModule, RouterLink, FormsModule,
    TableModule, ButtonModule, CardModule, ToolbarModule,
    TagModule, ToastModule, InputTextModule, ConfirmDialogModule
  ],
  providers: [MessageService, ConfirmationService],
  template: `
    <p-toast position="top-right" />
    <p-confirmDialog />

    <p-card>
      <p-toolbar styleClass="mb-4">
        <ng-template pTemplate="left">
          <h2 class="text-xl font-bold text-900 m-0">Teachers</h2>
        </ng-template>
        <ng-template pTemplate="right">
          <div class="flex gap-2 align-items-center">
            <span class="p-input-icon-left">
              <i class="pi pi-search"></i>
              <input
                pInputText
                type="text"
                [(ngModel)]="searchTerm"
                (ngModelChange)="onSearchChange()"
                placeholder="Search teachers…"
                class="w-16rem"
              />
            </span>
            <p-button label="Add Teacher" icon="pi pi-plus" routerLink="/admin/teachers/new" />
          </div>
        </ng-template>
      </p-toolbar>

      <p-table
        [value]="teachers"
        [lazy]="true"
        (onLazyLoad)="loadTeachers($event)"
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
            <th>Employee ID</th>
            <th>Full Name</th>
            <th>Specialization</th>
            <th>Joining Date</th>
            <th>Phone</th>
            <th>Actions</th>
          </tr>
        </ng-template>

        <ng-template pTemplate="body" let-teacher>
          <tr>
            <td><span class="font-medium text-primary">{{ teacher.employee_id }}</span></td>
            <td>{{ teacher.full_name }}</td>
            <td>{{ teacher.specialization || '—' }}</td>
            <td>{{ teacher.joining_date | date:'mediumDate' }}</td>
            <td>{{ teacher.phone || '—' }}</td>
            <td>
              <div class="flex gap-1">
                <p-button
                  icon="pi pi-eye"
                  [rounded]="true" [text]="true"
                  severity="info" size="small"
                  pTooltip="View"
                  [routerLink]="['/admin/teachers', teacher.id]"
                />
                <p-button
                  icon="pi pi-pencil"
                  [rounded]="true" [text]="true"
                  severity="secondary" size="small"
                  pTooltip="Edit"
                  [routerLink]="['/admin/teachers', teacher.id, 'edit']"
                />
                <p-button
                  icon="pi pi-trash"
                  [rounded]="true" [text]="true"
                  severity="danger" size="small"
                  pTooltip="Delete"
                  (onClick)="confirmDelete(teacher)"
                />
              </div>
            </td>
          </tr>
        </ng-template>

        <ng-template pTemplate="emptymessage">
          <tr>
            <td colspan="6" class="text-center text-600 py-4">
              No teachers found.
              <a routerLink="/admin/teachers/new" class="text-primary ml-1">Add the first teacher.</a>
            </td>
          </tr>
        </ng-template>
      </p-table>
    </p-card>
  `
})
export class TeacherListComponent implements OnInit {
  private teacherService = inject(TeacherService);
  private toast = inject(MessageService);
  private confirm = inject(ConfirmationService);

  teachers: Teacher[] = [];
  totalRecords = 0;
  loading = false;
  rows = 20;
  searchTerm = '';
  private currentPage = 1;
  private searchSubject = new Subject<string>();

  ngOnInit(): void {
    this.searchSubject.pipe(debounceTime(300)).subscribe(() => {
      this.currentPage = 1;
      this.loadTeachers();
    });
    this.loadTeachers();
  }

  onSearchChange(): void {
    this.searchSubject.next(this.searchTerm);
  }

  loadTeachers(event?: any): void {
    this.loading = true;
    const page = event ? Math.floor(event.first / event.rows) + 1 : this.currentPage;
    const perPage = event?.rows ?? this.rows;

    this.teacherService.getTeachers(page, perPage, this.searchTerm).subscribe({
      next: (res) => {
        this.teachers = res.data.teachers;
        this.totalRecords = res.data.meta.total;
        this.loading = false;
      },
      error: () => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load teachers' });
        this.loading = false;
      }
    });
  }

  confirmDelete(teacher: Teacher): void {
    this.confirm.confirm({
      message: `Delete teacher "${teacher.full_name}"? This cannot be undone.`,
      header: 'Confirm Delete',
      icon: 'pi pi-trash',
      acceptButtonStyleClass: 'p-button-danger',
      accept: () => this.deleteTeacher(teacher)
    });
  }

  private deleteTeacher(teacher: Teacher): void {
    this.teacherService.deleteTeacher(teacher.id).subscribe({
      next: () => {
        this.toast.add({ severity: 'success', summary: 'Deleted', detail: `${teacher.full_name} removed` });
        this.loadTeachers();
      },
      error: () => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to delete teacher' });
      }
    });
  }
}
