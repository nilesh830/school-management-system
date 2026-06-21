import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CardModule } from 'primeng/card';
import { TagModule } from 'primeng/tag';
import { ButtonModule } from 'primeng/button';
import { MessageModule } from 'primeng/message';
import { SkeletonModule } from 'primeng/skeleton';
import { ToastModule } from 'primeng/toast';
import { MessageService } from 'primeng/api';

import { ParentPortalService } from '../parent-portal.service';
import { Announcement } from '../../../core/services/announcement.service';

@Component({
  selector: 'app-notice-board',
  standalone: true,
  imports: [
    CommonModule,
    CardModule,
    TagModule,
    ButtonModule,
    MessageModule,
    SkeletonModule,
    ToastModule,
  ],
  providers: [MessageService],
  templateUrl: './notice-board.component.html',
})
export class NoticeBoardComponent implements OnInit {
  private portalService = inject(ParentPortalService);
  private toast = inject(MessageService);

  recent: Announcement[] = [];
  archived: Announcement[] = [];
  loading = false;
  showArchived = false;

  ngOnInit(): void {
    this.loadNotices();
  }

  loadNotices(): void {
    this.loading = true;
    this.portalService.getNotices().subscribe({
      next: (res) => {
        const notices: Announcement[] = res.data?.notices ?? res.data ?? [];
        this.splitNotices(notices);
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load notices.' });
      },
    });
  }

  private splitNotices(notices: Announcement[]): void {
    const cutoff = Date.now() - 30 * 24 * 60 * 60 * 1000;
    this.recent = [];
    this.archived = [];

    for (const n of notices) {
      const ts = n.published_at ? new Date(n.published_at).getTime() : 0;
      if (ts >= cutoff) {
        this.recent.push(n);
      } else {
        this.archived.push(n);
      }
    }
  }

  toggleArchived(): void {
    this.showArchived = !this.showArchived;
  }
}
