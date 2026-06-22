import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiResponse } from '../models/user.model';

export interface TransportRoute {
  id: number;
  name: string;
  description: string | null;
  stops: string[];
  is_active: boolean;
}

export interface TransportVehicle {
  id: number;
  registration_no: string;
  capacity: number;
  driver_name: string | null;
  driver_phone: string | null;
  route_id: number | null;
  route_name: string | null;
  is_active: boolean;
}

export interface StudentTransportAssignment {
  id: number;
  student_id: number;
  student_name: string | null;
  admission_no: string | null;
  route_id: number;
  route_name: string | null;
  pickup_stop: string | null;
  drop_stop: string | null;
  academic_year_id: number;
  is_active: boolean;
}

@Injectable({ providedIn: 'root' })
export class TransportService {
  private http = inject(HttpClient);
  private readonly apiUrl = '/api/v1/transport';

  // ── Routes ────────────────────────────────────────────────────────────────
  getRoutes(): Observable<ApiResponse<{ routes: TransportRoute[] }>> {
    return this.http.get<ApiResponse<{ routes: TransportRoute[] }>>(`${this.apiUrl}/routes`);
  }

  createRoute(payload: Partial<TransportRoute>): Observable<ApiResponse<TransportRoute>> {
    return this.http.post<ApiResponse<TransportRoute>>(`${this.apiUrl}/routes`, payload);
  }

  updateRoute(id: number, payload: Partial<TransportRoute>): Observable<ApiResponse<TransportRoute>> {
    return this.http.put<ApiResponse<TransportRoute>>(`${this.apiUrl}/routes/${id}`, payload);
  }

  deleteRoute(id: number): Observable<ApiResponse<any>> {
    return this.http.delete<ApiResponse<any>>(`${this.apiUrl}/routes/${id}`);
  }

  // ── Vehicles ──────────────────────────────────────────────────────────────
  getVehicles(routeId?: number): Observable<ApiResponse<{ vehicles: TransportVehicle[] }>> {
    let params = new HttpParams();
    if (routeId !== undefined && routeId !== null) params = params.set('route_id', routeId.toString());
    return this.http.get<ApiResponse<{ vehicles: TransportVehicle[] }>>(`${this.apiUrl}/vehicles`, { params });
  }

  createVehicle(payload: Partial<TransportVehicle>): Observable<ApiResponse<TransportVehicle>> {
    return this.http.post<ApiResponse<TransportVehicle>>(`${this.apiUrl}/vehicles`, payload);
  }

  updateVehicle(id: number, payload: Partial<TransportVehicle>): Observable<ApiResponse<TransportVehicle>> {
    return this.http.put<ApiResponse<TransportVehicle>>(`${this.apiUrl}/vehicles/${id}`, payload);
  }

  // ── Student assignments ─────────────────────────────────────────────────────
  getAssignments(routeId?: number): Observable<ApiResponse<{ assignments: StudentTransportAssignment[] }>> {
    let params = new HttpParams();
    if (routeId !== undefined && routeId !== null) params = params.set('route_id', routeId.toString());
    return this.http.get<ApiResponse<{ assignments: StudentTransportAssignment[] }>>(`${this.apiUrl}/assignments`, { params });
  }

  assignStudent(payload: {
    student_id: number;
    route_id: number;
    pickup_stop?: string | null;
    drop_stop?: string | null;
    academic_year_id: number;
  }): Observable<ApiResponse<StudentTransportAssignment>> {
    return this.http.post<ApiResponse<StudentTransportAssignment>>(`${this.apiUrl}/assignments`, payload);
  }

  unassign(id: number): Observable<ApiResponse<any>> {
    return this.http.delete<ApiResponse<any>>(`${this.apiUrl}/assignments/${id}`);
  }

  getStudentTransport(studentId: number): Observable<ApiResponse<{ transport: StudentTransportAssignment | null }>> {
    return this.http.get<ApiResponse<{ transport: StudentTransportAssignment | null }>>(`/api/v1/students/${studentId}/transport`);
  }
}
