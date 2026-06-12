import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiResponse } from '../models/user.model';
import { TimetableEntry } from './teacher.service';

export { TimetableEntry };

@Injectable({ providedIn: 'root' })
export class TimetableService {
  private readonly apiUrl = '/api/v1/timetables';

  constructor(private http: HttpClient) {}

  getBySection(sectionId: number): Observable<ApiResponse<{ timetable: TimetableEntry[] }>> {
    const params = new HttpParams().set('section_id', sectionId.toString());
    return this.http.get<ApiResponse<{ timetable: TimetableEntry[] }>>(this.apiUrl, { params });
  }

  getByTeacher(teacherId: number): Observable<ApiResponse<{ timetable: TimetableEntry[] }>> {
    const params = new HttpParams().set('teacher_id', teacherId.toString());
    return this.http.get<ApiResponse<{ timetable: TimetableEntry[] }>>(this.apiUrl, { params });
  }

  create(data: any): Observable<ApiResponse<TimetableEntry>> {
    return this.http.post<ApiResponse<TimetableEntry>>(this.apiUrl, data);
  }

  update(id: number, data: any): Observable<ApiResponse<TimetableEntry>> {
    return this.http.put<ApiResponse<TimetableEntry>>(`${this.apiUrl}/${id}`, data);
  }

  delete(id: number): Observable<ApiResponse<any>> {
    return this.http.delete<ApiResponse<any>>(`${this.apiUrl}/${id}`);
  }
}
