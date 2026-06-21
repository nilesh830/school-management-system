import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { BadgeModule } from 'primeng/badge';
import { AvatarModule } from 'primeng/avatar';
import { DialogModule } from 'primeng/dialog';
import { MessageModule } from 'primeng/message';
import { SkeletonModule } from 'primeng/skeleton';
import { ToastModule } from 'primeng/toast';
import { MessageService } from 'primeng/api';
import { NewThreadDialogComponent } from './new-thread-dialog.component';
import { ParentPortalService } from '../parent-portal.service';

@Component({
  selector: 'app-thread-list',
  standalone: true,
  imports: [
    CommonModule,
    ButtonModule, BadgeModule, AvatarModule, DialogModule,
    MessageModule, SkeletonModule, ToastModule,
    NewThreadDialogComponent
  ],
  providers: [MessageService],
  template: `
    <p-toast />

    <div>
      <!-- Header -->
      <div class="flex align-items-center justify-content-between mb-4">
        <div class="flex align-items-center gap-2">
          <i class="pi pi-envelope text-primary text-xl"></i>
          <h2 class="text-lg font-bold text-900 m-0">Messages</h2>
        </div>
        <p-button
          label="New Message"
          icon="pi pi-plus"
          size="small"
          (onClick)="openNewThread()"
        />
      </div>

      <!-- Loading -->
      @if (loading) {
        <div class="flex flex-column gap-2">
          @for (n of [1,2,3]; track n) {
            <p-skeleton height="4rem" borderRadius="8px" />
          }
        </div>
      }

      <!-- Empty -->
      @if (!loading && threads.length === 0) {
        <p-message
          severity="info"
          text="No messages yet. Start a conversation with a teacher."
          styleClass="w-full"
        />
      }

      <!-- Thread list -->
      @if (!loading && threads.length > 0) {
        <div class="flex flex-column gap-2">
          @for (thread of threads; track thread.id) {
            <div
              class="flex align-items-center gap-3 p-3 border-round cursor-pointer hover:surface-100 transition-colors transition-duration-200"
              style="background: white; border: 1px solid #e2e8f0"
              (click)="openThread(thread)"
            >
              <!-- Avatar -->
              <p-avatar
                [label]="getInitial(thread.teacher_name)"
                styleClass="bg-primary-100 text-primary font-bold flex-shrink-0"
                shape="circle"
                size="large"
              />

              <!-- Content -->
              <div class="flex-1 min-w-0">
                <div class="flex align-items-center justify-content-between gap-2">
                  <span class="font-semibold text-900 text-sm white-space-nowrap overflow-hidden text-overflow-ellipsis">
                    {{ thread.subject }}
                  </span>
                  @if (thread.unread_count > 0) {
                    <p-badge [value]="thread.unread_count.toString()" severity="danger" />
                  }
                </div>
                <div class="text-xs text-500 mt-1">
                  {{ thread.student_name }} · {{ thread.teacher_name ?? 'Teacher' }}
                </div>
                @if (thread.last_message) {
                  <div class="text-xs text-600 mt-1 white-space-nowrap overflow-hidden text-overflow-ellipsis">
                    {{ thread.last_message }}
                  </div>
                }
              </div>

              <!-- Time -->
              @if (thread.last_message_at) {
                <span class="text-xs text-400 flex-shrink-0">
                  {{ thread.last_message_at | date:'d MMM' }}
                </span>
              }
            </div>
          }
        </div>
      }
    </div>

    <!-- New thread dialog -->
    <p-dialog
      header="New Message"
      [(visible)]="newThreadVisible"
      [modal]="true"
      [style]="{ width: '95vw', maxWidth: '520px' }"
      [draggable]="false"
      [resizable]="false"
    >
      <app-new-thread-dialog
        [children]="children"
        (created)="onThreadCreated()"
        (cancelled)="newThreadVisible = false"
      />
    </p-dialog>
  `
})
export class ThreadListComponent implements OnInit {
  private portalService = inject(ParentPortalService);
  private router = inject(Router);
  private toast = inject(MessageService);

  threads: any[] = [];
  children: any[] = [];
  loading = false;
  newThreadVisible = false;

  ngOnInit(): void {
    this.loadThreads();
    this.loadChildren();
  }

  loadThreads(): void {
    this.loading = true;
    this.portalService.getThreads().subscribe({
      next: (res) => {
        this.threads = res.data?.threads ?? res.data ?? [];
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load messages.' });
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

  openThread(thread: any): void {
    this.router.navigate(['/parent/messages', thread.id]);
  }

  openNewThread(): void {
    this.newThreadVisible = true;
  }

  onThreadCreated(): void {
    this.newThreadVisible = false;
    this.toast.add({ severity: 'success', summary: 'Sent', detail: 'Message sent successfully.' });
    this.loadThreads();
  }

  getInitial(name: string | null | undefined): string {
    return name ? name.charAt(0).toUpperCase() : 'T';
  }
}
