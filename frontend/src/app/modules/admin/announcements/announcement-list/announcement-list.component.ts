import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MessageService } from 'primeng/api';
import { TableModule } from 'primeng/table';
import { DialogModule } from 'primeng/dialog';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { InputTextareaModule } from 'primeng/inputtextarea';
import { MultiSelectModule } from 'primeng/multiselect';
import { DropdownModule } from 'primeng/dropdown';
import { CalendarModule } from 'primeng/calendar';
import { TagModule } from 'primeng/tag';
import { ToolbarModule } from 'primeng/toolbar';
import { ToastModule } from 'primeng/toast';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { TooltipModule } from 'primeng/tooltip';

import {
  AnnouncementService,
  Announcement,
  AnnouncementPayload,
  AnnouncementStatus,
} from '../../../../core/services/announcement.service';
import { ClassesService } from '../../../../core/services/classes.service';

@Component({
  selector: 'app-announcement-list',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    TableModule,
    DialogModule,
    ButtonModule,
    InputTextModule,
    InputTextareaModule,
    MultiSelectModule,
    DropdownModule,
    CalendarModule,
    TagModule,
    ToolbarModule,
    ToastModule,
    ProgressSpinnerModule,
    TooltipModule,
  ],
  providers: [MessageService],
  templateUrl: './announcement-list.component.html',
})
export class AnnouncementListComponent implements OnInit {
  private announcementService = inject(AnnouncementService);
  private classesService = inject(ClassesService);
  private fb = inject(FormBuilder);
  private toast = inject(MessageService);

  announcements: Announcement[] = [];
  loading = false;
  dialogVisible = false;
  saving = false;
  publishingId: number | null = null;
  isEdit = false;
  editingId: number | null = null;

  roleOptions = [
    { label: 'Admin', value: 'admin' },
    { label: 'Teacher', value: 'teacher' },
    { label: 'Student', value: 'student' },
    { label: 'Parent', value: 'parent' },
  ];

  classOptions: { label: string; value: number }[] = [];

  statusOptions = [
    { label: 'Draft', value: 'draft' },
    { label: 'Published', value: 'published' },
    { label: 'Archived', value: 'archived' },
  ];

  form: FormGroup = this.fb.group({
    title: ['', Validators.required],
    content: ['', Validators.required],
    target_roles: [[]],
    target_class_ids: [[]],
    expires_at: [null],
    status: [null],
  });

  ngOnInit(): void {
    this.loadClasses();
    this.loadAnnouncements();
  }

  loadClasses(): void {
    this.classesService.getClasses(1, 100).subscribe({
      next: (res) => {
        const classes = res.data?.classes ?? [];
        this.classOptions = classes.map((c) => ({ label: c.name, value: c.id }));
      },
      error: () => {
        // non-blocking; class targeting just stays empty
      },
    });
  }

  loadAnnouncements(): void {
    this.loading = true;
    this.announcementService.getAll().subscribe({
      next: (res) => {
        this.announcements = res.data?.announcements ?? [];
        this.loading = false;
      },
      error: () => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load announcements' });
        this.loading = false;
      },
    });
  }

  openDialog(a?: Announcement): void {
    this.form.reset({ target_roles: [], target_class_ids: [], status: null });
    this.isEdit = false;
    this.editingId = null;

    if (a) {
      this.isEdit = true;
      this.editingId = a.id;
      this.form.patchValue({
        title: a.title,
        content: a.content,
        target_roles: a.target_roles ?? [],
        target_class_ids: a.target_class_ids ?? [],
        expires_at: a.expires_at ? new Date(a.expires_at) : null,
        status: a.status,
      });
    }

    this.dialogVisible = true;
  }

  closeDialog(): void {
    this.dialogVisible = false;
    this.form.reset({ target_roles: [], target_class_ids: [], status: null });
  }

  save(): void {
    if (this.form.invalid) return;

    this.saving = true;
    const raw = this.form.value;
    const roles: string[] = raw.target_roles ?? [];
    const classIds: number[] = raw.target_class_ids ?? [];

    const payload: AnnouncementPayload = {
      title: raw.title,
      content: raw.content,
      // empty selection => school-wide / all classes => send null
      target_roles: roles.length > 0 ? roles : null,
      target_class_ids: classIds.length > 0 ? classIds : null,
      expires_at: raw.expires_at ? this.formatDateTime(raw.expires_at) : null,
    };

    if (this.isEdit && raw.status) {
      payload.status = raw.status as AnnouncementStatus;
    }

    const request$ = this.isEdit && this.editingId !== null
      ? this.announcementService.update(this.editingId, payload)
      : this.announcementService.create(payload);

    request$.subscribe({
      next: () => {
        this.saving = false;
        this.dialogVisible = false;
        this.toast.add({
          severity: 'success',
          summary: 'Success',
          detail: this.isEdit ? 'Announcement updated successfully' : 'Announcement created successfully',
        });
        this.loadAnnouncements();
      },
      error: (err: any) => {
        this.saving = false;
        const detail = err?.error?.message ?? (this.isEdit ? 'Failed to update announcement' : 'Failed to create announcement');
        this.toast.add({ severity: 'error', summary: 'Error', detail });
      },
    });
  }

  publish(a: Announcement): void {
    this.publishingId = a.id;
    this.announcementService.publish(a.id).subscribe({
      next: (res) => {
        this.publishingId = null;
        const count = res.data?.notified_count ?? 0;
        this.toast.add({
          severity: 'success',
          summary: 'Published',
          detail: `Notified ${count} users`,
          life: 5000,
        });
        this.loadAnnouncements();
      },
      error: (err: any) => {
        this.publishingId = null;
        const detail = err?.error?.message ?? 'Failed to publish announcement';
        this.toast.add({ severity: 'error', summary: 'Error', detail });
      },
    });
  }

  getStatusSeverity(status: string): 'warning' | 'success' | 'secondary' | 'contrast' {
    const map: Record<string, 'warning' | 'success' | 'secondary' | 'contrast'> = {
      draft: 'warning',
      published: 'success',
      archived: 'secondary',
    };
    return map[status] ?? 'contrast';
  }

  getTargetLabel(a: Announcement): string {
    const parts: string[] = [];
    if (!a.target_roles || a.target_roles.length === 0) {
      parts.push('School-wide');
    } else {
      parts.push(a.target_roles.map((r) => this.capitalize(r)).join(', '));
    }
    if (a.target_class_ids && a.target_class_ids.length > 0) {
      const n = a.target_class_ids.length;
      parts.push(`${n} class${n === 1 ? '' : 'es'}`);
    }
    return parts.join(' · ');
  }

  private capitalize(s: string): string {
    return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
  }

  private formatDateTime(date: Date): string {
    return new Date(date).toISOString();
  }
}
