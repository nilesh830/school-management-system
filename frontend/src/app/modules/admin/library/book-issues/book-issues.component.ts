import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { MessageService } from 'primeng/api';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { ToolbarModule } from 'primeng/toolbar';
import { ToastModule } from 'primeng/toast';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { TooltipModule } from 'primeng/tooltip';
import { SelectButtonModule } from 'primeng/selectbutton';

import { LibraryService, BookIssue } from '../../../../core/services/library.service';

type IssueFilter = 'outstanding' | 'overdue' | 'returned' | 'all';

@Component({
  selector: 'app-book-issues',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    TableModule,
    ButtonModule,
    TagModule,
    ToolbarModule,
    ToastModule,
    ProgressSpinnerModule,
    TooltipModule,
    SelectButtonModule,
  ],
  providers: [MessageService],
  templateUrl: './book-issues.component.html',
})
export class BookIssuesComponent implements OnInit {
  private libraryService = inject(LibraryService);
  private toast = inject(MessageService);
  private router = inject(Router);

  issues: BookIssue[] = [];
  loading = false;
  returningId: number | null = null;

  filter: IssueFilter = 'outstanding';
  filterOptions = [
    { label: 'Outstanding', value: 'outstanding' },
    { label: 'Overdue', value: 'overdue' },
    { label: 'Returned', value: 'returned' },
    { label: 'All', value: 'all' },
  ];

  ngOnInit(): void {
    this.loadIssues();
  }

  loadIssues(): void {
    this.loading = true;
    // 'outstanding' = default (all not-yet-returned); others map to a status filter
    const status = this.filter === 'outstanding' ? undefined : this.filter;
    this.libraryService.getIssues(status).subscribe({
      next: (res) => {
        let rows = res.data?.issues ?? [];
        if (this.filter === 'overdue') {
          rows = rows.filter((i) => i.status === 'overdue');
        }
        this.issues = rows;
        this.loading = false;
      },
      error: () => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load book issues' });
        this.loading = false;
      },
    });
  }

  onFilterChange(): void {
    this.loadIssues();
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
        this.loadIssues();
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
