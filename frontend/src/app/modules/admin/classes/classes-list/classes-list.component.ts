import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MessageService, ConfirmationService } from 'primeng/api';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { ToolbarModule } from 'primeng/toolbar';
import { ToastModule } from 'primeng/toast';
import { InputTextModule } from 'primeng/inputtext';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { DialogModule } from 'primeng/dialog';
import { DropdownModule } from 'primeng/dropdown';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';

import { ClassesService, ClassRecord, AcademicYear } from '../../../../core/services/classes.service';

@Component({
  selector: 'app-classes-list',
  standalone: true,
  imports: [
    CommonModule, RouterLink, FormsModule, ReactiveFormsModule,
    TableModule, ButtonModule, CardModule, ToolbarModule,
    ToastModule, InputTextModule, ConfirmDialogModule, DialogModule, DropdownModule
  ],
  providers: [MessageService, ConfirmationService],
  template: `
    <p-toast position="top-right" />
    <p-confirmDialog />

    <p-card>
      <p-toolbar styleClass="mb-4">
        <ng-template pTemplate="left">
          <h2 class="text-xl font-bold text-900 m-0">Classes</h2>
        </ng-template>
        <ng-template pTemplate="right">
          <div class="flex gap-2">
            <p-button label="Subjects" icon="pi pi-book" severity="secondary" routerLink="/admin/subjects" />
            <p-button label="Add Class" icon="pi pi-plus" (onClick)="openForm()" />
          </div>
        </ng-template>
      </p-toolbar>

      <p-table
        [value]="classes"
        [lazy]="true"
        (onLazyLoad)="load($event)"
        [totalRecords]="total"
        [rows]="20"
        [paginator]="true"
        [loading]="loading"
        dataKey="id"
        styleClass="p-datatable-sm"
        [rowHover]="true"
      >
        <ng-template pTemplate="header">
          <tr>
            <th>Class Name</th>
            <th>Grade Level</th>
            <th>Academic Year</th>
            <th>Sections</th>
            <th>Actions</th>
          </tr>
        </ng-template>
        <ng-template pTemplate="body" let-c>
          <tr>
            <td>
              <a class="text-primary font-medium cursor-pointer" [routerLink]="['/admin/classes', c.id]">{{ c.name }}</a>
            </td>
            <td>Grade {{ c.grade_level }}</td>
            <td>{{ c.academic_year_name || '—' }}</td>
            <td>{{ (c.sections?.length) ?? '—' }}</td>
            <td>
              <div class="flex gap-1">
                <p-button icon="pi pi-eye" [text]="true" [rounded]="true" severity="info" size="small"
                  pTooltip="View" [routerLink]="['/admin/classes', c.id]" />
                <p-button icon="pi pi-pencil" [text]="true" [rounded]="true" severity="secondary" size="small"
                  pTooltip="Edit" (onClick)="openForm(c)" />
                <p-button icon="pi pi-trash" [text]="true" [rounded]="true" severity="danger" size="small"
                  pTooltip="Delete" (onClick)="confirmDelete(c)" />
              </div>
            </td>
          </tr>
        </ng-template>
        <ng-template pTemplate="emptymessage">
          <tr><td colspan="5" class="text-center text-600 py-4">No classes found. <a class="text-primary cursor-pointer" (click)="openForm()">Add the first class.</a></td></tr>
        </ng-template>
      </p-table>
    </p-card>

    <!-- Add/Edit Dialog -->
    <p-dialog
      [header]="editingClass ? 'Edit Class' : 'Add Class'"
      [(visible)]="showDialog"
      [modal]="true"
      [style]="{width:'450px'}"
    >
      <form [formGroup]="form" class="mt-2">
        <div class="field">
          <label>Class Name <span class="text-red-500">*</span></label>
          <input pInputText formControlName="name" class="w-full" placeholder="Grade 10, Class X…" />
        </div>
        <div class="field">
          <label>Grade Level <span class="text-red-500">*</span></label>
          <input pInputText type="number" formControlName="grade_level" class="w-full" placeholder="10" />
        </div>
        <div class="field">
          <label>Academic Year</label>
          <p-dropdown
            formControlName="academic_year_id"
            [options]="academicYears"
            optionLabel="name"
            optionValue="id"
            placeholder="Select year (optional)"
            styleClass="w-full"
            [showClear]="true"
          />
        </div>
        <div class="field">
          <label>Description</label>
          <input pInputText formControlName="description" class="w-full" />
        </div>
      </form>
      <ng-template pTemplate="footer">
        <p-button label="Cancel" severity="secondary" (onClick)="showDialog = false" />
        <p-button
          [label]="editingClass ? 'Save' : 'Create'"
          icon="pi pi-check"
          (onClick)="save()"
          [loading]="saving"
          [disabled]="form.invalid"
        />
      </ng-template>
    </p-dialog>
  `
})
export class ClassesListComponent implements OnInit {
  private svc = inject(ClassesService);
  private toast = inject(MessageService);
  private confirm = inject(ConfirmationService);
  private fb = inject(FormBuilder);

  classes: ClassRecord[] = [];
  total = 0;
  loading = false;
  showDialog = false;
  saving = false;
  editingClass: ClassRecord | null = null;
  academicYears: AcademicYear[] = [];

  form = this.fb.group({
    name: ['', Validators.required],
    grade_level: [null as number | null, Validators.required],
    academic_year_id: [null as number | null],
    description: [''],
  });

  ngOnInit(): void {
    this.load();
    this.svc.getAcademicYears().subscribe({ next: r => this.academicYears = r.data.academic_years, error: () => {} });
  }

  load(event?: any): void {
    this.loading = true;
    const page = event ? Math.floor(event.first / event.rows) + 1 : 1;
    this.svc.getClasses(page).subscribe({
      next: r => { this.classes = r.data.classes; this.total = r.data.meta.total; this.loading = false; },
      error: () => { this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load classes' }); this.loading = false; }
    });
  }

  openForm(c?: ClassRecord): void {
    this.editingClass = c ?? null;
    this.form.reset({ name: c?.name ?? '', grade_level: c?.grade_level ?? null, academic_year_id: c?.academic_year_id ?? null, description: c?.description ?? '' });
    this.showDialog = true;
  }

  save(): void {
    if (this.form.invalid) return;
    this.saving = true;
    const payload = { ...this.form.value };
    const req = this.editingClass
      ? this.svc.updateClass(this.editingClass.id, payload)
      : this.svc.createClass(payload);

    req.subscribe({
      next: () => {
        this.toast.add({ severity: 'success', summary: this.editingClass ? 'Updated' : 'Created', detail: 'Class saved' });
        this.showDialog = false;
        this.load();
        this.saving = false;
      },
      error: (err) => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: err.error?.message || 'Failed to save' });
        this.saving = false;
      }
    });
  }

  confirmDelete(c: ClassRecord): void {
    this.confirm.confirm({
      message: `Delete class "${c.name}"? This will fail if sections exist.`,
      header: 'Confirm Delete',
      acceptButtonStyleClass: 'p-button-danger',
      accept: () => {
        this.svc.deleteClass(c.id).subscribe({
          next: () => { this.toast.add({ severity: 'success', summary: 'Deleted', detail: 'Class removed' }); this.load(); },
          error: (err) => { this.toast.add({ severity: 'error', summary: 'Error', detail: err.error?.message || 'Cannot delete' }); }
        });
      }
    });
  }
}
