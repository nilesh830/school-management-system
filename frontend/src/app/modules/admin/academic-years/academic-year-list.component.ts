import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MessageService } from 'primeng/api';
import { TableModule } from 'primeng/table';
import { DialogModule } from 'primeng/dialog';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { CalendarModule } from 'primeng/calendar';
import { CheckboxModule } from 'primeng/checkbox';
import { TagModule } from 'primeng/tag';
import { ToolbarModule } from 'primeng/toolbar';
import { ToastModule } from 'primeng/toast';
import { ProgressSpinnerModule } from 'primeng/progressspinner';

import { ClassesService, AcademicYear } from '../../../core/services/classes.service';

@Component({
  selector: 'app-academic-year-list',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    TableModule,
    DialogModule,
    ButtonModule,
    InputTextModule,
    CalendarModule,
    CheckboxModule,
    TagModule,
    ToolbarModule,
    ToastModule,
    ProgressSpinnerModule,
  ],
  providers: [MessageService],
  templateUrl: './academic-year-list.component.html',
})
export class AcademicYearListComponent implements OnInit {
  private classesService = inject(ClassesService);
  private fb = inject(FormBuilder);
  private toast = inject(MessageService);

  years: AcademicYear[] = [];
  loading = false;
  dialogVisible = false;
  saving = false;
  isEdit = false;
  editingId: number | null = null;

  form: FormGroup = this.fb.group({
    name: ['', Validators.required],
    start_date: [null, Validators.required],
    end_date: [null, Validators.required],
    is_current: [false],
  });

  ngOnInit(): void {
    this.loadYears();
  }

  loadYears(): void {
    this.loading = true;
    this.classesService.getAcademicYears().subscribe({
      next: (res) => {
        this.years = res.data?.academic_years ?? [];
        this.loading = false;
      },
      error: () => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load academic years' });
        this.loading = false;
      },
    });
  }

  openDialog(year?: AcademicYear): void {
    this.isEdit = !!year;
    this.editingId = year ? year.id : null;
    this.form.reset({
      name: year?.name ?? '',
      start_date: year?.start_date ? new Date(year.start_date) : null,
      end_date: year?.end_date ? new Date(year.end_date) : null,
      is_current: year?.is_current ?? false,
    });
    this.dialogVisible = true;
  }

  save(): void {
    if (this.form.invalid) return;
    this.saving = true;
    const raw = this.form.value;
    const payload = {
      name: raw.name,
      start_date: this.formatDate(raw.start_date),
      end_date: this.formatDate(raw.end_date),
      is_current: raw.is_current ?? false,
    };

    const req$ = this.isEdit && this.editingId !== null
      ? this.classesService.updateAcademicYear(this.editingId, payload)
      : this.classesService.createAcademicYear(payload);

    req$.subscribe({
      next: () => {
        this.saving = false;
        this.dialogVisible = false;
        this.toast.add({
          severity: 'success',
          summary: 'Success',
          detail: this.isEdit ? 'Academic year updated' : 'Academic year created',
        });
        this.loadYears();
      },
      error: (err) => {
        this.saving = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: err?.error?.message ?? 'Failed to save academic year' });
      },
    });
  }

  setCurrent(year: AcademicYear): void {
    if (year.is_current) return;
    this.classesService.updateAcademicYear(year.id, { is_current: true }).subscribe({
      next: () => {
        this.toast.add({ severity: 'success', summary: 'Updated', detail: `${year.name} is now the current year` });
        this.loadYears();
      },
      error: () => this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to set current year' }),
    });
  }

  deleteYear(year: AcademicYear): void {
    if (!window.confirm(`Delete academic year "${year.name}"?`)) return;
    this.classesService.deleteAcademicYear(year.id).subscribe({
      next: () => {
        this.toast.add({ severity: 'success', summary: 'Deleted', detail: 'Academic year deleted' });
        this.loadYears();
      },
      error: () => this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to delete academic year' }),
    });
  }

  private formatDate(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }
}
