import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MessageService, ConfirmationService } from 'primeng/api';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { DropdownModule } from 'primeng/dropdown';
import { ToastModule } from 'primeng/toast';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { DialogModule } from 'primeng/dialog';
import { CalendarModule } from 'primeng/calendar';
import { ToolbarModule } from 'primeng/toolbar';

import { ClassesService, ClassRecord, Section, Subject } from '../../../../core/services/classes.service';
import { TimetableService, TimetableEntry } from '../../../../core/services/timetable.service';
import { TeacherService, Teacher } from '../../../../core/services/teacher.service';

const DAY_LABELS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const PERIODS = [1, 2, 3, 4, 5, 6, 7, 8];

@Component({
  selector: 'app-timetable-view',
  standalone: true,
  imports: [
    CommonModule, FormsModule, ReactiveFormsModule,
    CardModule, ButtonModule, DropdownModule, ToastModule,
    ConfirmDialogModule, DialogModule, CalendarModule, ToolbarModule
  ],
  providers: [MessageService, ConfirmationService],
  template: `
    <p-toast position="top-right" />
    <p-confirmDialog />

    <p-card>
      <p-toolbar styleClass="mb-4">
        <ng-template pTemplate="left">
          <h2 class="text-xl font-bold text-900 m-0">Timetable</h2>
        </ng-template>
        <ng-template pTemplate="right">
          <div class="flex gap-2 align-items-center">
            <p-dropdown
              [(ngModel)]="selectedClassId"
              [options]="classes"
              optionLabel="name"
              optionValue="id"
              placeholder="Select Class"
              styleClass="w-12rem"
              (ngModelChange)="onClassChange()"
            />
            <p-dropdown
              [(ngModel)]="selectedSectionId"
              [options]="sections"
              optionLabel="name"
              optionValue="id"
              placeholder="Select Section"
              styleClass="w-10rem"
              [disabled]="!selectedClassId"
              (ngModelChange)="loadTimetable()"
            />
          </div>
        </ng-template>
      </p-toolbar>

      @if (selectedSectionId) {
        <div class="overflow-x-auto">
          <table class="w-full border-collapse text-sm" style="min-width:800px">
            <thead>
              <tr>
                <th class="border-1 surface-border p-2 text-left bg-surface-100 w-6rem">Period</th>
                @for (day of dayLabels; track day; let i = $index) {
                  <th class="border-1 surface-border p-2 text-center bg-surface-100">{{ day }}</th>
                }
              </tr>
            </thead>
            <tbody>
              @for (period of periods; track period) {
                <tr>
                  <td class="border-1 surface-border p-2 font-medium bg-surface-50">Period {{ period }}</td>
                  @for (day of [0,1,2,3,4,5]; track day) {
                    <td
                      class="border-1 surface-border p-1 text-center cursor-pointer hover:surface-100 transition-colors transition-duration-150"
                      style="min-width:120px; height:60px"
                      (click)="cellClick(day, period, getEntry(day, period))"
                    >
                      @if (getEntry(day, period); as entry) {
                        <div class="primary-50 border-round p-1 text-xs text-left" style="background:var(--primary-50); border-left:3px solid var(--primary-color)">
                          <div class="font-semibold text-primary">{{ entry.subject_name }}</div>
                          <div class="text-600">{{ entry.teacher_name }}</div>
                          <div class="text-500">{{ entry.start_time }}–{{ entry.end_time }}</div>
                        </div>
                      } @else {
                        <span class="text-400 text-xs">+ Add</span>
                      }
                    </td>
                  }
                </tr>
              }
            </tbody>
          </table>
        </div>
      } @else {
        <div class="text-center text-600 py-6">
          <i class="pi pi-calendar text-4xl text-300 block mb-2"></i>
          Select a class and section to view or edit the timetable.
        </div>
      }
    </p-card>

    <!-- Add/Edit Slot Dialog -->
    <p-dialog
      [(visible)]="showSlotDialog"
      [header]="editingEntry ? 'Edit Slot' : 'Add Slot'"
      [modal]="true"
      [style]="{width:'420px'}"
    >
      @if (editingEntry) {
        <div class="mb-3 p-2 surface-100 border-round text-sm text-600">
          <i class="pi pi-info-circle mr-1"></i>
          Editing: {{ editingEntry.subject_name }} ({{ dayLabels[editingEntry.day_of_week] }}, P{{ editingEntry.period_no }})
          <p-button icon="pi pi-trash" [text]="true" severity="danger" size="small" class="ml-2" label="Delete slot" (onClick)="deleteEntry()" />
        </div>
      }
      <form [formGroup]="slotForm" class="mt-2">
        <div class="field">
          <label>Subject <span class="text-red-500">*</span></label>
          <p-dropdown formControlName="subject_id" [options]="allSubjects" optionLabel="name" optionValue="id"
            placeholder="Select subject" styleClass="w-full" />
        </div>
        <div class="field">
          <label>Teacher <span class="text-red-500">*</span></label>
          <p-dropdown formControlName="teacher_id" [options]="allTeachers" optionLabel="full_name" optionValue="id"
            placeholder="Select teacher" styleClass="w-full" [filter]="true" filterBy="full_name" />
        </div>
        <div class="grid">
          <div class="col-6 field">
            <label>Start Time <span class="text-red-500">*</span></label>
            <p-calendar formControlName="start_time" [timeOnly]="true" hourFormat="24" styleClass="w-full" />
          </div>
          <div class="col-6 field">
            <label>End Time <span class="text-red-500">*</span></label>
            <p-calendar formControlName="end_time" [timeOnly]="true" hourFormat="24" styleClass="w-full" />
          </div>
        </div>
      </form>
      <ng-template pTemplate="footer">
        <p-button label="Cancel" severity="secondary" (onClick)="showSlotDialog = false" />
        <p-button
          [label]="editingEntry ? 'Update' : 'Add Slot'"
          icon="pi pi-check"
          (onClick)="saveSlot()"
          [loading]="savingSlot"
          [disabled]="slotForm.invalid"
        />
      </ng-template>
    </p-dialog>
  `
})
export class TimetableViewComponent implements OnInit {
  private classesSvc = inject(ClassesService);
  private timetableSvc = inject(TimetableService);
  private teacherSvc = inject(TeacherService);
  private toast = inject(MessageService);
  private confirm = inject(ConfirmationService);
  private fb = inject(FormBuilder);

  classes: ClassRecord[] = [];
  sections: Section[] = [];
  allSubjects: Subject[] = [];
  allTeachers: Teacher[] = [];
  timetable: TimetableEntry[] = [];

  selectedClassId: number | null = null;
  selectedSectionId: number | null = null;
  loadingTimetable = false;

  showSlotDialog = false;
  savingSlot = false;
  editingEntry: TimetableEntry | null = null;
  pendingDay = 0;
  pendingPeriod = 1;

  readonly dayLabels = DAY_LABELS;
  readonly periods = PERIODS;

  slotForm = this.fb.group({
    subject_id: [null as number | null, Validators.required],
    teacher_id: [null as number | null, Validators.required],
    start_time: [null as Date | null, Validators.required],
    end_time: [null as Date | null, Validators.required],
  });

  ngOnInit(): void {
    this.classesSvc.getClasses(1, 100).subscribe({ next: r => this.classes = r.data.classes, error: () => {} });
    this.classesSvc.getSubjects(1, 100).subscribe({ next: r => this.allSubjects = r.data.subjects, error: () => {} });
    this.teacherSvc.getTeachers(1, 100).subscribe({ next: r => this.allTeachers = r.data.teachers, error: () => {} });
  }

  onClassChange(): void {
    this.selectedSectionId = null;
    this.timetable = [];
    if (this.selectedClassId) {
      this.classesSvc.getSections(this.selectedClassId).subscribe({
        next: r => this.sections = r.data.sections,
        error: () => {}
      });
    } else {
      this.sections = [];
    }
  }

  loadTimetable(): void {
    if (!this.selectedSectionId) return;
    this.loadingTimetable = true;
    this.timetableSvc.getBySection(this.selectedSectionId).subscribe({
      next: r => { this.timetable = r.data.timetable; this.loadingTimetable = false; },
      error: () => { this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load timetable' }); this.loadingTimetable = false; }
    });
  }

  getEntry(day: number, period: number): TimetableEntry | undefined {
    return this.timetable.find(e => e.day_of_week === day && e.period_no === period);
  }

  cellClick(day: number, period: number, entry?: TimetableEntry): void {
    this.pendingDay = day;
    this.pendingPeriod = period;
    this.editingEntry = entry ?? null;

    if (entry) {
      this.slotForm.patchValue({
        subject_id: entry.subject_id,
        teacher_id: entry.teacher_id,
        start_time: this.parseTime(entry.start_time),
        end_time: this.parseTime(entry.end_time),
      });
    } else {
      this.slotForm.reset();
    }
    this.showSlotDialog = true;
  }

  private parseTime(t: string): Date | null {
    if (!t) return null;
    const parts = t.split(':');
    const d = new Date();
    d.setHours(+parts[0], +parts[1], 0, 0);
    return d;
  }

  private toTimeStr(d: Date | null): string | null {
    if (!d) return null;
    const h = d.getHours().toString().padStart(2, '0');
    const m = d.getMinutes().toString().padStart(2, '0');
    return `${h}:${m}`;
  }

  saveSlot(): void {
    if (this.slotForm.invalid) { this.slotForm.markAllAsTouched(); return; }
    this.savingSlot = true;

    const payload = {
      section_id: this.selectedSectionId,
      subject_id: this.slotForm.value.subject_id,
      teacher_id: this.slotForm.value.teacher_id,
      day_of_week: this.pendingDay,
      period_no: this.pendingPeriod,
      start_time: this.toTimeStr(this.slotForm.value.start_time ?? null),
      end_time: this.toTimeStr(this.slotForm.value.end_time ?? null),
    };

    const req = this.editingEntry
      ? this.timetableSvc.update(this.editingEntry.id, payload)
      : this.timetableSvc.create(payload);

    req.subscribe({
      next: () => {
        this.toast.add({ severity: 'success', summary: 'Saved', detail: 'Timetable slot saved' });
        this.showSlotDialog = false;
        this.savingSlot = false;
        this.loadTimetable();
      },
      error: (err) => {
        this.toast.add({ severity: 'error', summary: 'Conflict', detail: err.error?.message || 'Failed to save slot' });
        this.savingSlot = false;
      }
    });
  }

  deleteEntry(): void {
    if (!this.editingEntry) return;
    this.confirm.confirm({
      message: 'Remove this timetable slot?',
      header: 'Confirm',
      acceptButtonStyleClass: 'p-button-danger',
      accept: () => {
        this.timetableSvc.delete(this.editingEntry!.id).subscribe({
          next: () => {
            this.toast.add({ severity: 'success', summary: 'Removed', detail: 'Slot deleted' });
            this.showSlotDialog = false;
            this.loadTimetable();
          },
          error: () => { this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to delete slot' }); }
        });
      }
    });
  }
}
