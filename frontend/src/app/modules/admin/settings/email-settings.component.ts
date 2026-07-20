import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators, AbstractControl } from '@angular/forms';
import { MessageService } from 'primeng/api';

import { CardModule } from 'primeng/card';
import { ToolbarModule } from 'primeng/toolbar';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { InputNumberModule } from 'primeng/inputnumber';
import { InputSwitchModule } from 'primeng/inputswitch';
import { ToastModule } from 'primeng/toast';
import { MessageModule } from 'primeng/message';
import { DividerModule } from 'primeng/divider';

import {
  SchoolSettingsService,
  EmailConfig,
  EmailConfigPayload
} from '../../../core/services/school-settings.service';

@Component({
  selector: 'app-email-settings',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    CardModule,
    ToolbarModule,
    ButtonModule,
    InputTextModule,
    InputNumberModule,
    InputSwitchModule,
    ToastModule,
    MessageModule,
    DividerModule
  ],
  providers: [MessageService],
  template: `
    <p-toast position="top-right" />

    <p-card>
      <p-toolbar styleClass="mb-4">
        <ng-template pTemplate="left">
          <h2 class="text-xl font-bold text-900 m-0">Email / SMTP Settings</h2>
        </ng-template>
      </p-toolbar>

      <p class="text-700 line-height-3 mb-3">
        Configure your school's outbound email server. These credentials are used
        to send login details to students created via
        <span class="font-medium">Bulk Import</span>, sent
        <span class="font-medium">from your school's own address</span>. Leave this
        unset and bulk-created students simply won't be emailed their credentials.
      </p>

      <p-message
        *ngIf="loaded && !existing"
        severity="info"
        text="No email server configured yet. Fill in the details below and save."
        styleClass="mb-3 block"
      />
      <p-message
        *ngIf="existing"
        severity="success"
        [text]="'Configured — sending from ' + existing.from_email"
        styleClass="mb-3 block"
      />

      <form [formGroup]="form" (ngSubmit)="onSubmit()" class="p-fluid formgrid grid" *ngIf="loaded">
        <div class="field col-12 md:col-8">
          <label for="host">SMTP Host *</label>
          <input pInputText id="host" formControlName="smtp_host" placeholder="smtp.gmail.com" />
          <small class="p-error" *ngIf="invalid('smtp_host')">SMTP host is required.</small>
        </div>

        <div class="field col-6 md:col-2">
          <label for="port">Port *</label>
          <p-inputNumber inputId="port" formControlName="smtp_port" [useGrouping]="false" [min]="1" [max]="65535" />
          <small class="p-error" *ngIf="invalid('smtp_port')">Port is required.</small>
        </div>

        <div class="field col-6 md:col-2 flex flex-column">
          <label for="tls">Use TLS</label>
          <p-inputSwitch inputId="tls" formControlName="smtp_use_tls" />
        </div>

        <div class="field col-12 md:col-6">
          <label for="user">SMTP Username *</label>
          <input pInputText id="user" formControlName="smtp_username" placeholder="mailer@yourschool.edu" />
          <small class="p-error" *ngIf="invalid('smtp_username')">Username is required.</small>
        </div>

        <div class="field col-12 md:col-6">
          <label for="pw">SMTP Password / App Password {{ existing ? '' : '*' }}</label>
          <input pInputText id="pw" type="password" formControlName="smtp_password"
                 [placeholder]="existing ? 'Leave blank to keep current password' : 'App password'"
                 autocomplete="new-password" />
          <small class="p-error" *ngIf="invalid('smtp_password')">Password is required.</small>
          <small class="text-500" *ngIf="existing?.smtp_password_set">A password is already saved.</small>
        </div>

        <div class="col-12"><p-divider /></div>

        <div class="field col-12 md:col-6">
          <label for="from">From Email *</label>
          <input pInputText id="from" formControlName="from_email" placeholder="noreply@yourschool.edu" />
          <small class="p-error" *ngIf="invalid('from_email')">A valid sender email is required.</small>
        </div>

        <div class="field col-12 md:col-6">
          <label for="fromName">From Name</label>
          <input pInputText id="fromName" formControlName="from_name" placeholder="Greenwood High School" />
        </div>

        <div class="field col-12 md:col-3 flex flex-column">
          <label for="active">Active</label>
          <p-inputSwitch inputId="active" formControlName="is_active" />
        </div>

        <div class="col-12 flex justify-content-end mt-2">
          <p-button type="submit" label="Save Settings" icon="pi pi-save" [loading]="saving" [disabled]="form.invalid" />
        </div>
      </form>
    </p-card>
  `
})
export class EmailSettingsComponent implements OnInit {
  private fb = inject(FormBuilder);
  private service = inject(SchoolSettingsService);
  private toast = inject(MessageService);

  loaded = false;
  saving = false;
  existing: EmailConfig | null = null;

  form = this.fb.group({
    smtp_host: ['', Validators.required],
    smtp_port: [587 as number, Validators.required],
    smtp_use_tls: [true],
    smtp_username: ['', Validators.required],
    smtp_password: ['', Validators.required], // relaxed to optional once a config exists
    from_email: ['', [Validators.required, Validators.email]],
    from_name: [''],
    is_active: [true]
  });

  ngOnInit(): void {
    this.service.getEmailConfig().subscribe({
      next: (res) => {
        this.existing = res.data ?? null;
        if (this.existing) {
          // Editing an existing config → password is optional (blank keeps it).
          this.form.get('smtp_password')?.clearValidators();
          this.form.get('smtp_password')?.updateValueAndValidity();
          this.form.patchValue({
            smtp_host: this.existing.smtp_host,
            smtp_port: this.existing.smtp_port,
            smtp_use_tls: this.existing.smtp_use_tls,
            smtp_username: this.existing.smtp_username,
            smtp_password: '',
            from_email: this.existing.from_email,
            from_name: this.existing.from_name ?? '',
            is_active: this.existing.is_active
          });
        }
        this.loaded = true;
      },
      error: () => {
        this.loaded = true;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load email settings' });
      }
    });
  }

  invalid(name: string): boolean {
    const c = this.form.get(name) as AbstractControl;
    return !!c && c.invalid && (c.dirty || c.touched);
  }

  onSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const v = this.form.getRawValue();
    const payload: EmailConfigPayload = {
      smtp_host: v.smtp_host!.trim(),
      smtp_port: v.smtp_port!,
      smtp_use_tls: !!v.smtp_use_tls,
      smtp_username: v.smtp_username!.trim(),
      from_email: v.from_email!.trim(),
      from_name: v.from_name?.trim() || null,
      is_active: !!v.is_active
    };
    // Only send the password when the admin actually typed one.
    if (v.smtp_password) payload.smtp_password = v.smtp_password;

    this.saving = true;
    this.service.saveEmailConfig(payload).subscribe({
      next: (res) => {
        this.saving = false;
        this.existing = res.data;
        this.form.get('smtp_password')?.clearValidators();
        this.form.get('smtp_password')?.updateValueAndValidity();
        this.form.patchValue({ smtp_password: '' });
        this.toast.add({ severity: 'success', summary: 'Saved', detail: 'Email settings updated' });
      },
      error: (err) => {
        this.saving = false;
        this.toast.add({
          severity: 'error',
          summary: 'Error',
          detail: err?.error?.message || 'Failed to save email settings'
        });
      }
    });
  }
}
