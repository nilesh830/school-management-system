import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MessageService } from 'primeng/api';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { ToolbarModule } from 'primeng/toolbar';
import { TagModule } from 'primeng/tag';
import { ToastModule } from 'primeng/toast';
import { InputTextModule } from 'primeng/inputtext';

import { StudentService, Student } from '../../../../core/services/student.service';

@Component({
  selector: 'app-student-list',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    TableModule,
    ButtonModule,
    CardModule,
    ToolbarModule,
    TagModule,
    ToastModule,
    InputTextModule
  ],
  providers: [MessageService],
  template: `
    <p-toast position="top-right" />

    <p-card>
      <p-toolbar styleClass="mb-4">
        <ng-template pTemplate="left">
          <h2 class="text-xl font-bold text-900 m-0">Students</h2>
        </ng-template>
        <ng-template pTemplate="right">
          <p-button
            label="Enroll Student"
            icon="pi pi-plus"
            routerLink="/admin/students/new"
          />
        </ng-template>
      </p-toolbar>

      <p-table
        [value]="students"
        [lazy]="true"
        (onLazyLoad)="loadStudents($event)"
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
            <th pSortableColumn="admission_no">Admission No <p-sortIcon field="admission_no" /></th>
            <th pSortableColumn="first_name">Name <p-sortIcon field="first_name" /></th>
            <th>Gender</th>
            <th>Date of Birth</th>
            <th>Phone</th>
            <th>Actions</th>
          </tr>
        </ng-template>

        <ng-template pTemplate="body" let-student>
          <tr>
            <td>
              <span class="font-medium text-primary">{{ student.admission_no }}</span>
            </td>
            <td>{{ student.first_name }} {{ student.last_name }}</td>
            <td>{{ student.gender }}</td>
            <td>{{ student.date_of_birth }}</td>
            <td>{{ student.phone || '—' }}</td>
            <td>
              <p-button
                icon="pi pi-eye"
                [rounded]="true"
                [text]="true"
                severity="info"
                pTooltip="View"
                size="small"
                [routerLink]="['/admin/students', student.id]"
              />
            </td>
          </tr>
        </ng-template>

        <ng-template pTemplate="emptymessage">
          <tr>
            <td colspan="6" class="text-center text-600 py-4">
              No students found.
              <a routerLink="/admin/students/new" class="text-primary ml-1">Enroll your first student.</a>
            </td>
          </tr>
        </ng-template>
      </p-table>
    </p-card>
  `
})
export class StudentListComponent implements OnInit {
  private studentService = inject(StudentService);
  private toast = inject(MessageService);

  students: Student[] = [];
  totalRecords = 0;
  loading = false;
  rows = 20;

  ngOnInit(): void {
    this.loadStudents();
  }

  loadStudents(event?: any): void {
    this.loading = true;
    const page = event ? Math.floor(event.first / event.rows) + 1 : 1;
    const perPage = event?.rows ?? this.rows;

    this.studentService.getStudents(page, perPage).subscribe({
      next: (res) => {
        this.students = res.data.students;
        this.totalRecords = res.data.meta.total;
        this.loading = false;
      },
      error: () => {
        this.toast.add({
          severity: 'error',
          summary: 'Error',
          detail: 'Failed to load students'
        });
        this.loading = false;
      }
    });
  }
}
