import { Component, inject, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MessageService } from 'primeng/api';
import { TableModule, TableLazyLoadEvent } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { ToolbarModule } from 'primeng/toolbar';
import { TagModule } from 'primeng/tag';
import { ToastModule } from 'primeng/toast';
import { InputTextModule } from 'primeng/inputtext';
import { Subject, debounceTime, distinctUntilChanged, takeUntil } from 'rxjs';
import { SchoolsService, School } from '../../../../core/services/schools.service';

@Component({
  selector: 'app-school-list',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    ReactiveFormsModule,
    TableModule,
    ButtonModule,
    CardModule,
    ToolbarModule,
    TagModule,
    ToastModule,
    InputTextModule
  ],
  providers: [MessageService],
  templateUrl: './school-list.component.html'
})
export class SchoolListComponent implements OnInit, OnDestroy {
  private schoolsService = inject(SchoolsService);
  private toast = inject(MessageService);
  private destroy$ = new Subject<void>();

  schools: School[] = [];
  totalRecords = 0;
  loading = false;
  rows = 20;

  searchCtrl = new FormControl('');

  ngOnInit(): void {
    this.loadSchools();

    this.searchCtrl.valueChanges.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      takeUntil(this.destroy$)
    ).subscribe(() => {
      this.loadSchools();
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadSchools(event?: TableLazyLoadEvent): void {
    this.loading = true;
    const page = event ? Math.floor((event.first ?? 0) / (event.rows ?? this.rows)) + 1 : 1;
    const perPage = event?.rows ?? this.rows;
    const search = this.searchCtrl.value ?? '';

    this.schoolsService.getSchools(page, perPage, search).subscribe({
      next: (res) => {
        this.schools = res.data.schools;
        this.totalRecords = res.data.meta.total;
        this.loading = false;
      },
      error: () => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load schools' });
        this.loading = false;
      }
    });
  }
}
