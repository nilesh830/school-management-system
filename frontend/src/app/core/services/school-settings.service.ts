import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiResponse } from '../models/user.model';

/** Outbound SMTP config for a school (password is never returned). */
export interface EmailConfig {
  id: number;
  school_slug: string;
  smtp_host: string;
  smtp_port: number;
  smtp_use_tls: boolean;
  smtp_username: string;
  smtp_password_set: boolean;
  from_email: string;
  from_name?: string | null;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface EmailConfigPayload {
  smtp_host: string;
  smtp_port: number;
  smtp_use_tls: boolean;
  smtp_username: string;
  smtp_password?: string | null; // omitted on update = keep existing
  from_email: string;
  from_name?: string | null;
  is_active: boolean;
}

@Injectable({ providedIn: 'root' })
export class SchoolSettingsService {
  private readonly apiUrl = '/api/v1/school';

  constructor(private http: HttpClient) {}

  /** Returns the config, or data:null when none has been set yet. */
  getEmailConfig(): Observable<ApiResponse<EmailConfig | null>> {
    return this.http.get<ApiResponse<EmailConfig | null>>(`${this.apiUrl}/email-config`);
  }

  saveEmailConfig(payload: EmailConfigPayload): Observable<ApiResponse<EmailConfig>> {
    return this.http.put<ApiResponse<EmailConfig>>(`${this.apiUrl}/email-config`, payload);
  }
}
