import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiResponse } from '../models/user.model';

// ── Shared ────────────────────────────────────────────────────────────────────

export type ExportFormat = 'pdf' | 'excel';

// ── Attendance report (SMS-057) ────────────────────────────────────────────────

export interface AttendanceReportStudent {
  student_id: number;
  name?: string;
  student_name?: string;
  admission_no?: string;
  present: number;
  absent: number;
  late: number;
  total: number;
  percentage: number;
}

export interface AttendanceReport {
  section_id: number;
  from_date: string;
  to_date: string;
  class_average: number;
  students: AttendanceReportStudent[];
}

// ── Grades report (SMS-058) ────────────────────────────────────────────────────

export interface GradeSubjectResult {
  subject_id: number;
  subject_name: string;
  marks_obtained: number | null;
  max_marks: number;
  grade?: string | null;
}

export interface GradeStudentResult {
  student_id: number;
  name: string;
  admission_no?: string;
  subjects: GradeSubjectResult[];
  overall_percentage: number | null;
  overall_grade: string | null;
  overall_gpa: number | null;
}

export interface GradesReport {
  exam_id: number;
  section_id?: number | null;
  grade_distribution: Record<string, number>;
  students: GradeStudentResult[];
}

// ── Fees report (SMS-059) ──────────────────────────────────────────────────────

export interface FeeTypeBreakdown {
  fee_type: string;
  collected: number;
  pending: number;
}

export interface FeeDefaulter {
  student_id: number;
  student_name: string;
  roll_number?: string;
  class_name?: string;
  balance_due: number;
}

export interface FeesReport {
  class_id?: number | null;
  academic_year_id?: number | null;
  by_fee_type: FeeTypeBreakdown[];
  totals: {
    collected: number;
    pending: number;
  };
  defaulters: FeeDefaulter[];
}

// ── Service ───────────────────────────────────────────────────────────────────

@Injectable({ providedIn: 'root' })
export class ReportService {
  private readonly apiUrl = '/api/v1/reports';

  constructor(private http: HttpClient) {}

  // ── Attendance ──────────────────────────────────────────────────────────────

  getAttendanceReport(sectionId: number, fromDate: string, toDate: string): Observable<ApiResponse<AttendanceReport>> {
    const params = new HttpParams()
      .set('section_id', sectionId.toString())
      .set('from_date', fromDate)
      .set('to_date', toDate);
    return this.http.get<ApiResponse<AttendanceReport>>(`${this.apiUrl}/attendance`, { params });
  }

  exportAttendanceReport(format: ExportFormat, sectionId: number, fromDate: string, toDate: string): Observable<Blob> {
    const params = new HttpParams()
      .set('format', format)
      .set('section_id', sectionId.toString())
      .set('from_date', fromDate)
      .set('to_date', toDate);
    return this.http.get(`${this.apiUrl}/attendance/export`, { params, responseType: 'blob' });
  }

  // ── Grades ────────────────────────────────────────────────────────────────────

  getGradesReport(examId: number, sectionId?: number): Observable<ApiResponse<GradesReport>> {
    let params = new HttpParams().set('exam_id', examId.toString());
    if (sectionId !== undefined && sectionId !== null) {
      params = params.set('section_id', sectionId.toString());
    }
    return this.http.get<ApiResponse<GradesReport>>(`${this.apiUrl}/grades`, { params });
  }

  exportGradesReport(format: ExportFormat, examId: number, sectionId?: number): Observable<Blob> {
    let params = new HttpParams().set('format', format).set('exam_id', examId.toString());
    if (sectionId !== undefined && sectionId !== null) {
      params = params.set('section_id', sectionId.toString());
    }
    return this.http.get(`${this.apiUrl}/grades/export`, { params, responseType: 'blob' });
  }

  // ── Fees ────────────────────────────────────────────────────────────────────

  getFeesReport(classId?: number, academicYearId?: number): Observable<ApiResponse<FeesReport>> {
    let params = new HttpParams();
    if (classId !== undefined && classId !== null) params = params.set('class_id', classId.toString());
    if (academicYearId !== undefined && academicYearId !== null) {
      params = params.set('academic_year_id', academicYearId.toString());
    }
    return this.http.get<ApiResponse<FeesReport>>(`${this.apiUrl}/fees`, { params });
  }

  exportFeesReport(format: ExportFormat, classId?: number, academicYearId?: number): Observable<Blob> {
    let params = new HttpParams().set('format', format);
    if (classId !== undefined && classId !== null) params = params.set('class_id', classId.toString());
    if (academicYearId !== undefined && academicYearId !== null) {
      params = params.set('academic_year_id', academicYearId.toString());
    }
    return this.http.get(`${this.apiUrl}/fees/export`, { params, responseType: 'blob' });
  }
}
