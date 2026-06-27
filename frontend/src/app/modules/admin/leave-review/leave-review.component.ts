import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule, FormBuilder } from '@angular/forms';
import { HttpClient, HttpParams } from '@angular/common/http';
import { ButtonModule } from 'primeng/button';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { DialogModule } from 'primeng/dialog';
import { DropdownModule } from 'primeng/dropdown';
import { InputTextareaModule } from 'primeng/inputtextarea';
import { ToolbarModule } from 'primeng/toolbar';
import { ToastModule } from 'primeng/toast';
import { SkeletonModule } from 'primeng/skeleton';
import { MessageModule } from 'primeng/message';
import { TooltipModule } from 'primeng/tooltip';
import { MessageService } from 'primeng/api';

@Component({
  selector: 'app-leave-review',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormsModule,
    ButtonModule, TableModule, TagModule, DialogModule,
    DropdownModule, InputTextareaModule, ToolbarModule,
    ToastModule, SkeletonModule, MessageModule, TooltipModule
  ],
  providers: [MessageService],
  template: `
    <p-toast />

    <div class="card">
      <p-toolbar styleClass="mb-3">
        <ng-template pTemplate="left">
          <h2 class="text-lg font-bold text-900 m-0">Leave Requests</h2>
        </ng-template>
        <ng-template pTemplate="right">
          <p-dropdown
            [options]="statusOptions"
            [(ngModel)]="selectedStatus"
            optionLabel="label"
            optionValue="value"
            (onChange)="onStatusChange()"
            styleClass="w-10rem"
          />
        </ng-template>
      </p-toolbar>

      <!-- Loading skeleton -->
      @if (loading) {
        <div class="flex flex-column gap-2">
          @for (n of [1,2,3,4]; track n) {
            <p-skeleton height="3rem" borderRadius="6px" />
          }
        </div>
      }

      <!-- Empty state -->
      @if (!loading && leaves.length === 0) {
        <p-message
          severity="info"
          text="No leave applications found for the selected filter."
          styleClass="w-full"
        />
      }

      <!-- Table -->
      @if (!loading && leaves.length > 0) {
        <p-table
          [value]="leaves"
          styleClass="p-datatable-sm p-datatable-gridlines"
          responsiveLayout="scroll"
          [tableStyle]="{'min-width': '750px'}"
        >
          <ng-template pTemplate="header">
            <tr>
              <th>Student</th>
              <th>Parent</th>
              <th>From</th>
              <th>To</th>
              <th class="text-center">Days</th>
              <th>Type</th>
              <th>Reason</th>
              <th class="text-center">Status</th>
              <th class="text-center">Actions</th>
            </tr>
          </ng-template>
          <ng-template pTemplate="body" let-leave>
            <tr>
              <td class="text-sm font-medium">{{ leave.student_name }}</td>
              <td class="text-sm">{{ leave.parent_name }}</td>
              <td class="text-sm">{{ leave.from_date | date:'d MMM y' }}</td>
              <td class="text-sm">{{ leave.to_date | date:'d MMM y' }}</td>
              <td class="text-center text-sm">{{ leave.duration_days ?? '-' }}</td>
              <td class="text-sm">{{ getTypeLabel(leave.leave_type) }}</td>
              <td class="text-sm" style="max-width: 200px">
                <span
                  class="overflow-hidden text-overflow-ellipsis white-space-nowrap block"
                  [pTooltip]="leave.reason"
                  tooltipPosition="top"
                >
                  {{ leave.reason }}
                </span>
              </td>
              <td class="text-center">
                <p-tag
                  [value]="getStatusLabel(leave.status)"
                  [severity]="getStatusSeverity(leave.status)"
                />
              </td>
              <td class="text-center">
                @if (leave.status === 'pending') {
                  <div class="flex gap-1 justify-content-center">
                    <p-button
                      icon="pi pi-check"
                      severity="success"
                      [rounded]="true"
                      [text]="true"
                      size="small"
                      pTooltip="Approve"
                      (onClick)="openReview(leave, 'approved')"
                    />
                    <p-button
                      icon="pi pi-times"
                      severity="danger"
                      [rounded]="true"
                      [text]="true"
                      size="small"
                      pTooltip="Reject"
                      (onClick)="openReview(leave, 'rejected')"
                    />
                  </div>
                } @else {
                  <span class="text-xs text-400">—</span>
                }
              </td>
            </tr>
          </ng-template>
        </p-table>
      }
    </div>

    <!-- Review dialog -->
    <p-dialog
      [header]="reviewAction === 'approved' ? 'Approve Leave' : 'Reject Leave'"
      [(visible)]="reviewVisible"
      [modal]="true"
      [style]="{ width: '95vw', maxWidth: '440px' }"
      [draggable]="false"
      [resizable]="false"
    >
      @if (selectedLeave) {
        <div class="mb-3 p-3 border-round surface-100">
          <div class="text-sm font-semibold text-900">{{ selectedLeave.student_name }}</div>
          <div class="text-xs text-500 mt-1">
            {{ selectedLeave.from_date | date:'d MMM y' }} – {{ selectedLeave.to_date | date:'d MMM y' }}
            ({{ selectedLeave.duration_days ?? '?' }} days)
          </div>
          <div class="text-xs text-600 mt-1">{{ selectedLeave.reason }}</div>
        </div>
      }

      <form [formGroup]="reviewForm" (ngSubmit)="submitReview()">
        <div class="field">
          <label class="block text-sm font-medium text-700 mb-1">Remarks</label>
          <textarea
            pInputTextarea
            formControlName="remarks"
            rows="3"
            placeholder="Optional remarks for the parent..."
            class="w-full"
          ></textarea>
        </div>

        <div class="flex justify-content-end gap-2 mt-3">
          <p-button
            label="Cancel"
            severity="secondary"
            [text]="true"
            type="button"
            (onClick)="closeReview()"
          />
          <p-button
            [label]="reviewAction === 'approved' ? 'Approve' : 'Reject'"
            [severity]="reviewAction === 'approved' ? 'success' : 'danger'"
            type="submit"
            [loading]="submitting"
          />
        </div>
      </form>
    </p-dialog>
  `
})
export class LeaveReviewComponent implements OnInit {
  private http = inject(HttpClient);
  private toast = inject(MessageService);
  private fb = inject(FormBuilder);

  leaves: any[] = [];
  loading = false;
  selectedStatus = 'pending';

  reviewVisible = false;
  selectedLeave: any = null;
  reviewAction: 'approved' | 'rejected' = 'approved';
  submitting = false;

  statusOptions = [
    { label: 'Pending', value: 'pending' },
    { label: 'Approved', value: 'approved' },
    { label: 'Rejected', value: 'rejected' },
    { label: 'All', value: '' }
  ];

  reviewForm = this.fb.group({
    remarks: ['']
  });

  ngOnInit(): void {
    this.loadLeaves();
  }

  onStatusChange(): void {
    this.loadLeaves();
  }

  loadLeaves(): void {
    this.loading = true;
    let params = new HttpParams();
    if (this.selectedStatus) params = params.set('status', this.selectedStatus);

    this.http.get('/api/v1/leave-applications/all', { params }).subscribe({
      next: (res: any) => {
        this.leaves = res.data?.leave_applications ?? res.data ?? [];
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load leave requests.' });
      }
    });
  }

  openReview(leave: any, action: 'approved' | 'rejected'): void {
    this.selectedLeave = leave;
    this.reviewAction = action;
    this.reviewForm.reset({ remarks: '' });
    this.reviewVisible = true;
  }

  closeReview(): void {
    this.reviewVisible = false;
    this.selectedLeave = null;
    this.reviewForm.reset();
  }

  submitReview(): void {
    if (!this.selectedLeave) return;
    this.submitting = true;

    const payload = {
      status: this.reviewAction,
      remarks: this.reviewForm.value.remarks ?? ''
    };

    this.http.put(`/api/v1/leave-applications/${this.selectedLeave.id}/review`, payload).subscribe({
      next: () => {
        this.submitting = false;
        this.reviewVisible = false;
        const label = this.reviewAction === 'approved' ? 'approved' : 'rejected';
        this.toast.add({ severity: 'success', summary: 'Done', detail: `Leave application ${label}.` });
        this.loadLeaves();
      },
      error: (err: any) => {
        this.submitting = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: err?.error?.message ?? 'Failed to update leave status.' });
      }
    });
  }

  getStatusLabel(status: string): string {
    const map: Record<string, string> = {
      pending: 'Pending',
      approved: 'Approved',
      rejected: 'Rejected'
    };
    return map[status] ?? status;
  }

  getStatusSeverity(status: string): 'warning' | 'success' | 'danger' | 'info' {
    const map: Record<string, 'warning' | 'success' | 'danger' | 'info'> = {
      pending: 'warning',
      approved: 'success',
      rejected: 'danger'
    };
    return map[status] ?? 'info';
  }

  getTypeLabel(type: string): string {
    const map: Record<string, string> = {
      sick: 'Sick',
      family: 'Family',
      personal: 'Personal',
      other: 'Other'
    };
    return map[type] ?? type;
  }
}
