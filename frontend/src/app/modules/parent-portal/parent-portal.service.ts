import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ParentPortalService {
  private http = inject(HttpClient);
  private readonly apiUrl = '/api/v1/parent-portal';
  private readonly feesApiUrl = '/api/v1/fees';
  private readonly leaveApiUrl = '/api/v1/leave-applications';
  private readonly notifApiUrl = '/api/v1/notifications';
  private readonly parentsApiUrl = '/api/v1/parents';

  /** GET /api/v1/parent-portal/dashboard */
  getDashboard(): Observable<any> {
    return this.http.get(`${this.apiUrl}/dashboard`);
  }

  /** GET /api/v1/parent-portal/children */
  getChildren(): Observable<any> {
    return this.http.get(`${this.apiUrl}/children`);
  }

  /** GET /api/v1/parent-portal/children/:id/attendance */
  getChildAttendance(childId: number, month?: number, year?: number): Observable<any> {
    let params = new HttpParams();
    if (month !== undefined) params = params.set('month', month.toString());
    if (year !== undefined) params = params.set('year', year.toString());
    return this.http.get(`${this.apiUrl}/children/${childId}/attendance`, { params });
  }

  /** GET /api/v1/parent-portal/children/:id/grades */
  getChildGrades(childId: number): Observable<any> {
    return this.http.get(`${this.apiUrl}/children/${childId}/grades`);
  }

  /** GET /api/v1/parent-portal/children/:id/fees */
  getChildFees(childId: number): Observable<any> {
    return this.http.get(`${this.apiUrl}/children/${childId}/fees`);
  }

  /** GET /api/v1/parent-portal/children/:id/report-card/:examId — returns PDF blob */
  downloadReportCard(childId: number, examId: number): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/children/${childId}/report-card/${examId}`, {
      responseType: 'blob'
    });
  }

  /** GET /api/v1/fees/payments/:id/receipt — returns PDF blob */
  downloadReceipt(paymentId: number): Observable<Blob> {
    return this.http.get(`${this.feesApiUrl}/payments/${paymentId}/receipt`, {
      responseType: 'blob'
    });
  }

  // ── Leave Applications ────────────────────────────────────────────────────

  /** GET /api/v1/leave-applications */
  getMyLeaves(): Observable<any> {
    return this.http.get(this.leaveApiUrl);
  }

  /** POST /api/v1/leave-applications */
  submitLeave(data: any): Observable<any> {
    return this.http.post(this.leaveApiUrl, data);
  }

  // ── Messaging ─────────────────────────────────────────────────────────────

  /** GET /api/v1/parent-portal/messages/threads */
  getThreads(): Observable<any> {
    return this.http.get(`${this.apiUrl}/messages/threads`);
  }

  /** POST /api/v1/parent-portal/messages/threads */
  createThread(data: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/messages/threads`, data);
  }

  /** GET /api/v1/parent-portal/messages/threads/:threadId */
  getThread(threadId: string): Observable<any> {
    return this.http.get(`${this.apiUrl}/messages/threads/${threadId}`);
  }

  /** POST /api/v1/parent-portal/messages/threads/:threadId/reply */
  replyToThread(threadId: string, body: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/messages/threads/${threadId}/reply`, { message: body });
  }

  /** PUT /api/v1/parent-portal/messages/threads/:threadId/read */
  markThreadRead(threadId: string): Observable<any> {
    return this.http.put(`${this.apiUrl}/messages/threads/${threadId}/read`, {});
  }

  // ── Notifications ─────────────────────────────────────────────────────────

  /** GET /api/v1/notifications?unread=true|false */
  getNotifications(unreadOnly: boolean): Observable<any> {
    const params = new HttpParams().set('unread', unreadOnly ? 'true' : 'false');
    return this.http.get(this.notifApiUrl, { params });
  }

  /** PUT /api/v1/notifications/:id/read */
  markNotificationRead(id: number): Observable<any> {
    return this.http.put(`${this.notifApiUrl}/${id}/read`, {});
  }

  /** PUT /api/v1/notifications/read-all */
  markAllNotificationsRead(): Observable<any> {
    return this.http.put(`${this.notifApiUrl}/read-all`, {});
  }

  // ── Parent Profile ────────────────────────────────────────────────────────

  /** GET /api/v1/parents/me */
  getMyProfile(): Observable<any> {
    return this.http.get(`${this.parentsApiUrl}/me`);
  }

  /** PATCH /api/v1/parents/me */
  updateMyProfile(data: any): Observable<any> {
    return this.http.patch(`${this.parentsApiUrl}/me`, data);
  }
}
