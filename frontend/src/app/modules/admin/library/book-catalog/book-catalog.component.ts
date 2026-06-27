import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap, takeUntil } from 'rxjs/operators';
import { MessageService } from 'primeng/api';
import { TableModule } from 'primeng/table';
import { DialogModule } from 'primeng/dialog';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { InputNumberModule } from 'primeng/inputnumber';
import { TagModule } from 'primeng/tag';
import { ToolbarModule } from 'primeng/toolbar';
import { ToastModule } from 'primeng/toast';
import { CalendarModule } from 'primeng/calendar';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { TooltipModule } from 'primeng/tooltip';

import { LibraryService, Book, BookPayload, IssuePayload } from '../../../../core/services/library.service';
import { StudentService, Student } from '../../../../core/services/student.service';

@Component({
  selector: 'app-book-catalog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    TableModule,
    DialogModule,
    ButtonModule,
    InputTextModule,
    InputNumberModule,
    TagModule,
    ToolbarModule,
    ToastModule,
    CalendarModule,
    ProgressSpinnerModule,
    TooltipModule,
  ],
  providers: [MessageService],
  templateUrl: './book-catalog.component.html',
})
export class BookCatalogComponent implements OnInit, OnDestroy {
  private libraryService = inject(LibraryService);
  private studentService = inject(StudentService);
  private fb = inject(FormBuilder);
  private toast = inject(MessageService);
  private router = inject(Router);
  private destroy$ = new Subject<void>();

  books: Book[] = [];
  loading = false;

  // Search box (debounced)
  searchTerm = '';
  private searchSubject = new Subject<string>();

  // Book create/edit dialog
  dialogVisible = false;
  saving = false;
  isEdit = false;
  editingId: number | null = null;

  form: FormGroup = this.fb.group({
    isbn: [''],
    title: ['', Validators.required],
    author: ['', Validators.required],
    publisher: [''],
    category: [''],
    total_copies: [1, [Validators.required, Validators.min(1)]],
  });

  // Issue dialog
  issueDialogVisible = false;
  issuing = false;
  issueBook: Book | null = null;

  // Student search within issue dialog
  studentQuery = '';
  studentResults: Student[] = [];
  selectedStudent: Student | null = null;
  searchingStudents = false;
  private studentSearchSubject = new Subject<string>();

  issueForm: FormGroup = this.fb.group({
    due_date: [null, Validators.required],
  });

  ngOnInit(): void {
    // Book catalog search
    this.searchSubject
      .pipe(debounceTime(400), distinctUntilChanged(), takeUntil(this.destroy$))
      .subscribe((term) => this.loadBooks(term));

    // Student search inside issue dialog
    this.studentSearchSubject
      .pipe(
        debounceTime(400),
        distinctUntilChanged(),
        switchMap((query) => {
          if (!query || query.length < 2) {
            this.studentResults = [];
            this.searchingStudents = false;
            return [];
          }
          this.searchingStudents = true;
          return this.studentService.searchStudents(query, 10);
        }),
        takeUntil(this.destroy$)
      )
      .subscribe({
        next: (res: any) => {
          this.studentResults = res?.data?.students ?? [];
          this.searchingStudents = false;
        },
        error: () => {
          this.searchingStudents = false;
          this.studentResults = [];
        },
      });

    this.loadBooks();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadBooks(search?: string): void {
    this.loading = true;
    this.libraryService.getBooks(search).subscribe({
      next: (res) => {
        this.books = res.data?.books ?? [];
        this.loading = false;
      },
      error: () => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load books' });
        this.loading = false;
      },
    });
  }

  onSearchInput(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.searchTerm = value;
    this.searchSubject.next(value);
  }

  // ── Book CRUD ──────────────────────────────────────────────────────────────

  openDialog(book?: Book): void {
    this.form.reset({ total_copies: 1 });
    this.isEdit = false;
    this.editingId = null;

    if (book) {
      this.isEdit = true;
      this.editingId = book.id;
      this.form.patchValue({
        isbn: book.isbn,
        title: book.title,
        author: book.author,
        publisher: book.publisher,
        category: book.category,
        total_copies: book.total_copies,
      });
    }

    this.dialogVisible = true;
  }

  closeDialog(): void {
    this.dialogVisible = false;
    this.form.reset({ total_copies: 1 });
  }

  saveBook(): void {
    if (this.form.invalid) return;

    this.saving = true;
    const raw = this.form.value;
    const payload: BookPayload = {
      isbn: raw.isbn?.trim() || null,
      title: raw.title,
      author: raw.author,
      publisher: raw.publisher?.trim() || null,
      category: raw.category?.trim() || null,
      total_copies: raw.total_copies,
    };

    const request$ = this.isEdit && this.editingId !== null
      ? this.libraryService.updateBook(this.editingId, payload)
      : this.libraryService.createBook(payload);

    request$.subscribe({
      next: () => {
        this.saving = false;
        this.dialogVisible = false;
        this.toast.add({
          severity: 'success',
          summary: 'Success',
          detail: this.isEdit ? 'Book updated successfully' : 'Book added successfully',
        });
        this.loadBooks(this.searchTerm);
      },
      error: (err: any) => {
        this.saving = false;
        const detail = err?.error?.message ?? (this.isEdit ? 'Failed to update book' : 'Failed to add book');
        this.toast.add({ severity: 'error', summary: 'Error', detail });
      },
    });
  }

  deleteBook(book: Book): void {
    if (!window.confirm(`Delete "${book.title}"? This will deactivate the book.`)) return;

    this.libraryService.deleteBook(book.id).subscribe({
      next: () => {
        this.toast.add({ severity: 'success', summary: 'Deleted', detail: 'Book removed from catalog' });
        this.loadBooks(this.searchTerm);
      },
      error: (err: any) => {
        // 409 => book has active issues; surface the backend message
        const detail = err?.error?.message ?? 'Failed to delete book';
        this.toast.add({ severity: 'error', summary: 'Cannot Delete', detail, life: 5000 });
      },
    });
  }

  availabilitySeverity(book: Book): 'success' | 'danger' {
    return book.available_copies > 0 ? 'success' : 'danger';
  }

  // ── Issue flow ─────────────────────────────────────────────────────────────

  openIssueDialog(book: Book): void {
    this.issueBook = book;
    this.selectedStudent = null;
    this.studentQuery = '';
    this.studentResults = [];
    const due = new Date();
    due.setDate(due.getDate() + 14);
    this.issueForm.reset({ due_date: due });
    this.issueDialogVisible = true;
  }

  closeIssueDialog(): void {
    this.issueDialogVisible = false;
    this.issueBook = null;
    this.selectedStudent = null;
    this.studentQuery = '';
    this.studentResults = [];
    this.issueForm.reset();
  }

  onStudentSearchInput(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.studentQuery = value;
    if (!value || value.length < 2) {
      this.studentResults = [];
      this.selectedStudent = null;
      return;
    }
    this.studentSearchSubject.next(value);
  }

  selectStudent(student: Student): void {
    this.selectedStudent = student;
    this.studentQuery = `${student.first_name} ${student.last_name} (${student.admission_no})`;
    this.studentResults = [];
  }

  submitIssue(): void {
    if (this.issueForm.invalid || !this.issueBook || !this.selectedStudent) return;

    this.issuing = true;
    const payload: IssuePayload = {
      book_id: this.issueBook.id,
      student_id: this.selectedStudent.id,
      due_date: this.formatDate(this.issueForm.value.due_date),
    };

    this.libraryService.issueBook(payload).subscribe({
      next: () => {
        this.issuing = false;
        this.issueDialogVisible = false;
        this.toast.add({
          severity: 'success',
          summary: 'Book Issued',
          detail: `"${this.issueBook?.title}" issued to ${this.selectedStudent?.first_name} ${this.selectedStudent?.last_name}`,
          life: 4000,
        });
        this.closeIssueDialog();
        this.loadBooks(this.searchTerm);
      },
      error: (err: any) => {
        this.issuing = false;
        // 409 => no copies available
        const detail = err?.error?.message ?? 'Failed to issue book';
        this.toast.add({ severity: 'error', summary: 'Error', detail, life: 5000 });
      },
    });
  }

  navigateTo(path: string): void {
    this.router.navigate([path]);
  }

  private formatDate(date: Date): string {
    const d = new Date(date);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }
}
