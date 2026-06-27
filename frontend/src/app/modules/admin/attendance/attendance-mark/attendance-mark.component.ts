import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MessageService, ConfirmationService } from 'primeng/api';
import { DropdownModule } from 'primeng/dropdown';
import { CalendarModule } from 'primeng/calendar';
import { SelectButtonModule } from 'primeng/selectbutton';
import { ButtonModule } from 'primeng/button';
import { ToastModule } from 'primeng/toast';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { MessageModule } from 'primeng/message';
import { CardModule } from 'primeng/card';
import { ToolbarModule } from 'primeng/toolbar';
import { TableModule } from 'primeng/table';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { DividerModule } from 'primeng/divider';

import { AttendanceService, AttendanceMarkPayload } from '../../../../core/services/attendance.service';
import { ClassesService, Section } from '../../../../core/services/classes.service';
import { StudentService, Student } from '../../../../core/services/student.service';

interface StudentRow {
  student: Student;
  status: string;
}

@Component({
  selector: 'app-attendance-mark',
  standalone: true,
  imports: [
    CommonModule, FormsModule,
    DropdownModule, CalendarModule, SelectButtonModule,
    ButtonModule, ToastModule, ConfirmDialogModule,
    MessageModule, CardModule, ToolbarModule, TableModule,
    ProgressSpinnerModule, DividerModule
  ],
  providers: [MessageService, ConfirmationService],
  templateUrl: './attendance-mark.component.html'
})
export class AttendanceMarkComponent implements OnInit {
  private attendanceService = inject(AttendanceService);
  private classesService = inject(ClassesService);
  private studentService = inject(StudentService);
  private toast = inject(MessageService);
  private confirm = inject(ConfirmationService);

  // Dropdown data
  sections: Section[] = [];
  sectionOptions: { label: string; value: number }[] = [];

  // Selection state
  selectedSectionId: number | null = null;
  selectedDate: Date = new Date();
  maxDate: Date = new Date();

  // Students state
  studentRows: StudentRow[] = [];
  studentsLoading = false;
  studentsLoaded = false;

  // Submit state
  submitting = false;
  submitted = false;
  alreadyMarked = false;

  // Status options for SelectButton
  statusOptions = [
    { label: 'Present', value: 'present' },
    { label: 'Absent', value: 'absent' },
    { label: 'Late', value: 'late' }
  ];

  ngOnInit(): void {
    this.loadSections();
  }

  loadSections(): void {
    this.classesService.getSections(undefined, 1, 200).subscribe({
      next: (res) => {
        this.sections = res.data.sections;
        this.sectionOptions = this.sections.map(s => ({
          label: `${s.class_name} - Section ${s.name}`,
          value: s.id
        }));
      },
      error: () => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load sections' });
      }
    });
  }

  loadStudents(): void {
    if (!this.selectedSectionId) {
      this.toast.add({ severity: 'warn', summary: 'Warning', detail: 'Please select a section first' });
      return;
    }

    this.studentsLoading = true;
    this.studentsLoaded = false;
    this.alreadyMarked = false;
    this.submitted = false;

    this.studentService.getStudentsBySection(this.selectedSectionId).subscribe({
      next: (res) => {
        const students: Student[] = res.data.students ?? res.data ?? [];
        this.studentRows = students.map(s => ({ student: s, status: 'present' }));
        this.studentsLoaded = true;
        this.studentsLoading = false;
      },
      error: () => {
        this.studentsLoading = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load students' });
      }
    });
  }

  markAllPresent(): void {
    this.studentRows = this.studentRows.map(row => ({ ...row, status: 'present' }));
  }

  confirmSubmit(): void {
    if (!this.selectedSectionId || !this.studentRows.length) return;

    this.confirm.confirm({
      message: `Mark attendance for ${this.studentRows.length} students on ${this.formatDate(this.selectedDate)}?`,
      header: 'Confirm Attendance',
      icon: 'pi pi-check-circle',
      acceptLabel: 'Yes, Submit',
      rejectLabel: 'Cancel',
      acceptButtonStyleClass: 'p-button-success',
      accept: () => this.submitAttendance()
    });
  }

  private submitAttendance(): void {
    this.submitting = true;
    this.alreadyMarked = false;

    const payload: AttendanceMarkPayload = {
      section_id: this.selectedSectionId!,
      date: this.formatDate(this.selectedDate),
      records: this.studentRows.map(row => ({
        student_id: row.student.id,
        status: row.status as any
      }))
    };

    this.attendanceService.markAttendance(payload).subscribe({
      next: (res) => {
        this.submitting = false;
        this.submitted = true;
        this.toast.add({
          severity: 'success',
          summary: 'Attendance Marked',
          detail: `Successfully marked attendance for ${res.data.records_created} students`
        });
      },
      error: (err) => {
        this.submitting = false;
        if (err.status === 409) {
          this.alreadyMarked = true;
        } else {
          this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to mark attendance' });
        }
      }
    });
  }

  private formatDate(date: Date): string {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }

  getStatusSeverity(status: string): string {
    switch (status) {
      case 'present': return 'success';
      case 'absent': return 'danger';
      case 'late': return 'warning';
      default: return 'info';
    }
  }

  resetForm(): void {
    this.selectedSectionId = null;
    this.selectedDate = new Date();
    this.studentRows = [];
    this.studentsLoaded = false;
    this.submitted = false;
    this.alreadyMarked = false;
  }
}
