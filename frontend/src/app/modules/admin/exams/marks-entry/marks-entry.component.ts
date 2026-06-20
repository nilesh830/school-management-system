import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { MessageService } from 'primeng/api';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { DropdownModule } from 'primeng/dropdown';
import { InputNumberModule } from 'primeng/inputnumber';
import { ToastModule } from 'primeng/toast';
import { CardModule } from 'primeng/card';
import { ToolbarModule } from 'primeng/toolbar';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { TagModule } from 'primeng/tag';
import { forkJoin } from 'rxjs';

import { ExamService, Exam } from '../../../../core/services/exam.service';
import { StudentService, Student } from '../../../../core/services/student.service';
import { ClassesService, Subject } from '../../../../core/services/classes.service';

interface SavedResult {
  grade: string;
  gpa: number;
}

@Component({
  selector: 'app-marks-entry',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormsModule,
    TableModule,
    ButtonModule,
    DropdownModule,
    InputNumberModule,
    ToastModule,
    CardModule,
    ToolbarModule,
    ProgressSpinnerModule,
    TagModule,
  ],
  providers: [MessageService],
  templateUrl: './marks-entry.component.html',
})
export class MarksEntryComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private examService = inject(ExamService);
  private studentService = inject(StudentService);
  private classesService = inject(ClassesService);
  private toast = inject(MessageService);
  private fb = inject(FormBuilder);

  exam: Exam | null = null;
  students: Student[] = [];
  subjects: Subject[] = [];
  subjectOptions: { label: string; value: number }[] = [];

  selectedSubjectId: number | null = null;
  /** Plain object — keyed by student id, value is marks entered (null = not entered). */
  marksValues: Record<number, number | null> = {};
  /** Populated after a successful save — keyed by student id. */
  savedResults: Record<number, SavedResult> = {};

  loading = false;
  saving = false;
  examId = 0;

  form: FormGroup = this.fb.group({
    subject_id: [null, Validators.required],
  });

  ngOnInit(): void {
    this.examId = Number(this.route.snapshot.paramMap.get('examId'));
    this.loadData();
  }

  private loadData(): void {
    this.loading = true;
    this.examService.getExam(this.examId).subscribe({
      next: (examRes) => {
        this.exam = examRes.data;
        const sectionId = this.exam.section_id;

        forkJoin([
          this.studentService.getStudentsBySection(sectionId),
          this.classesService.getSubjects(1, 100),
        ]).subscribe({
          next: ([studentsRes, subjectsRes]) => {
            this.students = studentsRes.data.students ?? [];
            this.subjects = subjectsRes.data.subjects ?? [];
            this.subjectOptions = this.subjects.map(s => ({
              label: `${s.name} (${s.code})`,
              value: s.id,
            }));
            // Pre-fill marksValues keys so ngModel has a target
            this.marksValues = {};
            this.students.forEach(s => { this.marksValues[s.id] = null; });
            this.loading = false;
          },
          error: () => {
            this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load students or subjects' });
            this.loading = false;
          },
        });
      },
      error: () => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load exam details' });
        this.loading = false;
      },
    });
  }

  onSubjectChange(subjectId: number): void {
    this.selectedSubjectId = subjectId;
    this.savedResults = {};
  }

  getSavedResult(studentId: number): SavedResult | null {
    return this.savedResults[studentId] ?? null;
  }

  saveMarks(): void {
    if (this.form.invalid || !this.selectedSubjectId || !this.exam) {
      this.form.markAllAsTouched();
      return;
    }

    const marksArray = this.students
      .filter(s => this.marksValues[s.id] !== null && this.marksValues[s.id] !== undefined)
      .map(s => ({
        student_id: s.id,
        marks_obtained: this.marksValues[s.id] as number,
      }));

    if (marksArray.length === 0) {
      this.toast.add({ severity: 'warn', summary: 'Warning', detail: 'Please enter marks for at least one student' });
      return;
    }

    this.saving = true;
    this.examService.enterMarks(this.examId, {
      subject_id: this.selectedSubjectId,
      section_id: this.exam.section_id,
      marks: marksArray,
    }).subscribe({
      next: (res) => {
        this.saving = false;
        const saved = res.data?.saved ?? marksArray.length;
        this.toast.add({
          severity: 'success',
          summary: 'Marks Saved',
          detail: `${saved} record(s) saved successfully`,
        });
        if (res.data?.results && Array.isArray(res.data.results)) {
          res.data.results.forEach((r: any) => {
            if (r.student_id && r.grade !== undefined) {
              this.savedResults[r.student_id] = { grade: r.grade, gpa: r.gpa ?? 0 };
            }
          });
        }
      },
      error: (err) => {
        this.saving = false;
        const detail = err?.error?.message ?? 'Failed to save marks';
        this.toast.add({ severity: 'error', summary: 'Error', detail });
      },
    });
  }

  getStudentFullName(student: Student): string {
    return `${student.first_name} ${student.last_name}`;
  }

  getGradeSeverity(grade: string): 'success' | 'warning' | 'danger' | 'info' {
    if (!grade) return 'info';
    const g = grade.toUpperCase();
    if (g === 'A+' || g === 'A') return 'success';
    if (g === 'B+' || g === 'B' || g === 'C') return 'warning';
    return 'danger';
  }
}
