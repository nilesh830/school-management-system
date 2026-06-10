import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ConfirmationService, MessageService } from 'primeng/api';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { ButtonModule } from 'primeng/button';
import { DropdownModule } from 'primeng/dropdown';
import { TagModule } from 'primeng/tag';
import { ToastModule } from 'primeng/toast';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { ToolbarModule } from 'primeng/toolbar';
import { SkeletonModule } from 'primeng/skeleton';
import { SchoolsService, School } from '../../../../core/services/schools.service';

const MONTH_NAMES = ['', 'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'];

const MONTH_OPTIONS = MONTH_NAMES.slice(1).map((label, i) => ({ label, value: i + 1 }));

@Component({
  selector: 'app-school-detail',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
    CardModule,
    InputTextModule,
    ButtonModule,
    DropdownModule,
    TagModule,
    ToastModule,
    ConfirmDialogModule,
    ToolbarModule,
    SkeletonModule
  ],
  providers: [MessageService, ConfirmationService],
  templateUrl: './school-detail.component.html'
})
export class SchoolDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private fb = inject(FormBuilder);
  private schoolsService = inject(SchoolsService);
  private toast = inject(MessageService);
  private confirm = inject(ConfirmationService);

  school = signal<School | null>(null);
  loading = signal(false);
  saving = signal(false);
  toggling = signal(false);
  editMode = signal(false);

  readonly monthOptions = MONTH_OPTIONS;

  editForm = this.fb.group({
    name: ['', Validators.required],
    address: [''],
    phone: [''],
    email: ['', Validators.email],
    logo_url: [''],
    academic_year_start_month: [null as number | null]
  });

  get schoolId(): number {
    return Number(this.route.snapshot.paramMap.get('id'));
  }

  get monthName(): string {
    const m = this.school()?.academic_year_start_month;
    return m ? MONTH_NAMES[m] : '—';
  }

  ngOnInit(): void {
    this.loadSchool();
  }

  loadSchool(): void {
    this.loading.set(true);
    this.schoolsService.getSchool(this.schoolId).subscribe({
      next: (res) => {
        this.school.set(res.data);
        this.loading.set(false);
      },
      error: () => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load school' });
        this.loading.set(false);
      }
    });
  }

  enterEditMode(): void {
    const s = this.school();
    if (!s) return;
    this.editForm.patchValue({
      name: s.name,
      address: s.address ?? '',
      phone: s.phone ?? '',
      email: s.email ?? '',
      logo_url: s.logo_url ?? '',
      academic_year_start_month: s.academic_year_start_month ?? null
    });
    this.editMode.set(true);
  }

  cancelEdit(): void {
    this.editMode.set(false);
    this.editForm.reset();
  }

  saveChanges(): void {
    if (this.editForm.invalid) {
      this.editForm.markAllAsTouched();
      return;
    }

    this.saving.set(true);
    const val = this.editForm.value;
    const payload: Partial<School> = {
      name: val.name!,
      address: val.address || null,
      phone: val.phone || null,
      email: val.email || null,
      logo_url: val.logo_url || null,
      academic_year_start_month: val.academic_year_start_month ?? null
    };

    this.schoolsService.updateSchool(this.schoolId, payload).subscribe({
      next: (res) => {
        this.school.set(res.data);
        this.saving.set(false);
        this.editMode.set(false);
        this.toast.add({ severity: 'success', summary: 'Saved', detail: 'School updated successfully' });
      },
      error: (err) => {
        this.saving.set(false);
        const detail = err.error?.message || 'Failed to update school';
        this.toast.add({ severity: 'error', summary: 'Error', detail });
      }
    });
  }

  toggleActive(): void {
    const s = this.school();
    if (!s) return;

    if (s.is_active) {
      this.confirm.confirm({
        header: 'Deactivate School',
        message: `Are you sure you want to deactivate "${s.name}"? Users will not be able to log in until it is reactivated.`,
        icon: 'pi pi-exclamation-triangle',
        acceptLabel: 'Deactivate',
        rejectLabel: 'Cancel',
        acceptButtonStyleClass: 'p-button-danger',
        accept: () => this._doToggle()
      });
    } else {
      this._doToggle();
    }
  }

  private _doToggle(): void {
    const s = this.school();
    if (!s) return;
    this.toggling.set(true);

    this.schoolsService.updateSchool(this.schoolId, { is_active: !s.is_active }).subscribe({
      next: (res) => {
        this.school.set(res.data);
        this.toggling.set(false);
        const action = res.data.is_active ? 'activated' : 'deactivated';
        this.toast.add({ severity: 'success', summary: 'Updated', detail: `School ${action} successfully` });
      },
      error: (err) => {
        this.toggling.set(false);
        const detail = err.error?.message || 'Failed to update school status';
        this.toast.add({ severity: 'error', summary: 'Error', detail });
      }
    });
  }
}
