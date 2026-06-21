import { Component, OnInit, OnDestroy, ViewChild, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { BadgeModule } from 'primeng/badge';
import { OverlayPanelModule } from 'primeng/overlaypanel';
import { OverlayPanel } from 'primeng/overlaypanel';
import { ParentPortalService } from '../parent-portal.service';

const NOTIFICATION_ROUTES: Record<string, string> = {
  attendance: '/parent/children/{ref_id}/attendance',
  exam_result: '/parent/children/{ref_id}/grades',
  fee: '/parent/children/{ref_id}/fees',
  leave: '/parent/leave-applications',
  message: '/parent/messages',
  announcement: '/parent/notices'
};

@Component({
  selector: 'app-notification-bell',
  standalone: true,
  imports: [
    CommonModule,
    ButtonModule,
    BadgeModule,
    OverlayPanelModule
  ],
  template: `
    <div class="relative inline-flex">
      <p-button
        icon="pi pi-bell"
        [rounded]="true"
        [text]="true"
        severity="secondary"
        styleClass="p-button-sm"
        (onClick)="bellPanel.toggle($event)"
      />
      @if (unreadCount > 0) {
        <span
          class="absolute top-0 right-0 flex align-items-center justify-content-center border-circle font-bold text-white"
          style="min-width: 1.1rem; height: 1.1rem; font-size: 0.65rem; background: #ef4444; transform: translate(30%, -30%)"
        >
          {{ unreadCount > 99 ? '99+' : unreadCount }}
        </span>
      }
    </div>

    <p-overlayPanel #bellPanel [style]="{ width: '320px', maxHeight: '420px' }">
      <div class="flex align-items-center justify-content-between mb-2" style="border-bottom: 1px solid #e2e8f0; padding-bottom: 0.5rem">
        <span class="font-semibold text-900 text-sm">Notifications</span>
        @if (unreadCount > 0) {
          <span
            class="text-xs text-primary cursor-pointer hover:underline"
            (click)="markAllRead()"
          >
            Mark all read
          </span>
        }
      </div>

      @if (loading) {
        <div class="text-center py-3 text-500 text-xs">Loading...</div>
      }

      @if (!loading && notifications.length === 0) {
        <div class="text-center py-4 text-500 text-sm">
          <i class="pi pi-bell-slash text-2xl mb-2 block text-400"></i>
          No notifications
        </div>
      }

      @if (!loading && notifications.length > 0) {
        <div style="overflow-y: auto; max-height: 330px">
          @for (notif of notifications; track notif.id) {
            <div
              class="flex flex-column gap-1 px-2 py-2 border-round cursor-pointer hover:surface-100 transition-colors transition-duration-200"
              [style.background]="!notif.is_read ? '#eff6ff' : 'transparent'"
              (click)="onNotifClick(notif)"
            >
              <div class="font-semibold text-900 text-xs">{{ notif.title }}</div>
              <div class="text-xs text-600" style="overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical">
                {{ truncate(notif.body, 80) }}
              </div>
              <div class="text-xs text-400">{{ notif.created_at | date:'d MMM, h:mm a' }}</div>
            </div>
          }
        </div>
      }
    </p-overlayPanel>
  `
})
export class NotificationBellComponent implements OnInit, OnDestroy {
  @ViewChild('bellPanel') bellPanel!: OverlayPanel;

  private portalService = inject(ParentPortalService);
  private router = inject(Router);

  notifications: any[] = [];
  unreadCount = 0;
  loading = false;
  private pollInterval: ReturnType<typeof setInterval> | null = null;

  ngOnInit(): void {
    this.pollUnread();
    this.pollInterval = setInterval(() => this.pollUnread(), 60_000);
  }

  ngOnDestroy(): void {
    if (this.pollInterval) clearInterval(this.pollInterval);
  }

  pollUnread(): void {
    this.portalService.getNotifications(true).subscribe({
      next: (res) => {
        const list = res.data?.notifications ?? res.data ?? [];
        this.unreadCount = list.length;
      },
      error: () => {}
    });
  }

  loadAll(): void {
    this.loading = true;
    this.portalService.getNotifications(false).subscribe({
      next: (res) => {
        this.notifications = (res.data?.notifications ?? res.data ?? []).slice(0, 20);
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      }
    });
  }

  onNotifClick(notif: any): void {
    if (!notif.is_read) {
      this.portalService.markNotificationRead(notif.id).subscribe({
        next: () => {
          notif.is_read = true;
          this.unreadCount = Math.max(0, this.unreadCount - 1);
        },
        error: () => {}
      });
    }
    const route = this.buildRoute(notif);
    if (route) {
      this.bellPanel.hide();
      this.router.navigateByUrl(route);
    }
  }

  markAllRead(): void {
    this.portalService.markAllNotificationsRead().subscribe({
      next: () => {
        this.unreadCount = 0;
        this.notifications.forEach(n => n.is_read = true);
      },
      error: () => {}
    });
  }

  truncate(text: string, max: number): string {
    if (!text) return '';
    return text.length > max ? text.substring(0, max) + '...' : text;
  }

  private buildRoute(notif: any): string | null {
    const template = NOTIFICATION_ROUTES[notif.notification_type ?? notif.type ?? ''];
    if (!template) return null;
    return template.replace('{ref_id}', String(notif.reference_id ?? ''));
  }

  // Called from parent-layout when panel opens
  onPanelShow(): void {
    this.loadAll();
  }
}
