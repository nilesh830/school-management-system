import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, ActivatedRoute } from '@angular/router';
import { MessageService } from 'primeng/api';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { CardModule } from 'primeng/card';
import { ToolbarModule } from 'primeng/toolbar';
import { ChartModule } from 'primeng/chart';
import { ToastModule } from 'primeng/toast';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { ExamService } from '../../../../core/services/exam.service';

interface StudentSummary {
  student_id: number;
  student_name: string;
  overall_gpa: number;
  overall_percentage: number;
  overall_grade: string;
  total_marks_obtained: number;
  total_max_marks: number;
}

@Component({
  selector: 'app-class-results',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    TableModule,
    ButtonModule,
    TagModule,
    CardModule,
    ToolbarModule,
    ChartModule,
    ToastModule,
    ProgressSpinnerModule,
  ],
  providers: [MessageService],
  templateUrl: './class-results.component.html',
})
export class ClassResultsComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private examService = inject(ExamService);
  private messageService = inject(MessageService);

  examId = 0;
  examName = '';
  loading = true;
  results: StudentSummary[] = [];
  chartData: any = {};
  chartOptions: any = {};

  get passCount(): number {
    return this.results.filter(r => r.overall_percentage >= 35).length;
  }

  get failCount(): number {
    return this.results.filter(r => r.overall_percentage < 35).length;
  }

  get classAvgPercentage(): number {
    if (!this.results.length) return 0;
    return this.results.reduce((s, r) => s + r.overall_percentage, 0) / this.results.length;
  }

  get classAvgGpa(): number {
    if (!this.results.length) return 0;
    return this.results.reduce((s, r) => s + r.overall_gpa, 0) / this.results.length;
  }

  ngOnInit(): void {
    this.examId = Number(this.route.snapshot.paramMap.get('examId'));
    this.loadExam();
    this.loadResults();
  }

  private loadExam(): void {
    this.examService.getExam(this.examId).subscribe({
      next: (res: any) => {
        this.examName = res?.data?.name ?? `Exam #${this.examId}`;
      },
      error: () => {},
    });
  }

  private loadResults(): void {
    this.loading = true;
    // getResults(examId, studentId?) — calling without studentId returns all students
    this.examService.getResults(this.examId).subscribe({
      next: (res: any) => {
        this.results = Array.isArray(res?.data) ? res.data : [];
        this.buildChartData();
        this.loading = false;
      },
      error: () => {
        this.messageService.add({
          severity: 'error',
          summary: 'Error',
          detail: 'Failed to load results.',
        });
        this.loading = false;
      },
    });
  }

  private buildChartData(): void {
    const gradeOrder = ['A+', 'A', 'B', 'C', 'D', 'E', 'F'];
    const counts: Record<string, number> = {};
    gradeOrder.forEach(g => (counts[g] = 0));
    this.results.forEach(r => {
      if (r.overall_grade in counts) counts[r.overall_grade]++;
    });
    this.chartData = {
      labels: gradeOrder,
      datasets: [
        {
          label: 'Students',
          data: gradeOrder.map(g => counts[g]),
          backgroundColor: [
            '#22c55e',
            '#4ade80',
            '#60a5fa',
            '#facc15',
            '#fb923c',
            '#f87171',
            '#ef4444',
          ],
        },
      ],
    };
    this.chartOptions = {
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
    };
  }

  getGradeSeverity(grade: string): 'success' | 'info' | 'warning' | 'danger' | undefined {
    if (['A+', 'A'].includes(grade)) return 'success';
    if (grade === 'B') return 'info';
    if (['C', 'D'].includes(grade)) return 'warning';
    return 'danger';
  }
}
