import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MessageService } from 'primeng/api';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { ToolbarModule } from 'primeng/toolbar';
import { ToastModule } from 'primeng/toast';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { TooltipModule } from 'primeng/tooltip';

import { LibraryService, BookIssue } from '../../../../core/services/library.service';

@Component({
  selector: 'app-book-issues',
  standalone: true,
  imports: [
    CommonModule,
    TableModule,
    ButtonModule,
    TagModule,
    ToolbarModule,
    ToastModule,
    ProgressSpinnerModule,
    TooltipModule,
  ],
  providers: [MessageService],
  templateUrl: './book-issues.component.html',
})
export class BookIssuesComponent implements OnInit {
  private libraryService = inject(LibraryService);
  private toast = inject(MessageService);
  private router = inject(Router);

  overdue: BookIssue[] = [];
  loading = false;
  returningId: number | null = null;

  ngOnInit(): void {
    this.loadOverdue();
  }

  loadOverdue(): void {
    this.loading = true;
    this.libraryService.getOverdue().subscribe({
      next: (res) => {
        this.overdue = res.data?.overdue ?? [];
        this.loading = false;
      },
      error: () => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load overdue issues' });
        this.loading = false;
      },
    });
  }

  returnIssue(issue: BookIssue): void {
    this.returningId = issue.id;
    this.libraryService.returnBook(issue.id).subscribe({
      next: (res) => {
        this.returningId = null;
        const fine = res.data?.fine_amount ?? 0;
        const detail = fine > 0
          ? `Book returned. Fine due: ₹${fine.toFixed(2)}`
          : 'Book returned. No fine due.';
        this.toast.add({
          severity: fine > 0 ? 'warn' : 'success',
          summary: 'Returned',
          detail,
          life: 5000,
        });
        this.loadOverdue();
      },
      error: (err: any) => {
        this.returningId = null;
        const detail = err?.error?.message ?? 'Failed to return book';
        this.toast.add({ severity: 'error', summary: 'Error', detail });
      },
    });
  }

  statusSeverity(status: string): 'warning' | 'success' | 'danger' | 'info' {
    const map: Record<string, 'warning' | 'success' | 'danger' | 'info'> = {
      issued: 'info',
      returned: 'success',
      overdue: 'danger',
    };
    return map[status] ?? 'info';
  }

  navigateTo(path: string): void {
    this.router.navigate([path]);
  }
}
