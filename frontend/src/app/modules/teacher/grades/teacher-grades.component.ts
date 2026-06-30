import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { ToastModule } from 'primeng/toast';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { MessageService } from 'primeng/api';

import { ExamService, Exam, ExamType } from '../../../core/services/exam.service';

/**
 * Teacher · Grades — exam list scoped to teacher accessibility.
 *
 * Teachers may view exams, enter marks and view results (backend allows those),
 * but must NOT create / edit / finalize exams — those are admin-only. So unlike
 * the admin ExamListComponent there is no "New Exam", "Edit" or "Finalize" here;
 * only "Enter Marks" and "Results" navigate into the shared, role-aware pages.
 */
@Component({
  selector: 'app-teacher-grades',
  standalone: true,
  imports: [
    CommonModule, RouterLink, TableModule, ButtonModule,
    TagModule, TooltipModule, ToastModule, ProgressSpinnerModule
  ],
  providers: [MessageService],
  template: `
    <p-toast />

    <div class="card">
      <div class="mb-3">
        <h2 class="text-xl font-bold text-900 m-0">Grades</h2>
        <p class="text-600 text-sm mt-1 mb-0">Enter marks and view results for your exams.</p>
      </div>

      @if (loading) {
        <div class="flex justify-content-center align-items-center py-6">
          <p-progressSpinner strokeWidth="4" />
        </div>
      }

      @if (!loading) {
        <p-table
          [value]="exams"
          [rows]="20"
          [paginator]="true"
          [rowsPerPageOptions]="[10, 20, 50]"
          dataKey="id"
          responsiveLayout="scroll"
          styleClass="p-datatable-sm"
        >
          <ng-template pTemplate="header">
            <tr>
              <th>Name</th>
              <th>Term</th>
              <th>Type</th>
              <th>Section</th>
              <th>Conducted Date</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </ng-template>

          <ng-template pTemplate="body" let-exam>
            <tr>
              <td>{{ exam.name }}</td>
              <td>{{ exam.term }}</td>
              <td>{{ getExamTypeLabel(exam.exam_type) }}</td>
              <td>{{ exam.section_id }}</td>
              <td>{{ exam.conducted_date ?? '—' }}</td>
              <td>
                <p-tag
                  [value]="exam.is_active ? 'Active' : 'Inactive'"
                  [severity]="exam.is_active ? 'success' : 'secondary'"
                />
              </td>
              <td class="flex gap-2 align-items-center">
                <p-button
                  label="Enter Marks"
                  icon="pi pi-file-edit"
                  size="small"
                  severity="info"
                  [text]="true"
                  [routerLink]="['/teacher/grades', exam.id, 'marks']"
                  pTooltip="Enter Marks"
                />
                <p-button
                  label="Results"
                  icon="pi pi-chart-bar"
                  size="small"
                  severity="success"
                  [text]="true"
                  [routerLink]="['/teacher/grades', exam.id, 'results']"
                  pTooltip="View Class Results"
                />
              </td>
            </tr>
          </ng-template>

          <ng-template pTemplate="emptymessage">
            <tr>
              <td colspan="7" class="text-center py-4 text-color-secondary">No exams found.</td>
            </tr>
          </ng-template>
        </p-table>
      }
    </div>
  `
})
export class TeacherGradesComponent implements OnInit {
  private examService = inject(ExamService);
  private toast = inject(MessageService);

  exams: Exam[] = [];
  loading = false;

  ngOnInit(): void {
    this.loadExams();
  }

  loadExams(): void {
    this.loading = true;
    this.examService.getExams().subscribe({
      next: (res) => {
        this.exams = res.data.exams ?? [];
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load exams.' });
      }
    });
  }

  getExamTypeLabel(type: ExamType): string {
    const map: Record<ExamType, string> = {
      midterm: 'Midterm',
      final: 'Final',
      unit_test: 'Unit Test',
      practical: 'Practical'
    };
    return map[type] ?? type;
  }
}
