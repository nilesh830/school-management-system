import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MessageService, ConfirmationService } from 'primeng/api';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { ToolbarModule } from 'primeng/toolbar';
import { ToastModule } from 'primeng/toast';
import { InputTextModule } from 'primeng/inputtext';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { DialogModule } from 'primeng/dialog';

import { ClassesService, Subject } from '../../../../core/services/classes.service';

@Component({
  selector: 'app-subjects-list',
  standalone: true,
  imports: [
    CommonModule, RouterLink, FormsModule, ReactiveFormsModule,
    TableModule, ButtonModule, CardModule, ToolbarModule,
    ToastModule, InputTextModule, ConfirmDialogModule, DialogModule
  ],
  providers: [MessageService, ConfirmationService],
  template: `
    <p-toast position="top-right" />
    <p-confirmDialog />

    <p-card>
      <p-toolbar styleClass="mb-4">
        <ng-template pTemplate="left">
          <div class="flex align-items-center gap-2">
            <p-button icon="pi pi-arrow-left" [text]="true" routerLink="/admin/classes" pTooltip="Back to Classes" />
            <h2 class="text-xl font-bold text-900 m-0">Subjects</h2>
          </div>
        </ng-template>
        <ng-template pTemplate="right">
          <div class="flex gap-2 align-items-center">
            <span class="p-input-icon-left">
              <i class="pi pi-search"></i>
              <input pInputText type="text" [(ngModel)]="searchTerm" (ngModelChange)="load()" placeholder="Search…" class="w-14rem" />
            </span>
            <p-button label="Add Subject" icon="pi pi-plus" (onClick)="openForm()" />
          </div>
        </ng-template>
      </p-toolbar>

      <p-table
        [value]="subjects"
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
            <th>Code</th>
            <th>Name</th>
            <th>Max Marks</th>
            <th>Pass Marks</th>
            <th>Actions</th>
          </tr>
        </ng-template>
        <ng-template pTemplate="body" let-s>
          <tr>
            <td><span class="font-mono font-medium">{{ s.code }}</span></td>
            <td>{{ s.name }}</td>
            <td>{{ s.max_marks }}</td>
            <td>{{ s.pass_marks }}</td>
            <td>
              <div class="flex gap-1">
                <p-button icon="pi pi-pencil" [text]="true" [rounded]="true" severity="secondary" size="small"
                  pTooltip="Edit" (onClick)="openForm(s)" />
                <p-button icon="pi pi-trash" [text]="true" [rounded]="true" severity="danger" size="small"
                  pTooltip="Delete" (onClick)="confirmDelete(s)" />
              </div>
            </td>
          </tr>
        </ng-template>
        <ng-template pTemplate="emptymessage">
          <tr><td colspan="5" class="text-center text-600 py-4">No subjects found.</td></tr>
        </ng-template>
      </p-table>
    </p-card>

    <!-- Add/Edit Dialog -->
    <p-dialog
      [header]="editingSubject ? 'Edit Subject' : 'Add Subject'"
      [(visible)]="showDialog"
      [modal]="true"
      [style]="{width:'420px'}"
    >
      <form [formGroup]="form" class="mt-2">
        <div class="field">
          <label>Code <span class="text-red-500">*</span></label>
          <input pInputText formControlName="code" class="w-full" placeholder="MATH101" style="text-transform:uppercase" />
          <small class="text-600">Will be stored uppercase</small>
        </div>
        <div class="field">
          <label>Name <span class="text-red-500">*</span></label>
          <input pInputText formControlName="name" class="w-full" />
        </div>
        <div class="grid">
          <div class="col-6 field">
            <label>Max Marks</label>
            <input pInputText type="number" formControlName="max_marks" class="w-full" />
          </div>
          <div class="col-6 field">
            <label>Pass Marks</label>
            <input pInputText type="number" formControlName="pass_marks" class="w-full" />
          </div>
        </div>
        <div class="field">
          <label>Description</label>
          <input pInputText formControlName="description" class="w-full" />
        </div>
      </form>
      <ng-template pTemplate="footer">
        <p-button label="Cancel" severity="secondary" (onClick)="showDialog = false" />
        <p-button
          [label]="editingSubject ? 'Save' : 'Create'"
          icon="pi pi-check"
          (onClick)="save()"
          [loading]="saving"
          [disabled]="form.invalid"
        />
      </ng-template>
    </p-dialog>
  `
})
export class SubjectsListComponent implements OnInit {
  private svc = inject(ClassesService);
  private toast = inject(MessageService);
  private confirm = inject(ConfirmationService);
  private fb = inject(FormBuilder);

  subjects: Subject[] = [];
  total = 0;
  loading = false;
  searchTerm = '';
  showDialog = false;
  saving = false;
  editingSubject: Subject | null = null;

  form = this.fb.group({
    code: ['', Validators.required],
    name: ['', Validators.required],
    max_marks: [100],
    pass_marks: [35],
    description: [''],
  });

  ngOnInit(): void { this.load(); }

  load(event?: any): void {
    this.loading = true;
    const page = event ? Math.floor(event.first / event.rows) + 1 : 1;
    this.svc.getSubjects(page, 20, this.searchTerm).subscribe({
      next: r => { this.subjects = r.data.subjects; this.total = r.data.meta.total; this.loading = false; },
      error: () => { this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load subjects' }); this.loading = false; }
    });
  }

  openForm(s?: Subject): void {
    this.editingSubject = s ?? null;
    this.form.reset({
      code: s?.code ?? '',
      name: s?.name ?? '',
      max_marks: s?.max_marks ?? 100,
      pass_marks: s?.pass_marks ?? 35,
      description: s?.description ?? '',
    });
    this.showDialog = true;
  }

  save(): void {
    if (this.form.invalid) return;
    this.saving = true;
    const payload = { ...this.form.value };
    const req = this.editingSubject
      ? this.svc.updateSubject(this.editingSubject.id, payload)
      : this.svc.createSubject(payload);

    req.subscribe({
      next: () => {
        this.toast.add({ severity: 'success', summary: this.editingSubject ? 'Updated' : 'Created', detail: 'Subject saved' });
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

  confirmDelete(s: Subject): void {
    this.confirm.confirm({
      message: `Delete subject "${s.name}"? This will fail if teacher assignments exist.`,
      header: 'Confirm Delete',
      acceptButtonStyleClass: 'p-button-danger',
      accept: () => {
        this.svc.deleteSubject(s.id).subscribe({
          next: () => { this.toast.add({ severity: 'success', summary: 'Deleted', detail: 'Subject removed' }); this.load(); },
          error: (err) => { this.toast.add({ severity: 'error', summary: 'Error', detail: err.error?.message || 'Cannot delete' }); }
        });
      }
    });
  }
}
