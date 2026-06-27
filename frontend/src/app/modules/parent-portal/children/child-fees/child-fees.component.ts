import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ButtonModule } from 'primeng/button';
import { MessageModule } from 'primeng/message';
import { SkeletonModule } from 'primeng/skeleton';
import { CardModule } from 'primeng/card';
import { MessageService } from 'primeng/api';
import { ToastModule } from 'primeng/toast';
import { ParentPortalService } from '../../parent-portal.service';

@Component({
  selector: 'app-child-fees',
  standalone: true,
  imports: [
    CommonModule,
    TableModule, TagModule, ButtonModule,
    MessageModule, SkeletonModule, CardModule, ToastModule
  ],
  providers: [MessageService],
  template: `
    <p-toast />

    <div>
      <!-- Page header -->
      <div class="flex align-items-center gap-2 mb-4">
        <i class="pi pi-credit-card text-primary text-xl"></i>
        <h2 class="text-lg font-bold text-900 m-0">Fee Status</h2>
        @if (childName) {
          <span class="text-500 text-sm">— {{ childName }}</span>
        }
      </div>

      <!-- Loading skeleton -->
      @if (loading) {
        <div class="flex flex-column gap-3">
          <p-skeleton height="3rem" borderRadius="8px" />
          <p-skeleton height="12rem" borderRadius="8px" />
        </div>
      }

      <!-- Loaded state -->
      @if (!loading) {
        <!-- Outstanding summary banner -->
        @if (totalDue > 0) {
          <div class="mb-3">
            <p-message
              severity="error"
              [text]="'Outstanding balance: ₹' + (totalDue | number:'1.0-0') + ' — Please contact the accounts office.'"
              styleClass="w-full"
            />
          </div>
        } @else {
          <div class="mb-3">
            <p-message
              severity="success"
              text="All fees are up to date."
              styleClass="w-full"
            />
          </div>
        }

        <!-- Empty state -->
        @if (feeRecords.length === 0) {
          <p-message
            severity="info"
            text="No fee records found for this student."
            styleClass="w-full"
          />
        }

        <!-- Fee records table -->
        @if (feeRecords.length > 0) {
          <p-card styleClass="shadow-1">
            <p-table
              [value]="feeRecords"
              [tableStyle]="{'min-width': '100%'}"
              styleClass="p-datatable-sm"
              responsiveLayout="scroll"
            >
              <ng-template pTemplate="header">
                <tr>
                  <th>Fee Type</th>
                  <th class="text-right">Amount</th>
                  <th>Due Date</th>
                  <th class="text-center">Status</th>
                  <th class="text-center">Receipt</th>
                </tr>
              </ng-template>
              <ng-template pTemplate="body" let-rec>
                <tr [class]="isOverdue(rec) ? 'row-overdue' : ''">
                  <td class="text-sm font-medium">{{ rec.fee_type }}</td>
                  <td class="text-right text-sm">
                    <span [class]="rec.amount_due > 0 ? 'text-red-500 font-semibold' : ''">
                      ₹{{ rec.net_amount | number:'1.0-0' }}
                    </span>
                    @if (rec.amount_due > 0 && rec.amount_paid > 0) {
                      <div class="text-xs text-500">Paid: ₹{{ rec.amount_paid | number:'1.0-0' }}</div>
                    }
                  </td>
                  <td class="text-sm">
                    @if (rec.due_date) {
                      <span [class]="isOverdue(rec) ? 'text-red-500' : ''">
                        {{ rec.due_date | date:'d MMM y' }}
                      </span>
                    } @else {
                      <span class="text-400">—</span>
                    }
                  </td>
                  <td class="text-center">
                    <p-tag
                      [value]="getStatusLabel(rec.status)"
                      [severity]="getStatusSeverity(rec.status)"
                    />
                  </td>
                  <td class="text-center">
                    @if (hasPayment(rec)) {
                      <p-button
                        icon="pi pi-download"
                        [rounded]="true"
                        [text]="true"
                        size="small"
                        pTooltip="Download Receipt"
                        [loading]="downloadingPaymentId === getLatestPaymentId(rec)"
                        (onClick)="downloadReceipt(rec)"
                      />
                    } @else {
                      <span class="text-400 text-xs">—</span>
                    }
                  </td>
                </tr>
              </ng-template>
            </p-table>
          </p-card>
        }
      }
    </div>

    <style>
      .row-overdue td { background-color: #fff5f5 !important; }
    </style>
  `
})
export class ChildFeesComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private portalService = inject(ParentPortalService);
  private toast = inject(MessageService);

  childId = 0;
  childName = '';
  loading = false;
  feeRecords: any[] = [];
  totalDue = 0;
  downloadingPaymentId: number | null = null;

  ngOnInit(): void {
    this.childId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadFees();
  }

  loadFees(): void {
    this.loading = true;
    this.portalService.getChildFees(this.childId).subscribe({
      next: (res) => {
        this.feeRecords = res.data?.fee_records ?? [];
        this.totalDue = res.data?.total_due ?? 0;
        if (res.data?.student_name) this.childName = res.data.student_name;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load fee records.' });
      }
    });
  }

  isOverdue(rec: any): boolean {
    if (!rec.due_date || rec.status === 'paid' || rec.status === 'waived') return false;
    return new Date(rec.due_date) < new Date();
  }

  hasPayment(rec: any): boolean {
    return Array.isArray(rec.payments) && rec.payments.length > 0;
  }

  getLatestPaymentId(rec: any): number | null {
    if (!this.hasPayment(rec)) return null;
    const sorted = [...rec.payments].sort((a: any, b: any) =>
      new Date(b.payment_date).getTime() - new Date(a.payment_date).getTime()
    );
    return sorted[0]?.id ?? null;
  }

  downloadReceipt(rec: any): void {
    const paymentId = this.getLatestPaymentId(rec);
    if (!paymentId) return;
    this.downloadingPaymentId = paymentId;
    this.portalService.downloadReceipt(paymentId).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `receipt-${paymentId}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
        this.downloadingPaymentId = null;
      },
      error: () => {
        this.downloadingPaymentId = null;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to download receipt.' });
      }
    });
  }

  getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      paid: 'Paid',
      pending: 'Pending',
      partial: 'Partial',
      waived: 'Waived',
      overdue: 'Overdue'
    };
    return labels[status] ?? status;
  }

  getStatusSeverity(status: string): 'success' | 'warning' | 'danger' | 'info' | 'secondary' {
    const map: Record<string, 'success' | 'warning' | 'danger' | 'info' | 'secondary'> = {
      paid: 'success',
      pending: 'warning',
      partial: 'warning',
      overdue: 'danger',
      waived: 'secondary'
    };
    return map[status] ?? 'info';
  }
}
