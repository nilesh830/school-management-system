import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { MessageService } from 'primeng/api';
import { TableModule } from 'primeng/table';
import { DialogModule } from 'primeng/dialog';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { DropdownModule } from 'primeng/dropdown';
import { CalendarModule } from 'primeng/calendar';
import { TagModule } from 'primeng/tag';
import { ToolbarModule } from 'primeng/toolbar';
import { ToastModule } from 'primeng/toast';
import { ProgressSpinnerModule } from 'primeng/progressspinner';

import { ExamService, Exam } from '../../../../core/services/exam.service';
import { ClassesService, Section } from '../../../../core/services/classes.service';

interface Option {
  label: string;
  value: number;
}

@Component({
  selector: 'app-exam-list',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
    TableModule,
    DialogModule,
    ButtonModule,
    InputTextModule,
    DropdownModule,
    CalendarModule,
    TagModule,
    ToolbarModule,
    ToastModule,
    ProgressSpinnerModule,
  ],
  providers: [MessageService],
  templateUrl: './exam-list.component.html',
})
export class ExamListComponent implements OnInit {
  private examService = inject(ExamService);
  private classesService = inject(ClassesService);
  private fb = inject(FormBuilder);
  private toast = inject(MessageService);

  exams: Exam[] = [];
  loading = false;
  dialogVisible = false;
  saving = false;
  isEdit = false;
  editingId: number | null = null;

  examTypeOptions = [
    { label: 'Midterm', value: 'midterm' },
    { label: 'Final', value: 'final' },
    { label: 'Unit Test', value: 'unit_test' },
    { label: 'Practical', value: 'practical' },
  ];

  // Reference data for the dropdowns
  classOptions: Option[] = [];
  sectionOptions: Option[] = [];
  yearOptions: Option[] = [];
  private allSections: Section[] = [];
  private currentYearId: number | null = null;
  refDataLoading = false;

  form: FormGroup = this.fb.group({
    name: ['', Validators.required],
    term: ['', Validators.required],
    exam_type: [null, Validators.required],
    class_id: [null, Validators.required],
    section_id: [null, Validators.required],
    academic_year_id: [null, Validators.required],
    conducted_date: [null],
  });

  ngOnInit(): void {
    this.loadExams();
    this.loadRefData();
  }

  loadExams(): void {
    this.loading = true;
    this.examService.getExams().subscribe({
      next: (res) => {
        this.exams = res.data.exams ?? [];
        this.loading = false;
      },
      error: () => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load exams' });
        this.loading = false;
      },
    });
  }

  /** Load classes, sections and academic years for the form dropdowns. */
  loadRefData(): void {
    this.refDataLoading = true;
    forkJoin({
      classes: this.classesService.getClasses(1, 200),
      sections: this.classesService.getSections(undefined, 1, 500),
      years: this.classesService.getAcademicYears(),
    }).subscribe({
      next: (res) => {
        const classes = res.classes.data.classes ?? [];
        this.classOptions = classes.map(c => ({ label: c.name, value: c.id }));

        this.allSections = res.sections.data.sections ?? [];

        const years = res.years.data.academic_years ?? [];
        this.yearOptions = years.map(y => ({ label: y.name, value: y.id }));
        this.currentYearId = years.find(y => y.is_current)?.id ?? null;

        this.refDataLoading = false;
      },
      error: () => {
        this.refDataLoading = false;
        this.toast.add({
          severity: 'error',
          summary: 'Error',
          detail: 'Failed to load classes / sections',
        });
      },
    });
  }

  /** Rebuild the Section options for the chosen class. */
  onClassChange(classId: number | null): void {
    this.sectionOptions = this.allSections
      .filter(s => s.class_id === classId)
      .map(s => ({ label: s.name, value: s.id }));
    // The previously selected section may not belong to the new class.
    this.form.get('section_id')?.setValue(null);
  }

  /** Friendly "Class - Section" label for the table, from a section id. */
  sectionLabel(sectionId: number): string {
    const s = this.allSections.find(x => x.id === sectionId);
    if (!s) return String(sectionId);
    return s.class_name ? `${s.class_name} - ${s.name}` : s.name;
  }

  openDialog(exam?: Exam): void {
    this.form.reset();
    this.sectionOptions = [];
    this.isEdit = false;
    this.editingId = null;

    if (exam) {
      this.isEdit = true;
      this.editingId = exam.id;

      // Derive the class from the exam's section so the cascade shows correctly.
      const section = this.allSections.find(s => s.id === exam.section_id);
      const classId = section?.class_id ?? null;
      this.onClassChange(classId);

      this.form.patchValue({
        name: exam.name,
        term: exam.term,
        exam_type: exam.exam_type,
        class_id: classId,
        section_id: exam.section_id,
        academic_year_id: exam.academic_year_id,
        conducted_date: exam.conducted_date ? new Date(exam.conducted_date) : null,
      });
    } else {
      // Default new exams to the current academic year for convenience.
      this.form.patchValue({ academic_year_id: this.currentYearId });
    }

    this.dialogVisible = true;
  }

  closeDialog(): void {
    this.dialogVisible = false;
    this.form.reset();
  }

  saveExam(): void {
    if (this.form.invalid) return;

    this.saving = true;
    const raw = this.form.value;
    const payload: Partial<Exam> = {
      name: raw.name,
      term: raw.term,
      exam_type: raw.exam_type,
      section_id: raw.section_id,
      academic_year_id: raw.academic_year_id,
      conducted_date: raw.conducted_date
        ? this.formatDate(raw.conducted_date)
        : null,
    };

    const request$ = this.isEdit && this.editingId !== null
      ? this.examService.updateExam(this.editingId, payload)
      : this.examService.createExam(payload);

    request$.subscribe({
      next: () => {
        this.saving = false;
        this.dialogVisible = false;
        this.toast.add({
          severity: 'success',
          summary: 'Success',
          detail: this.isEdit ? 'Exam updated successfully' : 'Exam created successfully',
        });
        this.loadExams();
      },
      error: () => {
        this.saving = false;
        this.toast.add({
          severity: 'error',
          summary: 'Error',
          detail: this.isEdit ? 'Failed to update exam' : 'Failed to create exam',
        });
      },
    });
  }

  getStatusSeverity(isActive: boolean): 'success' | 'danger' {
    return isActive ? 'success' : 'danger';
  }

  getExamTypeLabel(examType: string): string {
    const opt = this.examTypeOptions.find(o => o.value === examType);
    return opt ? opt.label : examType;
  }

  private formatDate(date: Date): string {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }
}
