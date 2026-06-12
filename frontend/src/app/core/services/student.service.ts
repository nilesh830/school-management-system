import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiResponse } from '../models/user.model';

export interface Student {
  id: number;
  admission_no: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: 'Male' | 'Female' | 'Other';
  admission_date: string;
  blood_group?: string | null;
  address?: string | null;
  phone?: string | null;
  user_id?: number | null;
  class_name?: string | null;
  status?: string;
  photo_url?: string | null;
  leaving_date?: string | null;
  current_section?: any | null;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface StudentPayload {
  admission_no: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: 'Male' | 'Female' | 'Other';
  admission_date: string;
  blood_group?: string | null;
  address?: string | null;
  phone?: string | null;
  user_id?: number | null;
}

export interface StudentListMeta {
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface StudentListData {
  students: Student[];
  meta: StudentListMeta;
}

export interface Parent {
  id: number;
  first_name: string;
  last_name: string;
  relationship_type: string;
  phone_primary: string;
  email?: string | null;
  is_primary_contact?: boolean;
}

export interface StudentDocument {
  id: number;
  document_type: string;
  file_name: string;
  file_path: string;
  created_at: string;
}

export interface TransferPayload {
  new_section_id: number;
  effective_date: string;
  reason?: string | null;
}

export interface StatusUpdatePayload {
  status: 'active' | 'alumni' | 'transferred' | 'expelled';
  leaving_date?: string | null;
}

@Injectable({ providedIn: 'root' })
export class StudentService {
  private readonly apiUrl = '/api/v1/students';

  constructor(private http: HttpClient) {}

  // ── Student CRUD ─────────────────────────────────────────────────────────

  getStudents(page = 1, perPage = 20): Observable<ApiResponse<StudentListData>> {
    const params = new HttpParams()
      .set('page', page.toString())
      .set('per_page', perPage.toString());
    return this.http.get<ApiResponse<StudentListData>>(this.apiUrl, { params });
  }

  searchStudents(search: string, perPage = 20): Observable<ApiResponse<StudentListData>> {
    const params = new HttpParams()
      .set('search', search)
      .set('per_page', perPage.toString());
    return this.http.get<ApiResponse<StudentListData>>(this.apiUrl, { params });
  }

  getStudentsBySection(sectionId: number): Observable<ApiResponse<StudentListData>> {
    const params = new HttpParams()
      .set('section_id', sectionId.toString())
      .set('per_page', '100');
    return this.http.get<ApiResponse<StudentListData>>(this.apiUrl, { params });
  }

  getStudentById(id: number): Observable<ApiResponse<Student>> {
    return this.http.get<ApiResponse<Student>>(`${this.apiUrl}/${id}`);
  }

  createStudent(data: StudentPayload): Observable<ApiResponse<Student>> {
    return this.http.post<ApiResponse<Student>>(this.apiUrl, data);
  }

  updateStudent(id: number, data: Partial<StudentPayload>): Observable<ApiResponse<Student>> {
    return this.http.put<ApiResponse<Student>>(`${this.apiUrl}/${id}`, data);
  }

  deleteStudent(id: number): Observable<ApiResponse<any>> {
    return this.http.delete<ApiResponse<any>>(`${this.apiUrl}/${id}`);
  }

  // ── Status (SMS-013) ─────────────────────────────────────────────────────

  updateStudentStatus(studentId: number, payload: StatusUpdatePayload): Observable<ApiResponse<Student>> {
    return this.http.patch<ApiResponse<Student>>(`${this.apiUrl}/${studentId}/status`, payload);
  }

  // ── Transfer (SMS-011) ───────────────────────────────────────────────────

  transferStudent(studentId: number, payload: TransferPayload): Observable<ApiResponse<any>> {
    return this.http.post<ApiResponse<any>>(`${this.apiUrl}/${studentId}/transfer`, payload);
  }

  // ── Parents (SMS-010) ────────────────────────────────────────────────────

  getStudentParents(studentId: number): Observable<ApiResponse<Parent[]>> {
    return this.http.get<ApiResponse<Parent[]>>(`${this.apiUrl}/${studentId}/parents`);
  }

  linkParent(studentId: number, parentId: number, isPrimary: boolean): Observable<ApiResponse<any>> {
    return this.http.post<ApiResponse<any>>(`${this.apiUrl}/${studentId}/parents`, {
      parent_id: parentId,
      is_primary_contact: isPrimary
    });
  }

  unlinkParent(studentId: number, parentId: number): Observable<ApiResponse<any>> {
    return this.http.delete<ApiResponse<any>>(`${this.apiUrl}/${studentId}/parents/${parentId}`);
  }

  // ── Documents (SMS-012) ──────────────────────────────────────────────────

  getDocuments(studentId: number): Observable<ApiResponse<StudentDocument[]>> {
    return this.http.get<ApiResponse<StudentDocument[]>>(`${this.apiUrl}/${studentId}/documents`);
  }

  uploadDocument(studentId: number, formData: FormData): Observable<ApiResponse<StudentDocument>> {
    return this.http.post<ApiResponse<StudentDocument>>(`${this.apiUrl}/${studentId}/documents`, formData);
  }

  deleteDocument(studentId: number, docId: number): Observable<ApiResponse<any>> {
    return this.http.delete<ApiResponse<any>>(`${this.apiUrl}/${studentId}/documents/${docId}`);
  }
}
