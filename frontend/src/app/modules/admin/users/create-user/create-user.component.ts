import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { PasswordModule } from 'primeng/password';
import { DropdownModule } from 'primeng/dropdown';
import { ToastModule } from 'primeng/toast';
import { MessageService } from 'primeng/api';
import { HttpClient } from '@angular/common/http';
import { UsersService } from '../../../../core/services/users.service';

@Component({
  selector: 'app-create-user',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, RouterLink,
    CardModule, ButtonModule, InputTextModule, PasswordModule,
    DropdownModule, ToastModule
  ],
  providers: [MessageService],
  templateUrl: './create-user.component.html'
})
export class CreateUserComponent implements OnInit {
  private fb = inject(FormBuilder);
  private http = inject(HttpClient);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private usersService = inject(UsersService);
  private toast = inject(MessageService);

  isEdit = false;
  userId: number | null = null;

  // Create User only offers roles it can fully provision here:
  //  • admin  → just a login account
  //  • parent → login + Parent profile (created inline below)
  // Students are created via "Enroll New Student" and teachers via "Add Teacher",
  // because those create their own profile records (a bare login is useless).
  roles = [
    { label: 'Administrator', value: 'admin' },
    { label: 'Parent / Guardian', value: 'parent' }
  ];

  relationshipTypes = [
    { label: 'Father', value: 'Father' },
    { label: 'Mother', value: 'Mother' },
    { label: 'Guardian', value: 'Guardian' }
  ];

  form = this.fb.group({
    first_name: ['', Validators.required],
    last_name: ['', Validators.required],
    email: ['', [Validators.required, Validators.email]],
    role: ['', Validators.required],
    password: ['', [Validators.required, Validators.minLength(8)]],
    // Parent-only fields — validators toggled dynamically on role change
    relationship_type: [''],
    phone_primary: [''],
    phone_secondary: [''],
    occupation: [''],
    address: ['']
  });

  loading = false;

  constructor() {
    // The backend requires relationship_type + phone_primary when role=parent.
    // Apply those validators only while Parent is selected so other roles aren't
    // blocked by empty parent fields. (Edit mode hides the parent fields and only
    // updates the user account, so it never applies these validators.)
    this.form.controls.role.valueChanges.subscribe((role) => {
      const rel = this.form.controls.relationship_type;
      const phone = this.form.controls.phone_primary;
      if (role === 'parent' && !this.isEdit) {
        rel.setValidators(Validators.required);
        phone.setValidators([Validators.required, Validators.pattern(/^[0-9+\-\s]{7,20}$/)]);
      } else {
        rel.clearValidators();
        phone.clearValidators();
      }
      rel.updateValueAndValidity();
      phone.updateValueAndValidity();
    });
  }

  ngOnInit(): void {
    const idParam = this.route.snapshot.paramMap.get('id');
    if (!idParam) {
      return; // create mode
    }
    this.isEdit = true;
    this.userId = Number(idParam);

    // In edit mode password is optional (blank = keep current) and the role is
    // locked — changing a role would orphan the linked Parent/Student records.
    this.f.password.clearValidators();
    this.f.password.setValidators(Validators.minLength(8));
    this.f.password.updateValueAndValidity();
    this.f.role.disable();

    this.usersService.getUser(this.userId).subscribe({
      next: (res) => {
        const u = res.data;
        this.form.patchValue({
          first_name: u.first_name,
          last_name: u.last_name,
          email: u.email,
          role: u.role
        });
      },
      error: () => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load user.' });
        this.router.navigate(['/admin/users']);
      }
    });
  }

  get f() { return this.form.controls; }

  generatePassword(): void {
    const upper = 'ABCDEFGHJKMNPQRSTUVWXYZ';
    const lower = 'abcdefghjkmnpqrstuvwxyz';
    const digits = '23456789';
    const special = '!@#$';
    const all = upper + lower + digits + special;
    const rand = (s: string) => s[Math.floor(Math.random() * s.length)];
    // Guarantee at least one of each required character type
    const pwd = [
      rand(upper), rand(lower), rand(digits), rand(special),
      ...Array.from({ length: 8 }, () => rand(all))
    ].sort(() => Math.random() - 0.5).join('');
    this.f.password.setValue(pwd);
  }

  onSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.loading = true;
    if (this.isEdit) {
      this.updateUser();
    } else {
      this.createUser();
    }
  }

  private createUser(): void {
    const v = this.form.value;
    const payload: Record<string, unknown> = {
      first_name: v.first_name,
      last_name: v.last_name,
      email: v.email,
      role: v.role,
      password: v.password
    };
    if (v.role === 'parent') {
      payload['relationship_type'] = v.relationship_type;
      payload['phone_primary'] = v.phone_primary;
      if (v.phone_secondary) payload['phone_secondary'] = v.phone_secondary;
      if (v.occupation) payload['occupation'] = v.occupation;
      if (v.address) payload['address'] = v.address;
    }

    this.http.post('/api/v1/users', payload).subscribe({
      next: () => {
        this.loading = false;
        this.toast.add({
          severity: 'success',
          summary: 'User Created',
          detail: 'The user account has been created successfully.'
        });
        setTimeout(() => this.router.navigate(['/admin/users']), 1200);
      },
      error: (err) => {
        this.loading = false;
        this.toast.add({
          severity: 'error',
          summary: 'Error',
          detail: err.error?.message || 'Failed to create user. Please try again.'
        });
      }
    });
  }

  private updateUser(): void {
    const v = this.form.getRawValue();
    const payload: Record<string, unknown> = {
      first_name: v.first_name,
      last_name: v.last_name,
      email: v.email
    };
    if (v.password) payload['password'] = v.password;

    this.usersService.updateUser(this.userId!, payload).subscribe({
      next: () => {
        this.loading = false;
        this.toast.add({
          severity: 'success',
          summary: 'User Updated',
          detail: 'The user account has been updated successfully.'
        });
        setTimeout(() => this.router.navigate(['/admin/users']), 1200);
      },
      error: (err) => {
        this.loading = false;
        this.toast.add({
          severity: 'error',
          summary: 'Error',
          detail: err.error?.message || 'Failed to update user. Please try again.'
        });
      }
    });
  }
}
