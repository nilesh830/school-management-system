import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { AvatarModule } from 'primeng/avatar';
import { FileUploadModule, FileUploadEvent } from 'primeng/fileupload';
import { ToastModule } from 'primeng/toast';
import { DividerModule } from 'primeng/divider';
import { MessageService } from 'primeng/api';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../../../core/services/auth.service';
import { User } from '../../../core/models/user.model';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule,
    CardModule, ButtonModule, InputTextModule, AvatarModule,
    FileUploadModule, ToastModule, DividerModule
  ],
  providers: [MessageService],
  templateUrl: './profile.component.html'
})
export class ProfileComponent implements OnInit {
  private fb = inject(FormBuilder);
  private http = inject(HttpClient);
  private auth = inject(AuthService);
  private toast = inject(MessageService);

  form = this.fb.group({
    first_name: ['', Validators.required],
    last_name: ['', Validators.required],
    phone: [''],
    address: ['']
  });

  user: User | null = null;
  loading = false;
  uploadLoading = false;
  photoUrl: string | null = null;

  get initials(): string {
    return this.user ? `${this.user.first_name[0]}${this.user.last_name[0]}`.toUpperCase() : 'U';
  }

  ngOnInit(): void {
    this.http.get<any>('/api/v1/auth/me').subscribe({
      next: (resp) => {
        this.user = resp.data.user ?? resp.data;
        this.photoUrl = this.user?.photo_url ?? null;
        this.form.patchValue({
          first_name: this.user?.first_name,
          last_name: this.user?.last_name
        });
      },
      error: () => {
        this.user = this.auth.currentUser();
        if (this.user) {
          this.form.patchValue({ first_name: this.user.first_name, last_name: this.user.last_name });
          this.photoUrl = this.user.photo_url ?? null;
        }
      }
    });
  }

  onSave(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.loading = true;

    this.http.patch<any>('/api/v1/auth/profile', this.form.value).subscribe({
      next: (resp) => {
        this.loading = false;
        const updated = resp.data?.user ?? resp.data;
        if (updated) {
          this.auth.updateCurrentUser(updated);
          this.user = this.auth.currentUser();
        }
        this.toast.add({ severity: 'success', summary: 'Saved', detail: 'Profile updated successfully.' });
      },
      error: (err) => {
        this.loading = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: err.error?.message || 'Failed to update profile.' });
      }
    });
  }

  onPhotoUpload(event: FileUploadEvent): void {
    // PrimeNG p-fileUpload in auto mode posts the file; handle success response here
    const resp = event.originalEvent as any;
    const body = resp?.body;
    if (body?.data?.photo_url) {
      this.photoUrl = body.data.photo_url;
      this.auth.updateCurrentUser({ photo_url: body.data.photo_url });
    }
    this.toast.add({ severity: 'success', summary: 'Photo Updated', detail: 'Profile photo uploaded successfully.' });
  }

  onPhotoError(): void {
    this.toast.add({ severity: 'error', summary: 'Upload Failed', detail: 'Could not upload photo. Max size is 5 MB.' });
  }
}
