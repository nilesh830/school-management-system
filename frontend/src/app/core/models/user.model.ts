export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  full_name?: string;
  role: 'admin' | 'teacher' | 'student' | 'parent';
  photo_url?: string | null;
  is_active?: boolean;
  last_login?: string | null;
  created_at?: string;
}

export interface ApiResponse<T = any> {
  success: boolean;
  data: T;
  message: string;
  errors: any;
}
