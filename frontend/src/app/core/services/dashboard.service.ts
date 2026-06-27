import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiResponse } from '../models/user.model';

// ── Admin dashboard interfaces ────────────────────────────────────────────────

export interface AttendanceTodaySnapshot {
  present: number;
  absent: number;
  late: number;
  percentage: number;
}

export interface FeeCollectionThisMonth {
  collected: number;
  pending: number;
}

export interface RecentAnnouncement {
  id: number;
  title: string;
  content?: string;
  published_at?: string | null;
}

export interface LowAttendanceStudent {
  student_id: number;
  name: string;
  percentage: number;
}

export interface AdminKpis {
  total_students: number;
  total_teachers: number;
  attendance_today: AttendanceTodaySnapshot;
  fee_collection_this_month: FeeCollectionThisMonth;
  pending_leave_applications: number;
  recent_announcements: RecentAnnouncement[];
  low_attendance_students: LowAttendanceStudent[];
  fee_defaulters_count: number;
}

// ── Service ───────────────────────────────────────────────────────────────────

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private readonly apiUrl = '/api/v1/dashboard';

  constructor(private http: HttpClient) {}

  /** GET /api/v1/dashboard/admin */
  getAdminKpis(): Observable<ApiResponse<AdminKpis>> {
    return this.http.get<ApiResponse<AdminKpis>>(`${this.apiUrl}/admin`);
  }
}
