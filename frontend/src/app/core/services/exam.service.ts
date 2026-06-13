import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiResponse } from '../models/user.model';

// ── Exam interfaces ───────────────────────────────────────────────────────────

export type ExamType = 'midterm' | 'final' | 'unit_test' | 'practical';

export interface Exam {
  id: number;
  name: string;
  term: string;
  exam_type: ExamType;
  section_id: number;
  conducted_date: string | null;
  academic_year_id: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by: number | null;
}

export interface ExamListData {
  exams: Exam[];
}

// ── Service ───────────────────────────────────────────────────────────────────

@Injectable({ providedIn: 'root' })
export class ExamService {
  private readonly apiUrl = '/api/v1/exams';

  constructor(private http: HttpClient) {}

  getExams(sectionId?: number): Observable<ApiResponse<ExamListData>> {
    let params = new HttpParams();
    if (sectionId !== undefined) {
      params = params.set('section_id', sectionId.toString());
    }
    return this.http.get<ApiResponse<ExamListData>>(this.apiUrl, { params });
  }

  getExam(id: number): Observable<ApiResponse<Exam>> {
    return this.http.get<ApiResponse<Exam>>(`${this.apiUrl}/${id}`);
  }

  createExam(payload: Partial<Exam>): Observable<ApiResponse<Exam>> {
    return this.http.post<ApiResponse<Exam>>(this.apiUrl, payload);
  }

  updateExam(id: number, payload: Partial<Exam>): Observable<ApiResponse<Exam>> {
    return this.http.put<ApiResponse<Exam>>(`${this.apiUrl}/${id}`, payload);
  }
}
