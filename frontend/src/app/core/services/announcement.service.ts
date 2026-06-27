import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiResponse } from '../models/user.model';

// ── Announcement interfaces ────────────────────────────────────────────────────

export type AnnouncementStatus = 'draft' | 'published' | 'archived';

export interface Announcement {
  id: number;
  title: string;
  content: string;
  target_roles: string[] | null;
  target_class_ids: number[] | null;
  status: AnnouncementStatus;
  published_at: string | null;
  expires_at: string | null;
  created_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface AnnouncementListData {
  announcements: Announcement[];
}

export interface AnnouncementPublishData extends Announcement {
  notified_count: number;
}

export interface AnnouncementPayload {
  title: string;
  content: string;
  target_roles?: string[] | null;
  target_class_ids?: number[] | null;
  publish_at?: string | null;
  expires_at?: string | null;
  status?: AnnouncementStatus;
}

// ── Service ─────────────────────────────────────────────────────────────────────

@Injectable({ providedIn: 'root' })
export class AnnouncementService {
  private http = inject(HttpClient);
  private readonly apiUrl = '/api/v1/announcements';

  /** POST /api/v1/announcements */
  create(payload: AnnouncementPayload): Observable<ApiResponse<Announcement>> {
    return this.http.post<ApiResponse<Announcement>>(this.apiUrl, payload);
  }

  /** GET /api/v1/announcements (admin gets all) */
  getAll(): Observable<ApiResponse<AnnouncementListData>> {
    return this.http.get<ApiResponse<AnnouncementListData>>(this.apiUrl);
  }

  /** GET /api/v1/announcements?role_view=true (announcements visible to current role) */
  getRoleView(): Observable<ApiResponse<AnnouncementListData>> {
    const params = new HttpParams().set('role_view', 'true');
    return this.http.get<ApiResponse<AnnouncementListData>>(this.apiUrl, { params });
  }

  /** GET /api/v1/announcements/:id */
  get(id: number): Observable<ApiResponse<Announcement>> {
    return this.http.get<ApiResponse<Announcement>>(`${this.apiUrl}/${id}`);
  }

  /** PUT /api/v1/announcements/:id */
  update(id: number, payload: Partial<AnnouncementPayload>): Observable<ApiResponse<Announcement>> {
    return this.http.put<ApiResponse<Announcement>>(`${this.apiUrl}/${id}`, payload);
  }

  /** POST /api/v1/announcements/:id/publish */
  publish(id: number): Observable<ApiResponse<AnnouncementPublishData>> {
    return this.http.post<ApiResponse<AnnouncementPublishData>>(`${this.apiUrl}/${id}/publish`, {});
  }
}
