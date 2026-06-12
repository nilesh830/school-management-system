import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators, FormsModule } from '@angular/forms';
import { MessageService, ConfirmationService } from 'primeng/api';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { TableModule } from 'primeng/table';
import { ToastModule } from 'primeng/toast';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';

import { ClassesService, ClassRecord, Section } from '../../../../core/services/classes.service';

@Component({
  selector: 'app-class-detail',
  standalone: true,
  imports: [
    CommonModule, RouterLink, ReactiveFormsModule, FormsModule,
    CardModule, ButtonModule, TableModule,
    ToastModule, ConfirmDialogModule, DialogModule, InputTextModule
  ],
  providers: [MessageService, ConfirmationService],
  template: `
    <p-toast position="top-right" />
    <p-confirmDialog />

    @if (classRecord) {
      <div class="mb-3 flex align-items-center gap-2">
        <p-button icon="pi pi-arrow-left" [text]="true" routerLink="/admin/classes" />
        <h2 class="text-2xl font-bold text-900 m-0">{{ classRecord.name }}</h2>
        <span class="text-600">Grade {{ classRecord.grade_level }}</span>
        @if (classRecord.academic_year_name) {
          <span class="text-600">· {{ classRecord.academic_year_name }}</span>
        }
      </div>

      <p-card>
        <div class="flex justify-content-between align-items-center mb-3">
          <h3 class="text-lg font-semibold m-0">Sections</h3>
          <p-button label="Add Section" icon="pi pi-plus" size="small" (onClick)="openSectionForm()" />
        </div>

        <p-table [value]="sections" [loading]="loading" styleClass="p-datatable-sm" dataKey="id">
          <ng-template pTemplate="header">
            <tr>
              <th>Section</th>
              <th>Capacity</th>
              <th>Students Enrolled</th>
              <th>Class Teacher</th>
              <th>Actions</th>
            </tr>
          </ng-template>
          <ng-template pTemplate="body" let-sec>
            <tr>
              <td class="font-medium">{{ classRecord.name }} - {{ sec.name }}</td>
              <td>{{ sec.capacity }}</td>
              <td>{{ sec.student_count ?? '—' }}</td>
              <td>{{ sec.class_teacher_name || '—' }}</td>
              <td>
                <div class="flex gap-1">
                  <p-button icon="pi pi-pencil" [text]="true" [rounded]="true" severity="secondary" size="small"
                    pTooltip="Edit" (onClick)="openSectionForm(sec)" />
                  <p-button icon="pi pi-trash" [text]="true" [rounded]="true" severity="danger" size="small"
                    pTooltip="Delete" (onClick)="confirmDeleteSection(sec)" />
                </div>
              </td>
            </tr>
          </ng-template>
          <ng-template pTemplate="emptymessage">
            <tr><td colspan="5" class="text-center text-600 py-4">No sections yet. <span class="text-primary cursor-pointer" (click)="openSectionForm()">Add a section.</span></td></tr>
          </ng-template>
        </p-table>
      </p-card>
    }

    <!-- Section Form Dialog -->
    <p-dialog
      [header]="editingSection ? 'Edit Section' : 'Add Section'"
      [(visible)]="showSectionDialog"
      [modal]="true"
      [style]="{width:'380px'}"
    >
      <form [formGroup]="sectionForm" class="mt-2">
        <div class="field">
          <label>Section Name <span class="text-red-500">*</span></label>
          <input pInputText formControlName="name" class="w-full" placeholder="A, B, C…" />
        </div>
        <div class="field">
          <label>Capacity</label>
          <input pInputText type="number" formControlName="capacity" class="w-full" placeholder="40" />
        </div>
      </form>
      <ng-template pTemplate="footer">
        <p-button label="Cancel" severity="secondary" (onClick)="showSectionDialog = false" />
        <p-button
          [label]="editingSection ? 'Save' : 'Create'"
          icon="pi pi-check"
          (onClick)="saveSection()"
          [loading]="savingSection"
          [disabled]="sectionForm.invalid"
        />
      </ng-template>
    </p-dialog>
  `
})
export class ClassDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private svc = inject(ClassesService);
  private toast = inject(MessageService);
  private confirm = inject(ConfirmationService);
  private fb = inject(FormBuilder);

  classRecord: ClassRecord | null = null;
  sections: Section[] = [];
  loading = false;

  showSectionDialog = false;
  savingSection = false;
  editingSection: Section | null = null;

  sectionForm = this.fb.group({
    name: ['', Validators.required],
    capacity: [40, Validators.min(1)],
  });

  ngOnInit(): void {
    const id = +this.route.snapshot.paramMap.get('id')!;
    this.svc.getClassById(id).subscribe({
      next: r => {
        this.classRecord = r.data;
        this.loadSections(id);
      },
      error: () => { this.toast.add({ severity: 'error', summary: 'Error', detail: 'Class not found' }); }
    });
  }

  private loadSections(classId: number): void {
    this.loading = true;
    this.svc.getSections(classId).subscribe({
      next: r => { this.sections = r.data.sections; this.loading = false; },
      error: () => { this.loading = false; }
    });
  }

  openSectionForm(sec?: Section): void {
    this.editingSection = sec ?? null;
    this.sectionForm.reset({ name: sec?.name ?? '', capacity: sec?.capacity ?? 40 });
    this.showSectionDialog = true;
  }

  saveSection(): void {
    if (this.sectionForm.invalid) return;
    this.savingSection = true;

    const payload = {
      name: this.sectionForm.value.name,
      capacity: this.sectionForm.value.capacity,
      class_id: this.classRecord!.id,
    };

    const req = this.editingSection
      ? this.svc.updateSection(this.editingSection.id, payload)
      : this.svc.createSection(payload);

    req.subscribe({
      next: () => {
        this.toast.add({ severity: 'success', summary: 'Saved', detail: 'Section saved' });
        this.showSectionDialog = false;
        this.loadSections(this.classRecord!.id);
        this.savingSection = false;
      },
      error: (err) => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: err.error?.message || 'Failed to save section' });
        this.savingSection = false;
      }
    });
  }

  confirmDeleteSection(sec: Section): void {
    this.confirm.confirm({
      message: `Delete section "${this.classRecord?.name} - ${sec.name}"? This will fail if students are enrolled.`,
      header: 'Confirm Delete',
      acceptButtonStyleClass: 'p-button-danger',
      accept: () => {
        this.svc.deleteSection(sec.id).subscribe({
          next: () => {
            this.toast.add({ severity: 'success', summary: 'Deleted', detail: 'Section removed' });
            this.loadSections(this.classRecord!.id);
          },
          error: (err) => {
            this.toast.add({ severity: 'error', summary: 'Error', detail: err.error?.message || 'Cannot delete section' });
          }
        });
      }
    });
  }
}
