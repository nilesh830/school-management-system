import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MessageService, ConfirmationService } from 'primeng/api';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { TabViewModule } from 'primeng/tabview';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ToastModule } from 'primeng/toast';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { DialogModule } from 'primeng/dialog';
import { DropdownModule } from 'primeng/dropdown';
import { FormsModule } from '@angular/forms';

import { TeacherService, Teacher, TeacherSubjectAssignment, TimetableEntry } from '../../../../core/services/teacher.service';
import { ClassesService, Subject } from '../../../../core/services/classes.service';

const DAY_LABELS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

@Component({
  selector: 'app-teacher-detail',
  standalone: true,
  imports: [
    CommonModule, RouterLink, FormsModule,
    CardModule, ButtonModule, TabViewModule, TableModule,
    TagModule, ToastModule, ConfirmDialogModule, DialogModule, DropdownModule
  ],
  providers: [MessageService, ConfirmationService],
  template: `
    <p-toast position="top-right" />
    <p-confirmDialog />

    @if (teacher) {
      <div class="mb-3 flex align-items-center justify-content-between">
        <div class="flex align-items-center gap-2">
          <p-button icon="pi pi-arrow-left" [text]="true" routerLink="/admin/teachers" />
          <h2 class="text-2xl font-bold text-900 m-0">{{ teacher.full_name }}</h2>
          <span class="text-600 text-sm">{{ teacher.employee_id }}</span>
        </div>
        <p-button
          label="Edit"
          icon="pi pi-pencil"
          severity="secondary"
          [routerLink]="['/admin/teachers', teacher.id, 'edit']"
        />
      </div>

      <p-tabView>

        <!-- TAB 1: Profile -->
        <p-tabPanel header="Profile">
          <div class="grid">
            <div class="col-12 md:col-6">
              <table class="w-full text-sm">
                <tr><td class="text-600 w-10rem py-2">Employee ID</td><td class="font-medium">{{ teacher.employee_id }}</td></tr>
                <tr><td class="text-600 py-2">Full Name</td><td class="font-medium">{{ teacher.full_name }}</td></tr>
                <tr><td class="text-600 py-2">Gender</td><td>{{ teacher.gender || '—' }}</td></tr>
                <tr><td class="text-600 py-2">Date of Birth</td><td>{{ (teacher.date_of_birth | date:'mediumDate') || '—' }}</td></tr>
                <tr><td class="text-600 py-2">Joining Date</td><td>{{ teacher.joining_date | date:'mediumDate' }}</td></tr>
                <tr><td class="text-600 py-2">Phone</td><td>{{ teacher.phone || '—' }}</td></tr>
                <tr><td class="text-600 py-2">Address</td><td>{{ teacher.address || '—' }}</td></tr>
                <tr><td class="text-600 py-2">Qualification</td><td>{{ teacher.qualification || '—' }}</td></tr>
                <tr><td class="text-600 py-2">Specialization</td><td>{{ teacher.specialization || '—' }}</td></tr>
              </table>
            </div>
          </div>
        </p-tabPanel>

        <!-- TAB 2: Subjects -->
        <p-tabPanel header="Subjects">
          <div class="flex justify-content-between align-items-center mb-3">
            <h3 class="text-lg font-semibold m-0">Assigned Subjects</h3>
            <p-button label="Assign Subject" icon="pi pi-plus" size="small" (onClick)="showAssignDialog = true" />
          </div>

          <p-table [value]="subjects" [loading]="loadingSubjects" styleClass="p-datatable-sm">
            <ng-template pTemplate="header">
              <tr>
                <th>Code</th>
                <th>Subject</th>
                <th>Class</th>
                <th>Actions</th>
              </tr>
            </ng-template>
            <ng-template pTemplate="body" let-row>
              <tr>
                <td><span class="font-mono text-sm">{{ row.subject_code || '—' }}</span></td>
                <td>{{ row.subject_name || '—' }}</td>
                <td>{{ row.class_name || '—' }}</td>
                <td>
                  <p-button icon="pi pi-trash" [text]="true" [rounded]="true" severity="danger" size="small"
                    (onClick)="unassignSubject(row)" pTooltip="Unassign" />
                </td>
              </tr>
            </ng-template>
            <ng-template pTemplate="emptymessage">
              <tr><td colspan="4" class="text-center text-600 py-4">No subjects assigned.</td></tr>
            </ng-template>
          </p-table>
        </p-tabPanel>

        <!-- TAB 3: Schedule -->
        <p-tabPanel header="Schedule">
          <div class="overflow-x-auto">
            <table class="w-full border-collapse text-sm" style="min-width:700px">
              <thead>
                <tr>
                  <th class="border-1 surface-border p-2 text-left w-5rem">Period</th>
                  @for (day of dayLabels; track day) {
                    <th class="border-1 surface-border p-2 text-center">{{ day }}</th>
                  }
                </tr>
              </thead>
              <tbody>
                @for (period of periods; track period) {
                  <tr>
                    <td class="border-1 surface-border p-2 font-medium">P{{ period }}</td>
                    @for (day of [0,1,2,3,4,5]; track day) {
                      <td class="border-1 surface-border p-2 text-center" style="min-width:100px">
                        @if (getScheduleEntry(day, period); as entry) {
                          <div class="surface-100 border-round p-1 text-xs">
                            <div class="font-medium">{{ entry.subject_name }}</div>
                            <div class="text-600">{{ entry.section_name }}</div>
                            <div class="text-600">{{ entry.start_time }}–{{ entry.end_time }}</div>
                          </div>
                        }
                      </td>
                    }
                  </tr>
                }
              </tbody>
            </table>
          </div>
          @if (!schedule.length) {
            <p class="text-center text-600 py-4">No timetable entries found.</p>
          }
        </p-tabPanel>

      </p-tabView>
    } @else if (notFound) {
      <p-card><p class="text-center text-600">Teacher not found.</p></p-card>
    }

    <!-- Assign Subject Dialog -->
    <p-dialog header="Assign Subject" [(visible)]="showAssignDialog" [modal]="true" [style]="{width:'400px'}">
      <div class="field mt-2">
        <label>Subject <span class="text-red-500">*</span></label>
        <p-dropdown
          [(ngModel)]="selectedSubjectId"
          [options]="allSubjects"
          optionLabel="name"
          optionValue="id"
          placeholder="Select subject"
          styleClass="w-full"
        />
      </div>
      <ng-template pTemplate="footer">
        <p-button label="Cancel" severity="secondary" (onClick)="showAssignDialog = false" />
        <p-button label="Assign" icon="pi pi-check" (onClick)="assignSubject()" [loading]="assigningSubject" [disabled]="!selectedSubjectId" />
      </ng-template>
    </p-dialog>
  `
})
export class TeacherDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private teacherService = inject(TeacherService);
  private classesService = inject(ClassesService);
  private toast = inject(MessageService);

  teacher: Teacher | null = null;
  notFound = false;
  subjects: TeacherSubjectAssignment[] = [];
  schedule: TimetableEntry[] = [];
  loadingSubjects = false;

  showAssignDialog = false;
  allSubjects: Subject[] = [];
  selectedSubjectId: number | null = null;
  assigningSubject = false;

  readonly dayLabels = DAY_LABELS;
  readonly periods = [1, 2, 3, 4, 5, 6, 7, 8];

  ngOnInit(): void {
    const id = +this.route.snapshot.paramMap.get('id')!;
    this.teacherService.getTeacherById(id).subscribe({
      next: (res) => {
        this.teacher = res.data;
        this.loadSubjects(id);
        this.loadSchedule(id);
        this.loadAllSubjects();
      },
      error: () => { this.notFound = true; }
    });
  }

  private loadSubjects(id: number): void {
    this.loadingSubjects = true;
    this.teacherService.getSubjects(id).subscribe({
      next: (res) => { this.subjects = res.data.subjects; this.loadingSubjects = false; },
      error: () => { this.loadingSubjects = false; }
    });
  }

  private loadSchedule(id: number): void {
    this.teacherService.getSchedule(id).subscribe({
      next: (res) => { this.schedule = res.data.schedule; },
      error: () => {}
    });
  }

  private loadAllSubjects(): void {
    this.classesService.getSubjects(1, 100).subscribe({
      next: (res) => { this.allSubjects = res.data.subjects; },
      error: () => {}
    });
  }

  getScheduleEntry(day: number, period: number): TimetableEntry | undefined {
    return this.schedule.find(e => e.day_of_week === day && e.period_no === period);
  }

  assignSubject(): void {
    if (!this.selectedSubjectId) return;
    this.assigningSubject = true;
    this.teacherService.assignSubject(this.teacher!.id, { subject_id: this.selectedSubjectId }).subscribe({
      next: () => {
        this.toast.add({ severity: 'success', summary: 'Assigned', detail: 'Subject assigned' });
        this.showAssignDialog = false;
        this.selectedSubjectId = null;
        this.loadSubjects(this.teacher!.id);
        this.assigningSubject = false;
      },
      error: (err) => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: err.error?.message || 'Failed to assign subject' });
        this.assigningSubject = false;
      }
    });
  }

  unassignSubject(row: TeacherSubjectAssignment): void {
    this.teacherService.unassignSubject(this.teacher!.id, row.subject_id, row.class_id).subscribe({
      next: () => {
        this.toast.add({ severity: 'success', summary: 'Removed', detail: 'Subject unassigned' });
        this.loadSubjects(this.teacher!.id);
      },
      error: (err) => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: err.error?.message || 'Failed to unassign' });
      }
    });
  }
}
