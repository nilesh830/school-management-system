export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: 'admin' | 'teacher' | 'student' | 'parent';
  photo_url?: string | null;
  last_login?: string | null;
}

export interface ApiResponse<T = any> {
  success: boolean;
  data: T;
  message: string;
  errors: any;
}
