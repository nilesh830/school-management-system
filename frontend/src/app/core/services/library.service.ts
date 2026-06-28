import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiResponse } from '../models/user.model';

// ── Library interfaces ─────────────────────────────────────────────────────────

export interface Book {
  id: number;
  isbn: string | null;
  title: string;
  author: string;
  publisher: string | null;
  category: string | null;
  total_copies: number;
  available_copies: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type BookIssueStatus = 'issued' | 'returned' | 'overdue';

export interface BookIssue {
  id: number;
  book_id: number;
  book_title: string;
  student_id: number;
  student_name: string;
  issued_date: string;
  due_date: string;
  returned_date: string | null;
  fine_amount: number;
  status: BookIssueStatus;
  issued_by: number | null;
  created_at: string;
  days_overdue?: number;
}

export interface BookListData {
  books: Book[];
}

export interface OverdueListData {
  overdue: BookIssue[];
}

export interface IssueListData {
  issues: BookIssue[];
}

export interface BookPayload {
  isbn?: string | null;
  title: string;
  author: string;
  publisher?: string | null;
  category?: string | null;
  total_copies: number;
  is_active?: boolean;
}

export interface IssuePayload {
  book_id: number;
  student_id: number;
  due_date: string; // YYYY-MM-DD
}

// ── Service ─────────────────────────────────────────────────────────────────────

@Injectable({ providedIn: 'root' })
export class LibraryService {
  private http = inject(HttpClient);
  private readonly apiUrl = '/api/v1/library';

  /** POST /api/v1/library/books */
  createBook(payload: BookPayload): Observable<ApiResponse<Book>> {
    return this.http.post<ApiResponse<Book>>(`${this.apiUrl}/books`, payload);
  }

  /** GET /api/v1/library/books?search= */
  getBooks(search?: string): Observable<ApiResponse<BookListData>> {
    let params = new HttpParams();
    if (search) params = params.set('search', search);
    return this.http.get<ApiResponse<BookListData>>(`${this.apiUrl}/books`, { params });
  }

  /** GET /api/v1/library/books/:id */
  getBook(id: number): Observable<ApiResponse<Book>> {
    return this.http.get<ApiResponse<Book>>(`${this.apiUrl}/books/${id}`);
  }

  /** PUT /api/v1/library/books/:id */
  updateBook(id: number, payload: Partial<BookPayload>): Observable<ApiResponse<Book>> {
    return this.http.put<ApiResponse<Book>>(`${this.apiUrl}/books/${id}`, payload);
  }

  /** DELETE /api/v1/library/books/:id (soft delete; 409 if active issues) */
  deleteBook(id: number): Observable<ApiResponse<any>> {
    return this.http.delete<ApiResponse<any>>(`${this.apiUrl}/books/${id}`);
  }

  /** POST /api/v1/library/issue (409 if no copies available) */
  issueBook(payload: IssuePayload): Observable<ApiResponse<BookIssue>> {
    return this.http.post<ApiResponse<BookIssue>>(`${this.apiUrl}/issue`, payload);
  }

  /** PUT /api/v1/library/issue/:id/return */
  returnBook(issueId: number, returnedDate?: string): Observable<ApiResponse<BookIssue>> {
    const body: { returned_date?: string } = {};
    if (returnedDate) body.returned_date = returnedDate;
    return this.http.put<ApiResponse<BookIssue>>(`${this.apiUrl}/issue/${issueId}/return`, body);
  }

  /** GET /api/v1/library/overdue */
  getOverdue(): Observable<ApiResponse<OverdueListData>> {
    return this.http.get<ApiResponse<OverdueListData>>(`${this.apiUrl}/overdue`);
  }

  /**
   * GET /api/v1/library/issues
   * Defaults to all outstanding (not-yet-returned) issues.
   * Pass status 'returned' or 'all' to widen, or studentId to filter.
   */
  getIssues(status?: string, studentId?: number): Observable<ApiResponse<IssueListData>> {
    let params = new HttpParams();
    if (status) params = params.set('status', status);
    if (studentId) params = params.set('student_id', studentId.toString());
    return this.http.get<ApiResponse<IssueListData>>(`${this.apiUrl}/issues`, { params });
  }
}
