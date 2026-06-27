import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { TableModule } from 'primeng/table';
import { DialogModule } from 'primeng/dialog';
import { MessageModule } from 'primeng/message';
import { SkeletonModule } from 'primeng/skeleton';
import { ToastModule } from 'primeng/toast';
import { MessageService } from 'primeng/api';
import { LeaveFormComponent } from './leave-form.component';
import { ParentPortalService } from '../parent-portal.service';

@Component({
  selector: 'app-leave-list',
  standalone: true,
  imports: [
    CommonModule,
    ButtonModule, TagModule, TableModule, DialogModule,
    MessageModule, SkeletonModule, ToastModule,
    LeaveFormComponent
  ],
  providers: [MessageService],
  template: `
    <p-toast />

    <div>
      <!-- Page header -->
      <div class="flex align-items-center justify-content-between mb-4">
        <div class="flex align-items-center gap-2">
          <i class="pi pi-file-check text-primary text-xl"></i>
          <h2 class="text-lg font-bold text-900 m-0">Leave Applications</h2>
        </div>
        <p-button
          label="Apply Leave"
          icon="pi pi-plus"
          size="small"
          (onClick)="openForm()"
        />
      </div>

      <!-- Loading skeleton -->
      @if (loading) {
        <div class="flex flex-column gap-2">
          @for (n of [1,2,3]; track n) {
            <p-skeleton height="3.5rem" borderRadius="8px" />
          }
        </div>
      }

      <!-- Empty state -->
      @if (!loading && leaves.length === 0) {
        <p-message
          severity="info"
          text="No leave applications found. Tap 'Apply Leave' to submit one."
          styleClass="w-full"
        />
      }

      <!-- Table -->
      @if (!loading && leaves.length > 0) {
        <div style="overflow-x: auto">
          <p-table
            [value]="leaves"
            styleClass="p-datatable-sm"
            [tableStyle]="{'min-width': '600px'}"
          >
            <ng-template pTemplate="header">
              <tr>
                <th>Child</th>
                <th>From</th>
                <th>To</th>
                <th class="text-center">Days</th>
                <th>Type</th>
                <th class="text-center">Status</th>
                <th>Remarks</th>
              </tr>
            </ng-template>
            <ng-template pTemplate="body" let-leave>
              <tr>
                <td class="text-sm font-medium">{{ leave.student_name }}</td>
                <td class="text-sm">{{ leave.from_date | date:'d MMM y' }}</td>
                <td class="text-sm">{{ leave.to_date | date:'d MMM y' }}</td>
                <td class="text-center text-sm">{{ leave.duration_days ?? '-' }}</td>
                <td class="text-sm">{{ getTypeLabel(leave.leave_type) }}</td>
                <td class="text-center">
                  <p-tag
                    [value]="getStatusLabel(leave.status)"
                    [severity]="getStatusSeverity(leave.status)"
                  />
                </td>
                <td class="text-sm text-500">{{ leave.reviewer_remarks || '—' }}</td>
              </tr>
            </ng-template>
          </p-table>
        </div>
      }
    </div>

    <!-- Apply leave dialog -->
    <p-dialog
      header="Apply for Leave"
      [(visible)]="formVisible"
      [modal]="true"
      [style]="{ width: '95vw', maxWidth: '520px' }"
      [draggable]="false"
      [resizable]="false"
    >
      <app-leave-form
        [children]="children"
        (submitted)="onFormSubmitted()"
        (cancelled)="formVisible = false"
      />
    </p-dialog>
  `
})
export class LeaveListComponent implements OnInit {
  private portalService = inject(ParentPortalService);
  private toast = inject(MessageService);

  leaves: any[] = [];
  children: any[] = [];
  loading = false;
  formVisible = false;

  ngOnInit(): void {
    this.loadLeaves();
    this.loadChildren();
  }

  loadLeaves(): void {
    this.loading = true;
    this.portalService.getMyLeaves().subscribe({
      next: (res) => {
        this.leaves = res.data?.leave_applications ?? res.data ?? [];
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load leave applications.' });
      }
    });
  }

  loadChildren(): void {
    this.portalService.getChildren().subscribe({
      next: (res) => {
        this.children = res.data?.children ?? res.data ?? [];
      },
      error: () => {}
    });
  }

  openForm(): void {
    this.formVisible = true;
  }

  onFormSubmitted(): void {
    this.formVisible = false;
    this.toast.add({ severity: 'success', summary: 'Submitted', detail: 'Leave application submitted successfully.' });
    this.loadLeaves();
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
