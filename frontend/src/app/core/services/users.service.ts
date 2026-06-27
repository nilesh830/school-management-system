import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiResponse, User } from '../models/user.model';

export interface UserListMeta {
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface UserListData {
  users: User[];
  meta: UserListMeta;
}

@Injectable({ providedIn: 'root' })
export class UsersService {
  private readonly apiUrl = '/api/v1/users';

  constructor(private http: HttpClient) {}

  getUsers(
    page = 1,
    perPage = 20,
    role?: string | null,
    search?: string | null,
    isActive?: boolean | null
  ): Observable<ApiResponse<UserListData>> {
    let params = new HttpParams().set('page', page).set('per_page', perPage);
    if (role) params = params.set('role', role);
    if (search) params = params.set('q', search);
    if (isActive !== null && isActive !== undefined) params = params.set('is_active', isActive);
    return this.http.get<ApiResponse<UserListData>>(this.apiUrl, { params });
  }

  updateUser(
    id: number,
    payload: Partial<{ first_name: string; last_name: string; email: string; password: string }>
  ): Observable<ApiResponse<{ user: User }>> {
    return this.http.patch<ApiResponse<{ user: User }>>(`${this.apiUrl}/${id}`, payload);
  }

  activateUser(id: number): Observable<ApiResponse<{ user: User }>> {
    return this.http.patch<ApiResponse<{ user: User }>>(`${this.apiUrl}/${id}/activate`, {});
  }

  getUser(id: number): Observable<ApiResponse<User>> {
    return this.http.get<ApiResponse<User>>(`${this.apiUrl}/${id}`);
  }

  deactivateUser(id: number): Observable<ApiResponse<User>> {
    return this.http.delete<ApiResponse<User>>(`${this.apiUrl}/${id}`);
  }
}
