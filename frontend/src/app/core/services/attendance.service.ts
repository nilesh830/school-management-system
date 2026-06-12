import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiResponse } from '../models/user.model';

// ── Shared interfaces ──────────────────────────────────────────────────────

export type AttendanceStatus = 'present' | 'absent' | 'late' | 'leave' | 'holiday';

export interface AttendanceRecord {
  id: number;
  student_id: number;
  section_id: number;
  date: string;
  status: AttendanceStatus;
  remarks?: string | null;
  marked_by?: number | null;
  created_at?: string;
  updated_at?: string;
}

export interface AttendanceMarkEntry {
  student_id: number;
  status: AttendanceStatus;
}

export interface AttendanceMarkPayload {
  section_id: number;
  date: string;
  records: AttendanceMarkEntry[];
}

export interface AttendanceMarkResponse {
  section_id: number;
  date: string;
  records_created: number;
}

export interface StudentAttendanceData {
  attendance: AttendanceRecord[];
}

export interface StudentSummary {
  student_id: number;
  student_name?: string;
  admission_no?: string;
  present: number;
  absent: number;
  late: number;
  leave: number;
  holiday: number;
  total: number;
}

export interface AttendanceReportData {
  section_id: number;
  from_date: string;
  to_date: string;
  total_records: number;
  student_summaries: StudentSummary[];
}

export interface TodaySummaryData {
  present: number;
  absent: number;
  late: number;
  leave: number;
  holiday: number;
  total: number;
  date: string;
}

// ── Service ────────────────────────────────────────────────────────────────

@Injectable({ providedIn: 'root' })
export class AttendanceService {
  private readonly apiUrl = '/api/v1/attendance';

  constructor(private http: HttpClient) {}

  markAttendance(payload: AttendanceMarkPayload): Observable<ApiResponse<AttendanceMarkResponse>> {
    return this.http.post<ApiResponse<AttendanceMarkResponse>>(`${this.apiUrl}/mark`, payload);
  }

  getAttendance(studentId: number, month: number, year: number): Observable<ApiResponse<StudentAttendanceData>> {
    const params = new HttpParams()
      .set('student_id', studentId.toString())
      .set('month', month.toString())
      .set('year', year.toString());
    return this.http.get<ApiResponse<StudentAttendanceData>>(this.apiUrl, { params });
  }

  getReport(sectionId: number, fromDate: string, toDate: string): Observable<ApiResponse<AttendanceReportData>> {
    const params = new HttpParams()
      .set('section_id', sectionId.toString())
      .set('from_date', fromDate)
      .set('to_date', toDate);
    return this.http.get<ApiResponse<AttendanceReportData>>(`${this.apiUrl}/report`, { params });
  }

  getTodaySummary(): Observable<ApiResponse<TodaySummaryData>> {
    return this.http.get<ApiResponse<TodaySummaryData>>(`${this.apiUrl}/today-summary`);
  }
}
