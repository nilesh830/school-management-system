import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { InputTextModule } from 'primeng/inputtext';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { ToastModule } from 'primeng/toast';
import { SkeletonModule } from 'primeng/skeleton';
import { MessageService } from 'primeng/api';
import { ParentPortalService } from '../parent-portal.service';

@Component({
  selector: 'app-parent-profile',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    InputTextModule,
    ButtonModule,
    CardModule,
    ToastModule,
    SkeletonModule
  ],
  providers: [MessageService],
  template: `
    <p-toast />

    <div>
      <!-- Page header -->
      <div class="flex align-items-center gap-2 mb-4">
        <i class="pi pi-user text-primary text-xl"></i>
        <h2 class="text-lg font-bold text-900 m-0">My Profile</h2>
      </div>

      <!-- Loading skeleton -->
      @if (loading) {
        <p-card styleClass="shadow-1">
          <div class="grid">
            @for (n of [1,2,3,4,5,6]; track n) {
              <div class="col-12 md:col-6">
                <p-skeleton height="2.5rem" borderRadius="6px" styleClass="mb-2" />
              </div>
            }
          </div>
        </p-card>
      }

      <!-- Profile form -->
      @if (!loading) {
        <p-card styleClass="shadow-1">
          <form [formGroup]="form" (ngSubmit)="onSave()">
            <div class="grid">
              <!-- First name -->
              <div class="col-12 md:col-6">
                <div class="field">
                  <label class="block text-sm font-medium text-700 mb-1">First Name <span class="text-red-500">*</span></label>
                  <input
                    pInputText
                    formControlName="first_name"
                    class="w-full"
                    placeholder="First name"
                  />
                  @if (form.get('first_name')?.invalid && form.get('first_name')?.touched) {
                    <small class="text-red-500">First name is required.</small>
                  }
                </div>
              </div>

              <!-- Last name -->
              <div class="col-12 md:col-6">
                <div class="field">
                  <label class="block text-sm font-medium text-700 mb-1">Last Name <span class="text-red-500">*</span></label>
                  <input
                    pInputText
                    formControlName="last_name"
                    class="w-full"
                    placeholder="Last name"
                  />
                  @if (form.get('last_name')?.invalid && form.get('last_name')?.touched) {
                    <small class="text-red-500">Last name is required.</small>
                  }
                </div>
              </div>

              <!-- Email (read-only) -->
              <div class="col-12 md:col-6">
                <div class="field">
                  <label class="block text-sm font-medium text-700 mb-1">Email</label>
                  <input
                    pInputText
                    formControlName="email"
                    class="w-full"
                    [readonly]="true"
                    style="background: #f8fafc; color: #64748b"
                  />
                  <small class="text-400">Email cannot be changed.</small>
                </div>
              </div>

              <!-- Primary phone -->
              <div class="col-12 md:col-6">
                <div class="field">
                  <label class="block text-sm font-medium text-700 mb-1">Primary Phone</label>
                  <input
                    pInputText
                    formControlName="phone_primary"
                    class="w-full"
                    placeholder="Primary contact number"
                  />
                </div>
              </div>

              <!-- Secondary phone -->
              <div class="col-12 md:col-6">
                <div class="field">
                  <label class="block text-sm font-medium text-700 mb-1">Secondary Phone</label>
                  <input
                    pInputText
                    formControlName="phone_secondary"
                    class="w-full"
                    placeholder="Alternate contact number"
                  />
                </div>
              </div>

              <!-- Occupation -->
              <div class="col-12 md:col-6">
                <div class="field">
                  <label class="block text-sm font-medium text-700 mb-1">Occupation</label>
                  <input
                    pInputText
                    formControlName="occupation"
                    class="w-full"
                    placeholder="Your occupation"
                  />
                </div>
              </div>

              <!-- Address -->
              <div class="col-12">
                <div class="field">
                  <label class="block text-sm font-medium text-700 mb-1">Address</label>
                  <input
                    pInputText
                    formControlName="address"
                    class="w-full"
                    placeholder="Residential address"
                  />
                </div>
              </div>
            </div>

            <!-- Save button -->
            <div class="flex justify-content-end mt-2">
              <p-button
                label="Save Changes"
                icon="pi pi-check"
                type="submit"
                [loading]="saving"
                [disabled]="form.invalid || form.pristine"
              />
            </div>
          </form>
        </p-card>
      }
    </div>
  `
})
export class ParentProfileComponent implements OnInit {
  private portalService = inject(ParentPortalService);
  private toast = inject(MessageService);
  private fb = inject(FormBuilder);

  loading = false;
  saving = false;

  form = this.fb.group({
    first_name: ['', Validators.required],
    last_name: ['', Validators.required],
    email: [{ value: '', disabled: true }],
    phone_primary: [''],
    phone_secondary: [''],
    occupation: [''],
    address: ['']
  });

  ngOnInit(): void {
    this.loadProfile();
  }

  loadProfile(): void {
    this.loading = true;
    this.portalService.getMyProfile().subscribe({
      next: (res) => {
        const profile = res.data?.parent ?? res.data ?? {};
        this.form.patchValue({
          first_name: profile.first_name ?? '',
          last_name: profile.last_name ?? '',
          email: profile.email ?? '',
          phone_primary: profile.phone_primary ?? '',
          phone_secondary: profile.phone_secondary ?? '',
          occupation: profile.occupation ?? '',
          address: profile.address ?? ''
        });
        this.form.markAsPristine();
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load profile.' });
      }
    });
  }

  onSave(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving = true;

    // Only send changed (dirty) fields
    const raw = this.form.getRawValue();
    const payload: Record<string, any> = {};
    const fields: (keyof typeof raw)[] = ['first_name', 'last_name', 'phone_primary', 'phone_secondary', 'occupation', 'address'];
    fields.forEach(key => {
      if (raw[key] !== null && raw[key] !== undefined) {
        payload[key] = raw[key];
      }
    });

    this.portalService.updateMyProfile(payload).subscribe({
      next: () => {
        this.saving = false;
        this.form.markAsPristine();
        this.toast.add({ severity: 'success', summary: 'Saved', detail: 'Profile updated successfully.' });
      },
      error: (err: any) => {
        this.saving = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: err?.error?.message ?? 'Failed to update profile.' });
      }
    });
  }
}
