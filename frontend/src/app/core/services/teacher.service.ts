import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiResponse } from '../models/user.model';

export interface Teacher {
  id: number;
  user_id: number;
  employee_id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  date_of_birth?: string | null;
  gender?: 'Male' | 'Female' | 'Other' | null;
  qualification?: string | null;
  specialization?: string | null;
  joining_date: string;
  phone?: string | null;
  address?: string | null;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface TeacherListMeta {
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface TeacherListData {
  teachers: Teacher[];
  meta: TeacherListMeta;
}

export interface TeacherSubjectAssignment {
  id: number;
  teacher_id: number;
  subject_id: number;
  class_id?: number | null;
  academic_year_id?: number | null;
  subject_name?: string;
  subject_code?: string;
  class_name?: string | null;
}

export interface TeacherDocument {
  id: number;
  teacher_id: number;
  document_type: string;
  file_name: string;
  file_path: string;
  is_active: boolean;
  created_at: string;
}

export interface TimetableEntry {
  id: number;
  section_id: number;
  subject_id: number;
  teacher_id: number;
  day_of_week: number;
  period_no: number;
  start_time: string;
  end_time: string;
  section_name?: string;
  subject_name?: string;
  teacher_name?: string;
  class_name?: string;
}

@Injectable({ providedIn: 'root' })
export class TeacherService {
  private readonly apiUrl = '/api/v1/teachers';

  constructor(private http: HttpClient) {}

  getTeachers(page = 1, perPage = 20, search = ''): Observable<ApiResponse<TeacherListData>> {
    let params = new HttpParams()
      .set('page', page.toString())
      .set('per_page', perPage.toString());
    if (search) params = params.set('search', search);
    return this.http.get<ApiResponse<TeacherListData>>(this.apiUrl, { params });
  }

  getTeacherById(id: number): Observable<ApiResponse<Teacher>> {
    return this.http.get<ApiResponse<Teacher>>(`${this.apiUrl}/${id}`);
  }

  createTeacher(data: any): Observable<ApiResponse<Teacher>> {
    return this.http.post<ApiResponse<Teacher>>(this.apiUrl, data);
  }

  updateTeacher(id: number, data: any): Observable<ApiResponse<Teacher>> {
    return this.http.put<ApiResponse<Teacher>>(`${this.apiUrl}/${id}`, data);
  }

  deleteTeacher(id: number): Observable<ApiResponse<any>> {
    return this.http.delete<ApiResponse<any>>(`${this.apiUrl}/${id}`);
  }

  getSubjects(teacherId: number): Observable<ApiResponse<{ subjects: TeacherSubjectAssignment[] }>> {
    return this.http.get<ApiResponse<{ subjects: TeacherSubjectAssignment[] }>>(`${this.apiUrl}/${teacherId}/subjects`);
  }

  assignSubject(teacherId: number, data: { subject_id: number; class_id?: number | null; academic_year_id?: number | null }): Observable<ApiResponse<TeacherSubjectAssignment>> {
    return this.http.post<ApiResponse<TeacherSubjectAssignment>>(`${this.apiUrl}/${teacherId}/subjects`, data);
  }

  unassignSubject(teacherId: number, subjectId: number, classId?: number | null): Observable<ApiResponse<any>> {
    let params = new HttpParams();
    if (classId) params = params.set('class_id', classId.toString());
    return this.http.delete<ApiResponse<any>>(`${this.apiUrl}/${teacherId}/subjects/${subjectId}`, { params });
  }

  getDocuments(teacherId: number): Observable<ApiResponse<{ documents: TeacherDocument[] }>> {
    return this.http.get<ApiResponse<{ documents: TeacherDocument[] }>>(`${this.apiUrl}/${teacherId}/documents`);
  }

  uploadDocument(teacherId: number, formData: FormData): Observable<ApiResponse<TeacherDocument>> {
    return this.http.post<ApiResponse<TeacherDocument>>(`${this.apiUrl}/${teacherId}/documents`, formData);
  }

  deleteDocument(teacherId: number, docId: number): Observable<ApiResponse<any>> {
    return this.http.delete<ApiResponse<any>>(`${this.apiUrl}/${teacherId}/documents/${docId}`);
  }

  getSchedule(teacherId: number): Observable<ApiResponse<{ schedule: TimetableEntry[] }>> {
    return this.http.get<ApiResponse<{ schedule: TimetableEntry[] }>>(`${this.apiUrl}/${teacherId}/schedule`);
  }
}
