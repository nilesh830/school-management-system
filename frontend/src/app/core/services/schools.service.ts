import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiResponse } from '../models/user.model';
import { SuperAdminAuthService } from './superadmin-auth.service';

export interface School {
  id: number;
  name: string;
  slug: string;
  email?: string | null;
  address?: string | null;
  phone?: string | null;
  logo_url?: string | null;
  is_active: boolean;
  academic_year_start_month?: number | null;
  created_at?: string;
  updated_at?: string;
}

export interface SchoolCreatePayload {
  name: string;
  slug: string;
  admin_email: string;
  admin_password: string;
  address?: string;
  phone?: string;
  academic_year_start_month?: number | null;
}

export interface SchoolListMeta {
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface SchoolListData {
  schools: School[];
  meta: SchoolListMeta;
}

@Injectable({ providedIn: 'root' })
export class SchoolsService {
  private readonly apiUrl = '/api/v1/superadmin/schools';
  private http = inject(HttpClient);
  private saAuth = inject(SuperAdminAuthService);

  private get authHeaders(): HttpHeaders {
    const token = this.saAuth.getAccessToken();
    return token
      ? new HttpHeaders({ Authorization: `Bearer ${token}` })
      : new HttpHeaders();
  }

  getSchools(page = 1, perPage = 20, search = ''): Observable<ApiResponse<SchoolListData>> {
    let params = new HttpParams()
      .set('page', page.toString())
      .set('per_page', perPage.toString());
    if (search) {
      params = params.set('search', search);
    }
    return this.http.get<ApiResponse<SchoolListData>>(this.apiUrl, {
      params,
      headers: this.authHeaders
    });
  }

  getSchool(id: number): Observable<ApiResponse<School>> {
    return this.http.get<ApiResponse<School>>(`${this.apiUrl}/${id}`, {
      headers: this.authHeaders
    });
  }

  createSchool(data: SchoolCreatePayload): Observable<ApiResponse<School>> {
    return this.http.post<ApiResponse<School>>(this.apiUrl, data, {
      headers: this.authHeaders
    });
  }

  updateSchool(id: number, data: Partial<School>): Observable<ApiResponse<School>> {
    return this.http.patch<ApiResponse<School>>(`${this.apiUrl}/${id}`, data, {
      headers: this.authHeaders
    });
  }
}
