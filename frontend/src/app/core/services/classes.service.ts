import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiResponse } from '../models/user.model';

export interface AcademicYear {
  id: number;
  name: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
  is_active: boolean;
}

export interface ClassRecord {
  id: number;
  name: string;
  grade_level: number;
  description?: string | null;
  academic_year_id?: number | null;
  academic_year_name?: string | null;
  is_active: boolean;
  sections?: Section[];
}

export interface Section {
  id: number;
  name: string;
  class_id: number;
  class_name?: string | null;
  capacity: number;
  class_teacher_id?: number | null;
  class_teacher_name?: string | null;
  is_active: boolean;
  student_count?: number;
}

export interface Subject {
  id: number;
  code: string;
  name: string;
  description?: string | null;
  max_marks: number;
  pass_marks: number;
  is_active: boolean;
}

export interface ListMeta {
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

@Injectable({ providedIn: 'root' })
export class ClassesService {
  private readonly classUrl = '/api/v1/classes';
  private readonly subjectUrl = '/api/v1/subjects';
  private readonly sectionUrl = '/api/v1/sections';
  private readonly ayUrl = '/api/v1/academic-years';

  constructor(private http: HttpClient) {}

  // ── Academic Years ─────────────────────────────────────────────────────────

  getAcademicYears(): Observable<ApiResponse<{ academic_years: AcademicYear[] }>> {
    return this.http.get<ApiResponse<{ academic_years: AcademicYear[] }>>(this.ayUrl);
  }

  getCurrentAcademicYear(): Observable<ApiResponse<AcademicYear>> {
    return this.http.get<ApiResponse<AcademicYear>>(`${this.ayUrl}/current`);
  }

  createAcademicYear(data: any): Observable<ApiResponse<AcademicYear>> {
    return this.http.post<ApiResponse<AcademicYear>>(this.ayUrl, data);
  }

  updateAcademicYear(id: number, data: any): Observable<ApiResponse<AcademicYear>> {
    return this.http.put<ApiResponse<AcademicYear>>(`${this.ayUrl}/${id}`, data);
  }

  deleteAcademicYear(id: number): Observable<ApiResponse<any>> {
    return this.http.delete<ApiResponse<any>>(`${this.ayUrl}/${id}`);
  }

  // ── Classes ────────────────────────────────────────────────────────────────

  getClasses(page = 1, perPage = 20, search = ''): Observable<ApiResponse<{ classes: ClassRecord[]; meta: ListMeta }>> {
    let params = new HttpParams()
      .set('page', page.toString())
      .set('per_page', perPage.toString());
    if (search) params = params.set('search', search);
    return this.http.get<ApiResponse<{ classes: ClassRecord[]; meta: ListMeta }>>(this.classUrl, { params });
  }

  getClassById(id: number): Observable<ApiResponse<ClassRecord>> {
    return this.http.get<ApiResponse<ClassRecord>>(`${this.classUrl}/${id}`);
  }

  createClass(data: any): Observable<ApiResponse<ClassRecord>> {
    return this.http.post<ApiResponse<ClassRecord>>(this.classUrl, data);
  }

  updateClass(id: number, data: any): Observable<ApiResponse<ClassRecord>> {
    return this.http.put<ApiResponse<ClassRecord>>(`${this.classUrl}/${id}`, data);
  }

  deleteClass(id: number): Observable<ApiResponse<any>> {
    return this.http.delete<ApiResponse<any>>(`${this.classUrl}/${id}`);
  }

  // ── Subjects ───────────────────────────────────────────────────────────────

  getSubjects(page = 1, perPage = 50, search = ''): Observable<ApiResponse<{ subjects: Subject[]; meta: ListMeta }>> {
    let params = new HttpParams()
      .set('page', page.toString())
      .set('per_page', perPage.toString());
    if (search) params = params.set('search', search);
    return this.http.get<ApiResponse<{ subjects: Subject[]; meta: ListMeta }>>(this.subjectUrl, { params });
  }

  getSubjectById(id: number): Observable<ApiResponse<Subject>> {
    return this.http.get<ApiResponse<Subject>>(`${this.subjectUrl}/${id}`);
  }

  createSubject(data: any): Observable<ApiResponse<Subject>> {
    return this.http.post<ApiResponse<Subject>>(this.subjectUrl, data);
  }

  updateSubject(id: number, data: any): Observable<ApiResponse<Subject>> {
    return this.http.put<ApiResponse<Subject>>(`${this.subjectUrl}/${id}`, data);
  }

  deleteSubject(id: number): Observable<ApiResponse<any>> {
    return this.http.delete<ApiResponse<any>>(`${this.subjectUrl}/${id}`);
  }

  // ── Sections ───────────────────────────────────────────────────────────────

  getSections(classId?: number, page = 1, perPage = 50): Observable<ApiResponse<{ sections: Section[]; meta: ListMeta }>> {
    let params = new HttpParams()
      .set('page', page.toString())
      .set('per_page', perPage.toString());
    if (classId) params = params.set('class_id', classId.toString());
    return this.http.get<ApiResponse<{ sections: Section[]; meta: ListMeta }>>(this.sectionUrl, { params });
  }

  getSectionById(id: number): Observable<ApiResponse<Section>> {
    return this.http.get<ApiResponse<Section>>(`${this.sectionUrl}/${id}`);
  }

  createSection(data: any): Observable<ApiResponse<Section>> {
    return this.http.post<ApiResponse<Section>>(this.sectionUrl, data);
  }

  updateSection(id: number, data: any): Observable<ApiResponse<Section>> {
    return this.http.put<ApiResponse<Section>>(`${this.sectionUrl}/${id}`, data);
  }

  deleteSection(id: number): Observable<ApiResponse<any>> {
    return this.http.delete<ApiResponse<any>>(`${this.sectionUrl}/${id}`);
  }

  enrollStudent(sectionId: number, studentId: number, academicYearId?: number): Observable<ApiResponse<any>> {
    return this.http.post<ApiResponse<any>>(`${this.sectionUrl}/${sectionId}/enroll`, {
      student_id: studentId,
      academic_year_id: academicYearId
    });
  }

  unenrollStudent(sectionId: number, studentId: number): Observable<ApiResponse<any>> {
    return this.http.delete<ApiResponse<any>>(`${this.sectionUrl}/${sectionId}/students/${studentId}`);
  }
}
