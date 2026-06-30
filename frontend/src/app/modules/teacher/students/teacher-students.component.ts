import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TableModule, TableLazyLoadEvent } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { DialogModule } from 'primeng/dialog';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { ToastModule } from 'primeng/toast';
import { SkeletonModule } from 'primeng/skeleton';
import { MessageService } from 'primeng/api';

import { StudentService, Student } from '../../../core/services/student.service';

/**
 * Teacher · My Students — READ-ONLY roster.
 *
 * Teachers may view students (backend: GET /students is admin+teacher) but must
 * NOT enroll, edit, transfer or deactivate them — those are admin-only. This
 * component therefore exposes a view-only list + detail dialog with no mutating
 * actions, unlike the admin StudentListComponent.
 */
@Component({
  selector: 'app-teacher-students',
  standalone: true,
  imports: [
    CommonModule, TableModule, ButtonModule, CardModule,
    DialogModule, TagModule, TooltipModule, ToastModule, SkeletonModule
  ],
  providers: [MessageService],
  template: `
    <p-toast />

    <p-card>
      <div class="mb-3">
        <h2 class="text-xl font-bold text-900 m-0">My Students</h2>
        <p class="text-600 text-sm mt-1 mb-0">View student records (read-only).</p>
      </div>

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
            <th>Admission No</th>
            <th>Name</th>
            <th>Gender</th>
            <th>Class</th>
            <th>Phone</th>
            <th class="text-center">View</th>
          </tr>
        </ng-template>

        <ng-template pTemplate="body" let-student>
          <tr>
            <td><span class="font-medium text-primary">{{ student.admission_no }}</span></td>
            <td>{{ student.first_name }} {{ student.last_name }}</td>
            <td>{{ student.gender }}</td>
            <td>{{ student.class_name || '—' }}</td>
            <td>{{ student.phone || '—' }}</td>
            <td class="text-center">
              <p-button
                icon="pi pi-eye"
                [rounded]="true"
                [text]="true"
                severity="info"
                pTooltip="View details"
                size="small"
                (onClick)="openDetail(student)"
              />
            </td>
          </tr>
        </ng-template>

        <ng-template pTemplate="emptymessage">
          <tr>
            <td colspan="6" class="text-center text-600 py-4">No students found.</td>
          </tr>
        </ng-template>
      </p-table>
    </p-card>

    <!-- Read-only detail dialog -->
    <p-dialog
      header="Student Details"
      [(visible)]="detailVisible"
      [modal]="true"
      [style]="{ width: '95vw', maxWidth: '520px' }"
      [draggable]="false"
      [resizable]="false"
    >
      @if (detailLoading) {
        <div class="flex flex-column gap-2">
          @for (n of [1,2,3,4,5]; track n) {
            <p-skeleton height="2rem" borderRadius="6px" />
          }
        </div>
      }
      @if (!detailLoading && selected) {
        <div class="flex align-items-center gap-2 mb-3">
          <span class="text-lg font-bold text-900">{{ selected.first_name }} {{ selected.last_name }}</span>
          <p-tag [value]="(selected.status | titlecase) || 'Active'" severity="info" />
        </div>
        <div class="grid">
          <div class="col-12 md:col-6 field">
            <label class="font-semibold text-sm text-600 block mb-1">Admission No</label>
            <span class="text-900">{{ selected.admission_no }}</span>
          </div>
          <div class="col-12 md:col-6 field">
            <label class="font-semibold text-sm text-600 block mb-1">Class</label>
            <span class="text-900">{{ selected.class_name || '—' }}</span>
          </div>
          <div class="col-12 md:col-6 field">
            <label class="font-semibold text-sm text-600 block mb-1">Date of Birth</label>
            <span class="text-900">{{ selected.date_of_birth || '—' }}</span>
          </div>
          <div class="col-12 md:col-6 field">
            <label class="font-semibold text-sm text-600 block mb-1">Gender</label>
            <span class="text-900">{{ selected.gender }}</span>
          </div>
          <div class="col-12 md:col-6 field">
            <label class="font-semibold text-sm text-600 block mb-1">Blood Group</label>
            <span class="text-900">{{ selected.blood_group || '—' }}</span>
          </div>
          <div class="col-12 md:col-6 field">
            <label class="font-semibold text-sm text-600 block mb-1">Phone</label>
            <span class="text-900">{{ selected.phone || '—' }}</span>
          </div>
          <div class="col-12 field">
            <label class="font-semibold text-sm text-600 block mb-1">Address</label>
            <span class="text-900" style="white-space: pre-line;">{{ selected.address || '—' }}</span>
          </div>
        </div>
      }
    </p-dialog>
  `
})
export class TeacherStudentsComponent implements OnInit {
  private studentService = inject(StudentService);
  private toast = inject(MessageService);

  students: Student[] = [];
  totalRecords = 0;
  rows = 20;
  loading = false;

  detailVisible = false;
  detailLoading = false;
  selected: Student | null = null;

  ngOnInit(): void {}

  loadStudents(event: TableLazyLoadEvent): void {
    this.loading = true;
    const first = event.first ?? 0;
    const perPage = event.rows ?? this.rows;
    const page = Math.floor(first / perPage) + 1;

    this.studentService.getStudents(page, perPage).subscribe({
      next: (res) => {
        this.students = res.data.students ?? [];
        this.totalRecords = res.data.meta?.total ?? this.students.length;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load students.' });
      }
    });
  }

  openDetail(student: Student): void {
    this.detailVisible = true;
    this.detailLoading = true;
    this.selected = student;
    this.studentService.getStudentById(student.id).subscribe({
      next: (res) => {
        this.selected = res.data;
        this.detailLoading = false;
      },
      error: () => {
        this.detailLoading = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load student details.' });
      }
    });
  }
}
