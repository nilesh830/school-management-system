import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import {
  FormBuilder,
  FormControl,
  ReactiveFormsModule,
  Validators,
  AbstractControl,
  ValidationErrors
} from '@angular/forms';
import { MessageService, ConfirmationService } from 'primeng/api';

import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { TabViewModule } from 'primeng/tabview';
import { TagModule } from 'primeng/tag';
import { ToastModule } from 'primeng/toast';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { InputTextareaModule } from 'primeng/inputtextarea';
import { InputNumberModule } from 'primeng/inputnumber';
import { DropdownModule } from 'primeng/dropdown';
import { CalendarModule } from 'primeng/calendar';
import { TableModule } from 'primeng/table';
import { FileUploadModule } from 'primeng/fileupload';
import { ToolbarModule } from 'primeng/toolbar';
import { DividerModule } from 'primeng/divider';
import { ToggleButtonModule } from 'primeng/togglebutton';
import { AvatarModule } from 'primeng/avatar';
import { SkeletonModule } from 'primeng/skeleton';
import { TooltipModule } from 'primeng/tooltip';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { MessageModule } from 'primeng/message';

import { ExamService } from '../../../../core/services/exam.service';
import { ClassesService } from '../../../../core/services/classes.service';

import {
  StudentService,
  Student,
  Parent,
  StudentDocument,
  TransferPayload,
  StatusUpdatePayload
} from '../../../../core/services/student.service';

/** Format a JS Date to YYYY-MM-DD string */
function toIsoDate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

/** Rejects dates in the future */
function noFutureDate(control: AbstractControl): ValidationErrors | null {
  if (!control.value) return null;
  const selected = control.value instanceof Date ? control.value : new Date(control.value);
  const today = new Date();
  today.setHours(23, 59, 59, 999);
  return selected > today ? { futureDate: true } : null;
}

@Component({
  selector: 'app-student-detail',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    ReactiveFormsModule,
    ButtonModule,
    CardModule,
    TabViewModule,
    TagModule,
    ToastModule,
    ConfirmDialogModule,
    DialogModule,
    InputTextModule,
    InputTextareaModule,
    InputNumberModule,
    DropdownModule,
    CalendarModule,
    TableModule,
    FileUploadModule,
    ToolbarModule,
    DividerModule,
    ToggleButtonModule,
    AvatarModule,
    SkeletonModule,
    TooltipModule,
    ProgressSpinnerModule,
    MessageModule
  ],
  providers: [MessageService, ConfirmationService],
  templateUrl: './student-detail.component.html'
})
export class StudentDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private fb = inject(FormBuilder);
  private studentService = inject(StudentService);
  private examService = inject(ExamService);
  private classesService = inject(ClassesService);
  private toast = inject(MessageService);
  private confirm = inject(ConfirmationService);

  // ── Page state ────────────────────────────────────────────────────────────
  studentId!: number;
  student: Student | null = null;
  loading = false;
  editMode = false;
  savingEdit = false;

  // ── Documents ─────────────────────────────────────────────────────────────
  documents: StudentDocument[] = [];
  loadingDocs = false;
  uploadingDoc = false;
  docTypeControl = new FormControl('birth_certificate', { nonNullable: true });

  documentTypeOptions = [
    { label: 'Birth Certificate', value: 'birth_certificate' },
    { label: 'Photo', value: 'photo' },
    { label: 'Previous Certificate', value: 'previous_certificate' },
    { label: 'ID Proof', value: 'id_proof' },
    { label: 'Other', value: 'other' }
  ];

  // ── Parents ───────────────────────────────────────────────────────────────
  parents: Parent[] = [];
  loadingParents = false;
  linkingParent = false;
  parentDirectory: Parent[] = [];
  loadingDirectory = false;

  // ── Report Cards ──────────────────────────────────────────────────────────
  exams: any[] = [];
  loadingExams = false;
  downloadingExamId: number | null = null;

  // ── Dialogs ───────────────────────────────────────────────────────────────
  showTransferDialog = false;
  transferring = false;
  sectionOptions: { label: string; value: number }[] = [];
  loadingSections = false;

  showStatusDialog = false;
  updatingStatus = false;

  // ── Status options ────────────────────────────────────────────────────────
  statusOptions = [
    { label: 'Active', value: 'active' },
    { label: 'Alumni', value: 'alumni' },
    { label: 'Transferred', value: 'transferred' },
    { label: 'Expelled', value: 'expelled' }
  ];

  maxDate = new Date();

  // ── Edit form (Tab 1 — Personal Info) ────────────────────────────────────
  editForm = this.fb.group({
    first_name: ['', [Validators.required, Validators.maxLength(100)]],
    last_name: ['', [Validators.required, Validators.maxLength(100)]],
    date_of_birth: [null as Date | null, [Validators.required, noFutureDate]],
    gender: ['', Validators.required],
    blood_group: [null as string | null],
    phone: [null as string | null, Validators.maxLength(20)],
    address: [null as string | null]
  });

  genderOptions = [
    { label: 'Male', value: 'Male' },
    { label: 'Female', value: 'Female' },
    { label: 'Other', value: 'Other' }
  ];

  bloodGroupOptions = [
    { label: 'A+', value: 'A+' },
    { label: 'A-', value: 'A-' },
    { label: 'B+', value: 'B+' },
    { label: 'B-', value: 'B-' },
    { label: 'AB+', value: 'AB+' },
    { label: 'AB-', value: 'AB-' },
    { label: 'O+', value: 'O+' },
    { label: 'O-', value: 'O-' }
  ];

  // ── Transfer form ─────────────────────────────────────────────────────────
  transferForm = this.fb.group({
    new_section_id: [null as number | null, [Validators.required, Validators.min(1)]],
    effective_date: [null as Date | null, Validators.required],
    reason: [null as string | null]
  });

  // ── Status form ───────────────────────────────────────────────────────────
  statusForm = this.fb.group({
    status: ['', Validators.required],
    leaving_date: [null as Date | null]
  });

  // ── Link parent form ──────────────────────────────────────────────────────
  linkParentForm = this.fb.group({
    parent_id: [null as number | null, [Validators.required, Validators.min(1)]],
    is_primary_contact: [false]
  });

  // ── Getters ───────────────────────────────────────────────────────────────
  get ef() { return this.editForm.controls; }
  get tf() { return this.transferForm.controls; }
  get sf() { return this.statusForm.controls; }
  get lf() { return this.linkParentForm.controls; }

  get fullName(): string {
    if (!this.student) return '';
    return `${this.student.first_name} ${this.student.last_name}`;
  }

  get avatarLabel(): string {
    if (!this.student) return '?';
    return `${this.student.first_name[0]}${this.student.last_name[0]}`.toUpperCase();
  }

  get statusSeverity(): 'success' | 'info' | 'warning' | 'danger' {
    const map: Record<string, 'success' | 'info' | 'warning' | 'danger'> = {
      active: 'success',
      alumni: 'info',
      transferred: 'warning',
      expelled: 'danger'
    };
    return map[this.student?.status ?? 'active'] ?? 'info';
  }

  // ── Lifecycle ─────────────────────────────────────────────────────────────

  ngOnInit(): void {
    this.studentId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadStudent();
  }

  // ── Student load ──────────────────────────────────────────────────────────

  loadStudent(): void {
    this.loading = true;
    this.studentService.getStudentById(this.studentId).subscribe({
      next: (res) => {
        this.student = res.data;
        this.loading = false;
        this.loadDocuments();
        this.loadParents();
        this.loadParentDirectory();
      },
      error: (err) => {
        this.loading = false;
        if (err?.status === 403) {
          this.toast.add({ severity: 'error', summary: 'Access Denied', detail: 'You do not have permission to view this student.' });
        } else if (err?.status === 404) {
          this.toast.add({ severity: 'error', summary: 'Not Found', detail: 'Student not found.' });
          this.router.navigate(['/admin/students']);
        } else {
          this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load student.' });
        }
      }
    });
  }

  // ── Edit (Tab 1) ──────────────────────────────────────────────────────────

  enterEditMode(): void {
    if (!this.student) return;
    this.editForm.patchValue({
      first_name: this.student.first_name,
      last_name: this.student.last_name,
      date_of_birth: this.student.date_of_birth ? new Date(this.student.date_of_birth) : null,
      gender: this.student.gender,
      blood_group: this.student.blood_group ?? null,
      phone: this.student.phone ?? null,
      address: this.student.address ?? null
    });
    this.editMode = true;
  }

  cancelEdit(): void {
    this.editForm.reset();
    this.editMode = false;
  }

  saveEdit(): void {
    if (this.editForm.invalid) {
      this.editForm.markAllAsTouched();
      return;
    }
    const raw = this.editForm.getRawValue();
    const payload: any = {
      first_name: raw.first_name!,
      last_name: raw.last_name!,
      date_of_birth: raw.date_of_birth ? toIsoDate(raw.date_of_birth) : undefined,
      gender: raw.gender,
      blood_group: raw.blood_group ?? null,
      phone: raw.phone ?? null,
      address: raw.address ?? null
    };

    this.savingEdit = true;
    this.studentService.updateStudent(this.studentId, payload).subscribe({
      next: (res) => {
        this.student = res.data;
        this.savingEdit = false;
        this.editMode = false;
        this.toast.add({ severity: 'success', summary: 'Saved', detail: 'Student profile updated.' });
      },
      error: (err) => {
        this.savingEdit = false;
        const body = err?.error;
        if (err?.status === 422 && body?.errors) {
          const msgs = Object.entries(body.errors as Record<string, string[]>)
            .map(([f, e]) => `${f}: ${(e as string[]).join(', ')}`)
            .join('; ');
          this.toast.add({ severity: 'error', summary: 'Validation Error', detail: msgs });
        } else {
          this.toast.add({ severity: 'error', summary: 'Error', detail: body?.message || 'Failed to update student.' });
        }
      }
    });
  }

  isInvalid(control: AbstractControl): boolean {
    return control.invalid && (control.dirty || control.touched);
  }

  // ── Status change (Tab 2) ─────────────────────────────────────────────────

  openStatusDialog(): void {
    this.statusForm.patchValue({
      status: this.student?.status ?? 'active',
      leaving_date: null
    });
    this.showStatusDialog = true;
  }

  confirmStatusChange(): void {
    if (this.statusForm.invalid) {
      this.statusForm.markAllAsTouched();
      return;
    }
    const raw = this.statusForm.getRawValue();
    const payload: StatusUpdatePayload = {
      status: raw.status as StatusUpdatePayload['status'],
      leaving_date: raw.leaving_date ? toIsoDate(raw.leaving_date) : null
    };

    this.updatingStatus = true;
    this.studentService.updateStudentStatus(this.studentId, payload).subscribe({
      next: (res) => {
        this.student = res.data;
        this.updatingStatus = false;
        this.showStatusDialog = false;
        this.toast.add({ severity: 'success', summary: 'Status Updated', detail: `Status set to ${payload.status}.` });
      },
      error: (err) => {
        this.updatingStatus = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: err?.error?.message || 'Failed to update status.' });
      }
    });
  }

  quickDeactivate(): void {
    this.confirm.confirm({
      message: `Set ${this.fullName} as Alumni with today's date?`,
      header: 'Confirm Deactivation',
      icon: 'pi pi-exclamation-triangle',
      acceptButtonStyleClass: 'p-button-warning',
      accept: () => {
        const payload: StatusUpdatePayload = {
          status: 'alumni',
          leaving_date: toIsoDate(new Date())
        };
        this.studentService.updateStudentStatus(this.studentId, payload).subscribe({
          next: (res) => {
            this.student = res.data;
            this.toast.add({ severity: 'info', summary: 'Deactivated', detail: `${this.fullName} set to Alumni.` });
          },
          error: (err) => {
            this.toast.add({ severity: 'error', summary: 'Error', detail: err?.error?.message || 'Failed to deactivate student.' });
          }
        });
      }
    });
  }

  // ── Transfer (header button) ──────────────────────────────────────────────

  openTransferDialog(): void {
    this.transferForm.reset();
    this.showTransferDialog = true;
    this.loadSectionOptions();
  }

  private loadSectionOptions(): void {
    this.loadingSections = true;
    const currentSectionId = this.student?.current_section?.section_id ?? null;
    this.classesService.getSections(undefined, 1, 100).subscribe({
      next: (res) => {
        this.sectionOptions = (res.data.sections ?? [])
          .filter((s) => s.id !== currentSectionId) // can't transfer to the same section
          .map((s) => ({
            label: s.class_name ? `${s.class_name} — ${s.name}` : s.name,
            value: s.id
          }));
        this.loadingSections = false;
      },
      error: () => { this.loadingSections = false; }
    });
  }

  confirmTransfer(): void {
    if (this.transferForm.invalid) {
      this.transferForm.markAllAsTouched();
      return;
    }
    const raw = this.transferForm.getRawValue();
    const payload: TransferPayload = {
      new_section_id: raw.new_section_id!,
      effective_date: toIsoDate(raw.effective_date!),
      reason: raw.reason ?? null
    };

    this.transferring = true;
    this.studentService.transferStudent(this.studentId, payload).subscribe({
      next: () => {
        this.transferring = false;
        this.showTransferDialog = false;
        this.toast.add({ severity: 'success', summary: 'Transferred', detail: 'Student transferred successfully.' });
        this.loadStudent();
      },
      error: (err) => {
        this.transferring = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: err?.error?.message || 'Transfer failed.' });
      }
    });
  }

  // ── Documents (Tab 3) ─────────────────────────────────────────────────────

  loadDocuments(): void {
    this.loadingDocs = true;
    this.studentService.getDocuments(this.studentId).subscribe({
      next: (res) => {
        this.documents = res.data ?? [];
        this.loadingDocs = false;
      },
      error: () => {
        this.loadingDocs = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load documents.' });
      }
    });
  }

  onFileSelect(event: any): void {
    const file: File = event.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', this.docTypeControl.value);

    this.uploadingDoc = true;
    this.studentService.uploadDocument(this.studentId, formData).subscribe({
      next: (res) => {
        this.uploadingDoc = false;
        this.documents = [...this.documents, res.data];
        this.toast.add({ severity: 'success', summary: 'Uploaded', detail: 'Document uploaded successfully.' });
      },
      error: (err) => {
        this.uploadingDoc = false;
        this.toast.add({ severity: 'error', summary: 'Upload Failed', detail: err?.error?.message || 'Failed to upload document.' });
      }
    });
  }

  confirmDeleteDocument(doc: StudentDocument): void {
    this.confirm.confirm({
      message: `Delete document "${doc.file_name}"?`,
      header: 'Confirm Delete',
      icon: 'pi pi-trash',
      acceptButtonStyleClass: 'p-button-danger',
      accept: () => {
        this.studentService.deleteDocument(this.studentId, doc.id).subscribe({
          next: () => {
            this.documents = this.documents.filter(d => d.id !== doc.id);
            this.toast.add({ severity: 'success', summary: 'Deleted', detail: 'Document deleted.' });
          },
          error: (err) => {
            this.toast.add({ severity: 'error', summary: 'Error', detail: err?.error?.message || 'Failed to delete document.' });
          }
        });
      }
    });
  }

  docTypeLabel(value: string): string {
    return this.documentTypeOptions.find(o => o.value === value)?.label ?? value;
  }

  // ── Parents (Tab 4) ───────────────────────────────────────────────────────

  loadParents(): void {
    this.loadingParents = true;
    this.studentService.getStudentParents(this.studentId).subscribe({
      next: (res) => {
        this.parents = res.data ?? [];
        this.loadingParents = false;
      },
      error: () => {
        this.loadingParents = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load parent records.' });
      }
    });
  }

  loadParentDirectory(): void {
    this.loadingDirectory = true;
    this.studentService.listParents().subscribe({
      next: (res) => {
        this.parentDirectory = res.data ?? [];
        this.loadingDirectory = false;
      },
      error: () => {
        this.loadingDirectory = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load parent directory.' });
      }
    });
  }

  linkParent(): void {
    if (this.linkParentForm.invalid) {
      this.linkParentForm.markAllAsTouched();
      return;
    }
    const raw = this.linkParentForm.getRawValue();
    this.linkingParent = true;
    this.studentService.linkParent(this.studentId, raw.parent_id!, raw.is_primary_contact ?? false).subscribe({
      next: () => {
        this.linkingParent = false;
        this.linkParentForm.reset({ is_primary_contact: false });
        this.toast.add({ severity: 'success', summary: 'Linked', detail: 'Parent linked successfully.' });
        this.loadParents();
      },
      error: (err) => {
        this.linkingParent = false;
        const body = err?.error;
        if (err?.status === 404) {
          this.toast.add({ severity: 'error', summary: 'Not Found', detail: 'Parent ID not found.' });
        } else if (err?.status === 409) {
          this.toast.add({ severity: 'warn', summary: 'Already Linked', detail: 'This parent is already linked.' });
        } else {
          this.toast.add({ severity: 'error', summary: 'Error', detail: body?.message || 'Failed to link parent.' });
        }
      }
    });
  }

  confirmUnlinkParent(parent: Parent): void {
    this.confirm.confirm({
      message: `Unlink ${parent.first_name} ${parent.last_name} from this student?`,
      header: 'Confirm Unlink',
      icon: 'pi pi-user-minus',
      acceptButtonStyleClass: 'p-button-danger',
      accept: () => {
        this.studentService.unlinkParent(this.studentId, parent.id).subscribe({
          next: () => {
            this.parents = this.parents.filter(p => p.id !== parent.id);
            this.toast.add({ severity: 'success', summary: 'Unlinked', detail: 'Parent unlinked.' });
          },
          error: (err) => {
            this.toast.add({ severity: 'error', summary: 'Error', detail: err?.error?.message || 'Failed to unlink parent.' });
          }
        });
      }
    });
  }

  // ── Report Cards (Tab 5) ──────────────────────────────────────────────────

  loadExams(): void {
    const sectionId = this.student?.current_section?.id;
    if (!sectionId) return;
    this.loadingExams = true;
    this.examService.getExams(sectionId).subscribe({
      next: (res) => {
        this.exams = res.data?.exams ?? [];
        this.loadingExams = false;
      },
      error: () => {
        this.loadingExams = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load exams.' });
      }
    });
  }

  downloadReportCard(examId: number): void {
    this.downloadingExamId = examId;
    this.examService.downloadReportCard(examId, this.studentId).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `report_card_${this.studentId}_${examId}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
        this.downloadingExamId = null;
      },
      error: () => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to download report card.' });
        this.downloadingExamId = null;
      }
    });
  }
}
