import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { AccordionModule } from 'primeng/accordion';
import { TableModule } from 'primeng/table';
import { BadgeModule } from 'primeng/badge';
import { ButtonModule } from 'primeng/button';
import { MessageModule } from 'primeng/message';
import { SkeletonModule } from 'primeng/skeleton';
import { TagModule } from 'primeng/tag';
import { MessageService } from 'primeng/api';
import { ToastModule } from 'primeng/toast';
import { ParentPortalService } from '../../parent-portal.service';

@Component({
  selector: 'app-child-grades',
  standalone: true,
  imports: [
    CommonModule,
    AccordionModule, TableModule, BadgeModule, ButtonModule,
    MessageModule, SkeletonModule, TagModule, ToastModule
  ],
  providers: [MessageService],
  template: `
    <p-toast />

    <div>
      <!-- Page header -->
      <div class="flex align-items-center gap-2 mb-4">
        <i class="pi pi-chart-bar text-primary text-xl"></i>
        <h2 class="text-lg font-bold text-900 m-0">Exam Results</h2>
        @if (childName) {
          <span class="text-500 text-sm">— {{ childName }}</span>
        }
      </div>

      <!-- Loading skeleton -->
      @if (loading) {
        <div class="flex flex-column gap-3">
          @for (n of [1, 2, 3]; track n) {
            <p-skeleton height="4rem" borderRadius="8px" />
          }
        </div>
      }

      <!-- Empty state -->
      @if (!loading && exams.length === 0) {
        <p-message
          severity="info"
          text="No exam results available yet."
          styleClass="w-full"
        />
      }

      <!-- Exams accordion -->
      @if (!loading && exams.length > 0) {
        <p-accordion [multiple]="true">
          @for (exam of exams; track exam.exam_id) {
            <p-accordionTab>
              <ng-template pTemplate="header">
                <div class="flex align-items-center justify-content-between w-full pr-3">
                  <div class="flex flex-column gap-1">
                    <span class="font-semibold text-900 text-sm">{{ exam.exam_name }}</span>
                    <span class="text-xs text-500">{{ exam.term }}</span>
                  </div>
                  <div class="flex align-items-center gap-2">
                    <span class="text-sm text-600">{{ exam.average_percentage | number:'1.1-1' }}%</span>
                    <p-badge
                      [value]="exam.overall_grade ?? 'N/A'"
                      [severity]="getGradeSeverity(exam.overall_grade)"
                    />
                  </div>
                </div>
              </ng-template>

              <!-- Subject results table -->
              <p-table
                [value]="exam.subjects"
                [tableStyle]="{'min-width': '100%'}"
                styleClass="p-datatable-sm"
                responsiveLayout="scroll"
              >
                <ng-template pTemplate="header">
                  <tr>
                    <th>Subject</th>
                    <th class="text-right">Marks</th>
                    <th class="text-right">Max</th>
                    <th class="text-right">%</th>
                    <th class="text-center">Grade</th>
                  </tr>
                </ng-template>
                <ng-template pTemplate="body" let-row>
                  <tr [class]="row.percentage < 40 ? 'row-fail' : ''">
                    <td class="text-sm">{{ row.subject_name }}</td>
                    <td class="text-right text-sm">{{ row.marks_obtained }}</td>
                    <td class="text-right text-sm text-500">{{ row.max_marks }}</td>
                    <td class="text-right text-sm">
                      <span [style.color]="getPctColor(row.percentage)">
                        {{ row.percentage | number:'1.1-1' }}%
                      </span>
                    </td>
                    <td class="text-center">
                      <p-tag
                        [value]="row.grade ?? '-'"
                        [severity]="getGradeTagSeverity(row.grade)"
                      />
                    </td>
                  </tr>
                </ng-template>
              </p-table>

              <!-- Download report card -->
              <div class="flex justify-content-end mt-3">
                <p-button
                  label="Download Report Card"
                  icon="pi pi-download"
                  size="small"
                  [outlined]="true"
                  [loading]="downloadingExamId === exam.exam_id"
                  (onClick)="downloadReportCard(exam.exam_id)"
                />
              </div>
            </p-accordionTab>
          }
        </p-accordion>
      }
    </div>

    <style>
      .row-fail td { color: #ef4444 !important; }
    </style>
  `
})
export class ChildGradesComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private portalService = inject(ParentPortalService);
  private toast = inject(MessageService);

  childId = 0;
  childName = '';
  loading = false;
  downloadingExamId: number | null = null;
  exams: any[] = [];

  ngOnInit(): void {
    this.childId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadGrades();
  }

  loadGrades(): void {
    this.loading = true;
    this.portalService.getChildGrades(this.childId).subscribe({
      next: (res) => {
        this.exams = res.data?.exams ?? [];
        if (res.data?.student_name) this.childName = res.data.student_name;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load grades.' });
      }
    });
  }

  downloadReportCard(examId: number): void {
    this.downloadingExamId = examId;
    this.portalService.downloadReportCard(this.childId, examId).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `report-card-${this.childId}-${examId}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
        this.downloadingExamId = null;
      },
      error: () => {
        this.downloadingExamId = null;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to download report card.' });
      }
    });
  }

  getGradeSeverity(grade: string | null | undefined): 'success' | 'warning' | 'danger' | 'info' {
    if (!grade) return 'info';
    const g = grade.toUpperCase();
    if (g === 'A+' || g === 'A') return 'success';
    if (g === 'B+' || g === 'B') return 'info';
    if (g === 'C') return 'warning';
    return 'danger';
  }

  getGradeTagSeverity(grade: string | null | undefined): 'success' | 'warning' | 'danger' | 'info' | 'secondary' {
    return this.getGradeSeverity(grade) as any;
  }

  getPctColor(pct: number): string {
    if (pct >= 75) return '#22c55e';
    if (pct >= 40) return '#f59e0b';
    return '#ef4444';
  }
}
