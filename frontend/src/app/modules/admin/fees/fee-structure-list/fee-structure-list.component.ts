import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { MessageService } from 'primeng/api';
import { TableModule } from 'primeng/table';
import { DialogModule } from 'primeng/dialog';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { InputNumberModule } from 'primeng/inputnumber';
import { DropdownModule } from 'primeng/dropdown';
import { SelectButtonModule } from 'primeng/selectbutton';
import { CheckboxModule } from 'primeng/checkbox';
import { TagModule } from 'primeng/tag';
import { ToolbarModule } from 'primeng/toolbar';
import { ToastModule } from 'primeng/toast';
import { CalendarModule } from 'primeng/calendar';
import { ProgressSpinnerModule } from 'primeng/progressspinner';

import { FeeStructureService, FeeStructure } from '../../../../core/services/fee-structure.service';
import { ClassesService } from '../../../../core/services/classes.service';
import { TransportService, TransportRoute } from '../../../../core/services/transport.service';

@Component({
  selector: 'app-fee-structure-list',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    TableModule,
    DialogModule,
    ButtonModule,
    InputTextModule,
    InputNumberModule,
    DropdownModule,
    SelectButtonModule,
    CheckboxModule,
    TagModule,
    ToolbarModule,
    ToastModule,
    CalendarModule,
    ProgressSpinnerModule,
  ],
  providers: [MessageService],
  templateUrl: './fee-structure-list.component.html',
})
export class FeeStructureListComponent implements OnInit {
  private feeStructureService = inject(FeeStructureService);
  private classesService = inject(ClassesService);
  private transportService = inject(TransportService);
  private fb = inject(FormBuilder);
  private toast = inject(MessageService);
  private router = inject(Router);

  feeStructures: FeeStructure[] = [];
  loading = false;
  dialogVisible = false;
  saving = false;
  isEdit = false;
  editingId: number | null = null;
  generatingId: number | null = null;

  frequencyOptions = [
    { label: 'Monthly', value: 'monthly' },
    { label: 'Quarterly', value: 'quarterly' },
    { label: 'Annual', value: 'annual' },
    { label: 'One Time', value: 'one_time' },
  ];

  applicabilityOptions = [
    { label: 'Mandatory', value: 'mandatory' },
    { label: 'Optional', value: 'optional' },
  ];

  sourceKindOptions = [
    { label: 'Flat amount', value: 'flat' },
    { label: 'Transport', value: 'transport' },
  ];

  classOptions: { label: string; value: number }[] = [];
  academicYearOptions: { label: string; value: number }[] = [];
  routeOptions: { label: string; value: number }[] = [];
  loadingClasses = false;
  loadingYears = false;
  loadingRoutes = false;

  // route-id → fare lookup for the table display
  private routeNameById = new Map<number, string>();

  // id → display-name lookups for the table
  private classNameById = new Map<number, string>();
  private yearNameById = new Map<number, string>();

  form: FormGroup = this.fb.group({
    fee_type: ['', Validators.required],
    class_id: [null, Validators.required],
    academic_year_id: [null, Validators.required],
    amount: [null, [Validators.required, Validators.min(0)]],
    due_date: [null],
    is_recurring: [false],
    frequency: [null, Validators.required],
    // SMS-066
    applicability: ['mandatory', Validators.required],
    source_kind: ['flat', Validators.required],
    transport_route_id: [null],
  });

  /** True when the chosen frequency means the fee recurs each period. */
  get isRecurringFreq(): boolean {
    const f = this.form.get('frequency')?.value;
    return !!f && f !== 'one_time';
  }

  /** True when this structure is backed by a transport route (per-student fare). */
  get isTransport(): boolean {
    return this.form.get('source_kind')?.value === 'transport';
  }

  /** True for an optional + flat structure, which bills nobody in v1. */
  get isOptionalFlat(): boolean {
    return this.form.get('source_kind')?.value === 'flat'
      && this.form.get('applicability')?.value === 'optional';
  }

  ngOnInit(): void {
    this.loadFeeStructures();
    this.loadClasses();
    this.loadAcademicYears();
    this.loadRoutes();

    // Due date is required only for one-time fees; recurring fees derive a due
    // date per month. Keep is_recurring in sync with the chosen frequency.
    this.form.get('frequency')!.valueChanges.subscribe((freq) => {
      this.applyFrequencyRules(freq);
    });

    // Switching source_kind toggles the amount vs transport-route fields and
    // mirrors the backend rule (transport ⇒ optional).
    this.form.get('source_kind')!.valueChanges.subscribe((kind) => {
      this.applySourceKindRules(kind);
    });
  }

  /**
   * Mirror the backend rule in the UI:
   *  - transport ⇒ amount is ignored (hidden, not required); applicability forced
   *    to 'optional'; transport_route_id selectable.
   *  - flat ⇒ amount required as before; transport_route_id cleared.
   */
  private applySourceKindRules(kind: string | null): void {
    const amount = this.form.get('amount')!;
    const applicability = this.form.get('applicability')!;
    const routeId = this.form.get('transport_route_id')!;

    if (kind === 'transport') {
      amount.clearValidators();
      amount.setValue(null, { emitEvent: false });
      applicability.setValue('optional', { emitEvent: false });
      applicability.disable({ emitEvent: false });
    } else {
      amount.setValidators([Validators.required, Validators.min(0)]);
      applicability.enable({ emitEvent: false });
      routeId.setValue(null, { emitEvent: false });
    }
    amount.updateValueAndValidity({ emitEvent: false });
  }

  private applyFrequencyRules(freq: string | null): void {
    const dueDate = this.form.get('due_date')!;
    if (freq && freq !== 'one_time') {
      this.form.get('is_recurring')!.setValue(true, { emitEvent: false });
      dueDate.clearValidators();
    } else {
      this.form.get('is_recurring')!.setValue(false, { emitEvent: false });
      dueDate.setValidators([Validators.required]);
    }
    dueDate.updateValueAndValidity({ emitEvent: false });
  }

  private loadClasses(): void {
    this.loadingClasses = true;
    this.classesService.getClasses(1, 100).subscribe({
      next: (res) => {
        const classes = res.data?.classes ?? [];
        this.classOptions = classes.map((c) => ({
          label: `${c.name} (Grade ${c.grade_level})`,
          value: c.id,
        }));
        this.classNameById = new Map(classes.map((c) => [c.id, c.name]));
        this.loadingClasses = false;
      },
      error: () => { this.loadingClasses = false; },
    });
  }

  private loadAcademicYears(): void {
    this.loadingYears = true;
    this.classesService.getAcademicYears().subscribe({
      next: (res) => {
        const years = res.data?.academic_years ?? [];
        this.academicYearOptions = years.map((y) => ({
          label: y.is_current ? `${y.name} (current)` : y.name,
          value: y.id,
        }));
        this.yearNameById = new Map(years.map((y) => [y.id, y.name]));
        this.loadingYears = false;
      },
      error: () => { this.loadingYears = false; },
    });
  }

  private loadRoutes(): void {
    this.loadingRoutes = true;
    this.transportService.getRoutes().subscribe({
      next: (res) => {
        const routes = res.data?.routes ?? [];
        this.routeOptions = routes.map((r: TransportRoute) => ({
          label: r.fare != null
            ? `${r.name} (${r.fare} / ${this.getFrequencyLabel(r.fare_frequency)})`
            : `${r.name} (no fare set)`,
          value: r.id,
        }));
        this.routeNameById = new Map(routes.map((r: TransportRoute) => [r.id, r.name]));
        this.loadingRoutes = false;
      },
      error: () => { this.loadingRoutes = false; },
    });
  }

  getClassName(id: number): string {
    return this.classNameById.get(id) ?? `#${id}`;
  }

  getRouteName(id: number | null): string {
    if (id == null) return '—';
    return this.routeNameById.get(id) ?? `#${id}`;
  }

  getYearName(id: number): string {
    return this.yearNameById.get(id) ?? `#${id}`;
  }

  loadFeeStructures(): void {
    this.loading = true;
    this.feeStructureService.getFeeStructures().subscribe({
      next: (res) => {
        this.feeStructures = res.data?.fee_structures ?? res.data ?? [];
        this.loading = false;
      },
      error: () => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load fee structures' });
        this.loading = false;
      },
    });
  }

  openDialog(fs?: FeeStructure): void {
    this.form.get('applicability')!.enable({ emitEvent: false });
    this.form.reset({ is_recurring: false, applicability: 'mandatory', source_kind: 'flat', transport_route_id: null });
    this.isEdit = false;
    this.editingId = null;

    if (fs) {
      this.isEdit = true;
      this.editingId = fs.id;
      this.form.patchValue({
        fee_type: fs.fee_type,
        class_id: fs.class_id,
        academic_year_id: fs.academic_year_id,
        amount: fs.amount,
        due_date: fs.due_date ? new Date(fs.due_date) : null,
        is_recurring: fs.is_recurring,
        frequency: fs.frequency,
        applicability: fs.applicability ?? 'mandatory',
        source_kind: fs.source_kind ?? 'flat',
        transport_route_id: fs.transport_route_id ?? null,
      });
    }

    // Apply due-date validation rules for the current frequency, and the
    // amount/applicability rules for the current source_kind.
    this.applyFrequencyRules(this.form.get('frequency')!.value);
    this.applySourceKindRules(this.form.get('source_kind')!.value);
    this.dialogVisible = true;
  }

  closeDialog(): void {
    this.dialogVisible = false;
    this.form.get('applicability')!.enable({ emitEvent: false });
    this.form.reset({ is_recurring: false, applicability: 'mandatory', source_kind: 'flat', transport_route_id: null });
  }

  saveFeeStructure(): void {
    if (this.form.invalid) return;

    this.saving = true;
    // getRawValue() so the disabled `applicability` control (transport mode) is included.
    const raw = this.form.getRawValue();
    const isTransport = raw.source_kind === 'transport';
    const payload: Partial<FeeStructure> = {
      fee_type: raw.fee_type,
      class_id: raw.class_id,
      academic_year_id: raw.academic_year_id,
      // Transport structures ignore the flat amount (backend stores 0).
      amount: isTransport ? 0 : raw.amount,
      due_date: raw.due_date ? this.formatDate(raw.due_date) : null,
      is_recurring: raw.is_recurring ?? false,
      frequency: raw.frequency,
      applicability: isTransport ? 'optional' : raw.applicability,
      source_kind: raw.source_kind,
      transport_route_id: isTransport ? (raw.transport_route_id ?? null) : null,
    };

    const request$ = this.isEdit && this.editingId !== null
      ? this.feeStructureService.updateFeeStructure(this.editingId, payload)
      : this.feeStructureService.createFeeStructure(payload);

    request$.subscribe({
      next: () => {
        this.saving = false;
        this.dialogVisible = false;
        this.toast.add({
          severity: 'success',
          summary: 'Success',
          detail: this.isEdit ? 'Fee structure updated successfully' : 'Fee structure created successfully',
        });
        this.loadFeeStructures();
      },
      error: () => {
        this.saving = false;
        this.toast.add({
          severity: 'error',
          summary: 'Error',
          detail: this.isEdit ? 'Failed to update fee structure' : 'Failed to create fee structure',
        });
      },
    });
  }

  generateFees(fs: FeeStructure): void {
    const className = this.getClassName(fs.class_id);
    const recurringNote = fs.frequency && fs.frequency !== 'one_time'
      ? `\nThis is a ${fs.frequency} fee: one record per period will be created from each student's admission month up to the current month.`
      : '';
    if (!window.confirm(
      `Generate "${fs.fee_type}" fee records for all active students in ${className}?` +
      recurringNote +
      `\nExisting records are skipped.`
    )) return;

    this.generatingId = fs.id;
    this.feeStructureService.generateFeeRecords(fs.id).subscribe({
      next: (res) => {
        this.generatingId = null;
        const d = res?.data ?? {};
        const generated = d.generated ?? 0;
        const skipped = d.skipped ?? 0;
        const skippedNoFare = d.skipped_no_fare ?? 0;
        const skippedNoOptin = d.skipped_no_optin ?? 0;
        const total = d.total_students ?? (generated + skipped);

        // Optional + flat (v1) has no opt-in source → bills nobody. Surface that
        // explicitly rather than a generic "0 generated".
        if (fs.source_kind === 'flat' && fs.applicability === 'optional' && generated === 0) {
          this.toast.add({
            severity: 'warn',
            summary: 'No One Billed',
            detail: 'This is an Optional + Flat fee — in v1 it has no opt-in list, so generate bills nobody. '
              + 'Link it to a transport route to bill opted-in students.',
            life: 8000,
          });
          return;
        }

        const parts: string[] = [];
        parts.push(`Generated ${generated} record(s)`);
        if (skipped > 0) parts.push(`skipped ${skipped} already up-to-date`);
        if (skippedNoFare > 0) {
          parts.push(`skipped ${skippedNoFare} student(s) whose route has no fare set`);
        }
        if (skippedNoOptin > 0) {
          parts.push(`${skippedNoOptin} student(s) had not opted in`);
        }
        parts.push(`across ${total} billed student(s)`);

        this.toast.add({
          severity: generated > 0 ? 'success' : (skippedNoFare > 0 || skippedNoOptin > 0 ? 'warn' : 'info'),
          summary: 'Fees Generated',
          detail: total === 0
            ? (fs.source_kind === 'transport'
                ? `No students are opted in to transport for this route/year, so nobody was billed.`
                : `No active students found in ${className}. Enroll students first.`)
            : `${parts.join(', ')}.`,
          life: 8000,
        });
      },
      error: (err) => {
        this.generatingId = null;
        this.toast.add({
          severity: 'error',
          summary: 'Error',
          detail: err?.error?.message ?? 'Failed to generate fee records',
        });
      },
    });
  }

  deleteFeeStructure(fs: FeeStructure): void {
    if (!window.confirm(`Delete fee structure "${fs.fee_type}"? This cannot be undone.`)) return;

    this.feeStructureService.deleteFeeStructure(fs.id).subscribe({
      next: () => {
        this.toast.add({ severity: 'success', summary: 'Deleted', detail: 'Fee structure deleted' });
        this.loadFeeStructures();
      },
      error: () => {
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to delete fee structure' });
      },
    });
  }

  getFrequencyLabel(freq: string): string {
    const opt = this.frequencyOptions.find(o => o.value === freq);
    return opt ? opt.label : freq;
  }

  getStatusSeverity(isActive: boolean): 'success' | 'danger' {
    return isActive ? 'success' : 'danger';
  }

  navigateTo(path: string): void {
    this.router.navigate([path]);
  }

  private formatDate(date: Date): string {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }
}
