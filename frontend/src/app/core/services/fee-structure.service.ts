import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export type FeeApplicability = 'mandatory' | 'optional';
export type FeeSourceKind = 'flat' | 'transport';

export interface FeeStructure {
  id: number;
  class_id: number;
  academic_year_id: number;
  fee_type: string;
  amount: number;
  due_date: string | null;
  is_recurring: boolean;
  frequency: string;
  is_active: boolean;
  // SMS-066 — Fee applicability (optional/opt-in fees)
  applicability: FeeApplicability;
  source_kind: FeeSourceKind;
  transport_route_id: number | null;
}

export interface FeePayment {
  id: number;
  fee_record_id: number;
  amount_paid: number;
  payment_method: string;
  payment_date: string;
  receipt_no: string;
  transaction_reference: string | null;
  remarks: string | null;
  created_at: string;
}

export interface FeeDiscount {
  id: number;
  discount_type: string;
  amount: number;
  reason: string | null;
  approved_by: number | null;
  approved_at: string | null;
  created_at: string;
}

export interface FeeRecord {
  id: number;
  student_id: number;
  fee_structure_id: number;
  amount: number;
  amount_due: number;
  amount_paid: number;
  discount: number;
  net_amount: number;
  due_date: string | null;
  period?: string;
  fee_type?: string | null;
  frequency?: string | null;
  status: 'pending' | 'partial' | 'paid' | 'waived';
  payments: FeePayment[];
  discounts: FeeDiscount[];
}

@Injectable({ providedIn: 'root' })
export class FeeStructureService {
  private http = inject(HttpClient);
  private readonly apiUrl = '/api/v1/fee-structures';
  private readonly feesApiUrl = '/api/v1/fees';

  getFeeStructures(classId?: number, academicYearId?: number): Observable<any> {
    let params = new HttpParams();
    if (classId !== undefined) params = params.set('class_id', classId.toString());
    if (academicYearId !== undefined) params = params.set('academic_year_id', academicYearId.toString());
    return this.http.get(this.apiUrl, { params });
  }

  createFeeStructure(data: Partial<FeeStructure>): Observable<any> {
    return this.http.post(this.apiUrl, data);
  }

  updateFeeStructure(id: number, data: Partial<FeeStructure>): Observable<any> {
    return this.http.put(`${this.apiUrl}/${id}`, data);
  }

  deleteFeeStructure(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${id}`);
  }

  /** POST /api/v1/fee-structures/:id/generate — create FeeRecords for every student in the class */
  generateFeeRecords(id: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/${id}/generate`, {});
  }

  getFeeRecords(studentId: number): Observable<any> {
    const params = new HttpParams().set('student_id', studentId.toString());
    return this.http.get(`${this.feesApiUrl}/records`, { params });
  }

  recordPayment(payload: any): Observable<any> {
    return this.http.post(`${this.feesApiUrl}/payments`, payload);
  }

  downloadReceipt(paymentId: number): Observable<Blob> {
    return this.http.get(`${this.feesApiUrl}/payments/${paymentId}/receipt`, {
      responseType: 'blob',
    });
  }

  getDefaulters(classId?: number): Observable<any> {
    let params = new HttpParams();
    if (classId !== undefined) params = params.set('class_id', classId.toString());
    return this.http.get(`${this.feesApiUrl}/defaulters`, { params });
  }

  getFeeRecord(recordId: number): Observable<any> {
    return this.http.get(`${this.feesApiUrl}/records/${recordId}`);
  }

  applyDiscount(recordId: number, payload: { discount_type: string; amount: number; reason?: string }): Observable<any> {
    return this.http.post(`${this.feesApiUrl}/records/${recordId}/discount`, payload);
  }
}
