import { Component, inject, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, Router } from '@angular/router';
import { MessageService } from 'primeng/api';

import { CardModule } from 'primeng/card';
import { ToolbarModule } from 'primeng/toolbar';
import { ButtonModule } from 'primeng/button';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ToastModule } from 'primeng/toast';
import { FileUploadModule, FileUpload } from 'primeng/fileupload';
import { MessageModule } from 'primeng/message';

import {
  StudentService,
  BulkPreviewRow,
  BulkSummary,
  BulkCommitData
} from '../../../../core/services/student.service';

type Stage = 'upload' | 'preview' | 'result';

@Component({
  selector: 'app-student-import',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    CardModule,
    ToolbarModule,
    ButtonModule,
    TableModule,
    TagModule,
    ToastModule,
    FileUploadModule,
    MessageModule
  ],
  providers: [MessageService],
  template: `
    <p-toast position="top-right" />

    <p-card>
      <p-toolbar styleClass="mb-4">
        <ng-template pTemplate="left">
          <h2 class="text-xl font-bold text-900 m-0">Bulk Import Students</h2>
        </ng-template>
        <ng-template pTemplate="right">
          <p-button
            label="Back to Students"
            icon="pi pi-arrow-left"
            [text]="true"
            routerLink="/admin/students"
          />
        </ng-template>
      </p-toolbar>

      <!-- ── Stage: Upload ─────────────────────────────────────────────── -->
      <div *ngIf="stage === 'upload'">
        <p class="text-700 line-height-3 mb-3">
          Download the template, fill in one student per row, then upload it here.
          You'll see a preview and can fix any issues before anything is saved.
          Rows with an email get a login account and a temporary password emailed
          to the student.
        </p>

        <div class="flex flex-column sm:flex-row gap-3 align-items-start sm:align-items-center">
          <p-button
            label="Download Template (.xlsx)"
            icon="pi pi-download"
            severity="secondary"
            [outlined]="true"
            [loading]="downloadingTemplate"
            (onClick)="downloadTemplate()"
          />

          <p-fileUpload
            #uploader
            mode="basic"
            chooseLabel="Choose Excel file"
            chooseIcon="pi pi-upload"
            accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            [auto]="true"
            [customUpload]="true"
            [maxFileSize]="5000000"
            (uploadHandler)="onFileChosen($event)"
          />
        </div>

        <p-message
          *ngIf="loadingPreview"
          severity="info"
          text="Validating your file…"
          styleClass="mt-3 block"
        />
      </div>

      <!-- ── Stage: Preview ────────────────────────────────────────────── -->
      <div *ngIf="stage === 'preview'">
        <div class="flex flex-wrap gap-2 mb-3">
          <p-tag [value]="summary.total + ' rows'" severity="secondary" />
          <p-tag [value]="summary.valid + ' ready'" severity="success" />
          <p-tag *ngIf="summary.duplicate" [value]="summary.duplicate + ' duplicate'" severity="warning" />
          <p-tag *ngIf="summary.error" [value]="summary.error + ' with errors'" severity="danger" />
        </div>

        <p-message
          *ngIf="summary.valid === 0"
          severity="warn"
          text="No rows are ready to import. Fix the issues below and upload again."
          styleClass="mb-3 block"
        />

        <p-table [value]="previewRows" [scrollable]="true" styleClass="p-datatable-sm" [paginator]="previewRows.length > 25" [rows]="25">
          <ng-template pTemplate="header">
            <tr>
              <th style="width:3rem">
                <input type="checkbox" [checked]="allValidSelected()" (change)="toggleAll($event)"
                       [disabled]="summary.valid === 0" title="Select all importable rows" />
              </th>
              <th style="width:4rem">Row</th>
              <th>Student</th>
              <th style="width:6rem">Login</th>
              <th style="width:8rem">Status</th>
              <th>Issues</th>
            </tr>
          </ng-template>
          <ng-template pTemplate="body" let-r>
            <tr [class.surface-100]="r.status !== 'valid'">
              <td>
                <input type="checkbox"
                       *ngIf="r.status === 'valid'"
                       [checked]="selected.has(r.row)"
                       (change)="toggleRow(r.row)" />
              </td>
              <td>{{ r.row }}</td>
              <td>{{ r.label }}</td>
              <td>
                <i *ngIf="r.will_create_login" class="pi pi-check text-green-600" title="Login account will be created"></i>
                <span *ngIf="!r.will_create_login" class="text-500">—</span>
              </td>
              <td><p-tag [value]="r.status" [severity]="statusSeverity(r.status)" /></td>
              <td class="text-sm text-600">{{ errorText(r.errors) }}</td>
            </tr>
          </ng-template>
          <ng-template pTemplate="emptymessage">
            <tr><td colspan="6" class="text-center text-600 py-4">No rows found in the file.</td></tr>
          </ng-template>
        </p-table>

        <div class="flex flex-column sm:flex-row justify-content-between gap-2 mt-4">
          <p-button label="Choose a different file" icon="pi pi-refresh" [text]="true" (onClick)="reset()" />
          <p-button
            [label]="'Import ' + selected.size + ' student' + (selected.size === 1 ? '' : 's')"
            icon="pi pi-check"
            [loading]="committing"
            [disabled]="selected.size === 0"
            (onClick)="commit()"
          />
        </div>
      </div>

      <!-- ── Stage: Result ─────────────────────────────────────────────── -->
      <div *ngIf="stage === 'result'">
        <div class="flex flex-wrap gap-2 mb-3">
          <p-tag [value]="result!.summary.created + ' created'" severity="success" />
          <p-tag *ngIf="skippedCount() > 0" [value]="skippedCount() + ' skipped'" severity="warning" />
        </div>

        <p-message
          *ngIf="result!.emails.with_login > 0 && result!.emails.configured"
          severity="success"
          [text]="result!.emails.queued + ' credential email(s) are being sent to students.'"
          styleClass="mb-3 block"
        />
        <p-message
          *ngIf="result!.emails.with_login > 0 && !result!.emails.configured"
          severity="warn"
          text="Students were created, but no email server is configured for this school, so credentials were NOT sent. Set it up under School Settings, then reset those students' passwords."
          styleClass="mb-3 block"
        />

        <p-table *ngIf="failedRows().length" [value]="failedRows()" styleClass="p-datatable-sm">
          <ng-template pTemplate="header">
            <tr><th style="width:4rem">Row</th><th>Student</th><th style="width:8rem">Status</th><th>Reason</th></tr>
          </ng-template>
          <ng-template pTemplate="body" let-r>
            <tr>
              <td>{{ r.row }}</td>
              <td>{{ r.label }}</td>
              <td><p-tag [value]="r.status" [severity]="statusSeverity(r.status)" /></td>
              <td class="text-sm text-600">{{ errorText(r.errors) }}</td>
            </tr>
          </ng-template>
        </p-table>

        <div class="flex flex-column sm:flex-row justify-content-between gap-2 mt-4">
          <p-button label="Import another file" icon="pi pi-plus" [text]="true" (onClick)="reset()" />
          <p-button label="Go to Students" icon="pi pi-arrow-right" (onClick)="goToStudents()" />
        </div>
      </div>
    </p-card>
  `
})
export class StudentImportComponent {
  private studentService = inject(StudentService);
  private toast = inject(MessageService);
  private router = inject(Router);

  @ViewChild('uploader') uploader?: FileUpload;

  stage: Stage = 'upload';
  downloadingTemplate = false;
  loadingPreview = false;
  committing = false;

  previewRows: BulkPreviewRow[] = [];
  summary: BulkSummary = { total: 0, valid: 0, error: 0, duplicate: 0, created: 0 };
  selected = new Set<number>();
  result: BulkCommitData | null = null;

  // ── Template download ──────────────────────────────────────────────────
  downloadTemplate(): void {
    this.downloadingTemplate = true;
    this.studentService.downloadBulkTemplate().subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'student_import_template.xlsx';
        a.click();
        URL.revokeObjectURL(url);
        this.downloadingTemplate = false;
      },
      error: () => {
        this.downloadingTemplate = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to download template' });
      }
    });
  }

  // ── Upload → preview ───────────────────────────────────────────────────
  onFileChosen(event: { files: File[] }): void {
    const file = event.files?.[0];
    this.uploader?.clear(); // allow re-choosing the same file later
    if (!file) return;
    this.loadingPreview = true;
    this.studentService.bulkPreview(file).subscribe({
      next: (res) => {
        this.previewRows = res.data.rows;
        this.summary = res.data.summary;
        this.selected = new Set(
          this.previewRows.filter((r) => r.status === 'valid').map((r) => r.row)
        );
        this.stage = 'preview';
        this.loadingPreview = false;
      },
      error: (err) => {
        this.loadingPreview = false;
        this.toast.add({
          severity: 'error',
          summary: 'Could not read file',
          detail: err?.error?.message || 'Please upload a valid .xlsx file.'
        });
      }
    });
  }

  // ── Selection ──────────────────────────────────────────────────────────
  toggleRow(row: number): void {
    if (this.selected.has(row)) this.selected.delete(row);
    else this.selected.add(row);
  }

  allValidSelected(): boolean {
    return this.summary.valid > 0 && this.selected.size === this.summary.valid;
  }

  toggleAll(event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    this.selected = checked
      ? new Set(this.previewRows.filter((r) => r.status === 'valid').map((r) => r.row))
      : new Set();
  }

  // ── Commit ─────────────────────────────────────────────────────────────
  commit(): void {
    const rows = this.previewRows
      .filter((r) => r.status === 'valid' && this.selected.has(r.row))
      .map((r) => ({ ...r.data, _row: r.row }));

    if (!rows.length) return;
    this.committing = true;
    this.studentService.bulkCommit(rows).subscribe({
      next: (res) => {
        this.result = res.data;
        this.committing = false;
        this.stage = 'result';
        this.toast.add({
          severity: 'success',
          summary: 'Import complete',
          detail: `${res.data.summary.created} student(s) created`
        });
      },
      error: (err) => {
        this.committing = false;
        this.toast.add({
          severity: 'error',
          summary: 'Import failed',
          detail: err?.error?.message || 'Please try again.'
        });
      }
    });
  }

  // ── Result helpers ───────────────────────────────────────────────────────
  skippedCount(): number {
    if (!this.result) return 0;
    const s = this.result.summary;
    return s.error + s.duplicate;
  }

  failedRows() {
    return this.result?.rows.filter((r) => r.status !== 'created') ?? [];
  }

  // ── Misc ───────────────────────────────────────────────────────────────
  reset(): void {
    this.stage = 'upload';
    this.previewRows = [];
    this.summary = { total: 0, valid: 0, error: 0, duplicate: 0, created: 0 };
    this.selected = new Set();
    this.result = null;
  }

  goToStudents(): void {
    this.router.navigate(['/admin/students']);
  }

  statusSeverity(status: string): 'success' | 'warning' | 'danger' {
    switch (status) {
      case 'valid':
      case 'created':
        return 'success';
      case 'duplicate':
        return 'warning';
      default:
        return 'danger';
    }
  }

  errorText(errors: Record<string, string[]>): string {
    if (!errors) return '';
    return Object.entries(errors)
      .map(([field, msgs]) => (field === '_' ? msgs.join(', ') : `${field}: ${msgs.join(', ')}`))
      .join('; ');
  }
}
