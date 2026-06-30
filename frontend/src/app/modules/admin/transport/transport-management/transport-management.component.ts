import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MessageService } from 'primeng/api';
import { TabViewModule } from 'primeng/tabview';
import { TableModule } from 'primeng/table';
import { DialogModule } from 'primeng/dialog';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { InputNumberModule } from 'primeng/inputnumber';
import { DropdownModule } from 'primeng/dropdown';
import { TagModule } from 'primeng/tag';
import { ToolbarModule } from 'primeng/toolbar';
import { ToastModule } from 'primeng/toast';
import { ProgressSpinnerModule } from 'primeng/progressspinner';

import {
  TransportService,
  TransportRoute,
  TransportVehicle,
  StudentTransportAssignment,
} from '../../../../core/services/transport.service';
import { StudentService } from '../../../../core/services/student.service';
import { ClassesService, AcademicYear } from '../../../../core/services/classes.service';

interface Option { label: string; value: number; }

@Component({
  selector: 'app-transport-management',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormsModule,
    TabViewModule,
    TableModule,
    DialogModule,
    ButtonModule,
    InputTextModule,
    InputNumberModule,
    DropdownModule,
    TagModule,
    ToolbarModule,
    ToastModule,
    ProgressSpinnerModule,
  ],
  providers: [MessageService],
  templateUrl: './transport-management.component.html',
})
export class TransportManagementComponent implements OnInit {
  private transport = inject(TransportService);
  private studentSvc = inject(StudentService);
  private classesSvc = inject(ClassesService);
  private fb = inject(FormBuilder);
  private toast = inject(MessageService);

  routes: TransportRoute[] = [];
  vehicles: TransportVehicle[] = [];
  assignments: StudentTransportAssignment[] = [];

  routeOptions: Option[] = [];
  studentOptions: Option[] = [];
  academicYearOptions: Option[] = [];

  loadingRoutes = false;
  loadingVehicles = false;
  loadingAssignments = false;
  saving = false;

  // ── Route dialog ──
  routeDialogVisible = false;
  routeEditId: number | null = null;
  routeForm: FormGroup = this.fb.group({
    name: ['', Validators.required],
    description: [''],
    stops: [''], // comma-separated
    fare: [null, [Validators.min(0)]],
    fare_frequency: ['monthly', Validators.required],
  });

  fareFrequencyOptions: { label: string; value: string }[] = [
    { label: 'Monthly', value: 'monthly' },
    { label: 'Quarterly', value: 'quarterly' },
    { label: 'Annual', value: 'annual' },
    { label: 'One Time', value: 'one_time' },
  ];

  // ── Vehicle dialog ──
  vehicleDialogVisible = false;
  vehicleEditId: number | null = null;
  vehicleForm: FormGroup = this.fb.group({
    registration_no: ['', Validators.required],
    capacity: [null, [Validators.required, Validators.min(1)]],
    driver_name: [''],
    driver_phone: [''],
    route_id: [null],
  });

  // ── Assignment dialog ──
  assignDialogVisible = false;
  assignmentRouteFilter: number | null = null;
  assignForm: FormGroup = this.fb.group({
    student_id: [null, Validators.required],
    route_id: [null, Validators.required],
    academic_year_id: [null, Validators.required],
    pickup_stop: [''],
    drop_stop: [''],
  });

  ngOnInit(): void {
    this.loadRoutes();
    this.loadVehicles();
    this.loadAssignments();
    this.loadStudentOptions();
    this.loadAcademicYearOptions();
  }

  // ── Loaders ──────────────────────────────────────────────────────────────
  loadRoutes(): void {
    this.loadingRoutes = true;
    this.transport.getRoutes().subscribe({
      next: (res) => {
        this.routes = res.data?.routes ?? [];
        this.routeOptions = this.routes.map(r => ({ label: r.name, value: r.id }));
        this.loadingRoutes = false;
      },
      error: () => { this.fail('Failed to load routes'); this.loadingRoutes = false; },
    });
  }

  loadVehicles(): void {
    this.loadingVehicles = true;
    this.transport.getVehicles().subscribe({
      next: (res) => { this.vehicles = res.data?.vehicles ?? []; this.loadingVehicles = false; },
      error: () => { this.fail('Failed to load vehicles'); this.loadingVehicles = false; },
    });
  }

  loadAssignments(): void {
    this.loadingAssignments = true;
    this.transport.getAssignments(this.assignmentRouteFilter ?? undefined).subscribe({
      next: (res) => { this.assignments = res.data?.assignments ?? []; this.loadingAssignments = false; },
      error: () => { this.fail('Failed to load assignments'); this.loadingAssignments = false; },
    });
  }

  loadStudentOptions(): void {
    this.studentSvc.getStudents(1, 200).subscribe({
      next: (res) => {
        const students = res.data?.students ?? [];
        this.studentOptions = students.map(s => ({
          label: `${s.first_name} ${s.last_name} (${s.admission_no})`,
          value: s.id,
        }));
      },
    });
  }

  loadAcademicYearOptions(): void {
    this.classesSvc.getAcademicYears().subscribe({
      next: (res) => {
        const years = res.data?.academic_years ?? [];
        this.academicYearOptions = years.map((y: AcademicYear) => ({ label: y.name, value: y.id }));
      },
    });
  }

  // ── Routes CRUD ────────────────────────────────────────────────────────────
  openRouteDialog(route?: TransportRoute): void {
    this.routeEditId = route ? route.id : null;
    this.routeForm.reset({
      name: route?.name ?? '',
      description: route?.description ?? '',
      stops: route?.stops?.join(', ') ?? '',
      fare: route?.fare ?? null,
      fare_frequency: route?.fare_frequency ?? 'monthly',
    });
    this.routeDialogVisible = true;
  }

  saveRoute(): void {
    if (this.routeForm.invalid) return;
    this.saving = true;
    const raw = this.routeForm.value;
    const payload = {
      name: raw.name,
      description: raw.description || null,
      stops: this.parseStops(raw.stops),
      fare: raw.fare ?? null,
      fare_frequency: raw.fare_frequency ?? 'monthly',
    };
    const req$ = this.routeEditId !== null
      ? this.transport.updateRoute(this.routeEditId, payload)
      : this.transport.createRoute(payload);
    req$.subscribe({
      next: () => {
        this.saving = false;
        this.routeDialogVisible = false;
        this.ok(this.routeEditId !== null ? 'Route updated' : 'Route created');
        this.loadRoutes();
      },
      error: () => { this.saving = false; this.fail('Failed to save route'); },
    });
  }

  deleteRoute(route: TransportRoute): void {
    if (!window.confirm(`Delete route "${route.name}"?`)) return;
    this.transport.deleteRoute(route.id).subscribe({
      next: () => { this.ok('Route deleted'); this.loadRoutes(); this.loadVehicles(); },
      error: () => this.fail('Failed to delete route'),
    });
  }

  // ── Vehicles CRUD ──────────────────────────────────────────────────────────
  openVehicleDialog(vehicle?: TransportVehicle): void {
    this.vehicleEditId = vehicle ? vehicle.id : null;
    this.vehicleForm.reset({
      registration_no: vehicle?.registration_no ?? '',
      capacity: vehicle?.capacity ?? null,
      driver_name: vehicle?.driver_name ?? '',
      driver_phone: vehicle?.driver_phone ?? '',
      route_id: vehicle?.route_id ?? null,
    });
    this.vehicleDialogVisible = true;
  }

  saveVehicle(): void {
    if (this.vehicleForm.invalid) return;
    this.saving = true;
    const raw = this.vehicleForm.value;
    const payload = {
      registration_no: raw.registration_no,
      capacity: raw.capacity,
      driver_name: raw.driver_name || null,
      driver_phone: raw.driver_phone || null,
      route_id: raw.route_id ?? null,
    };
    const req$ = this.vehicleEditId !== null
      ? this.transport.updateVehicle(this.vehicleEditId, payload)
      : this.transport.createVehicle(payload);
    req$.subscribe({
      next: () => {
        this.saving = false;
        this.vehicleDialogVisible = false;
        this.ok(this.vehicleEditId !== null ? 'Vehicle updated' : 'Vehicle created');
        this.loadVehicles();
      },
      error: (err) => {
        this.saving = false;
        this.fail(err?.error?.message ?? 'Failed to save vehicle');
      },
    });
  }

  // ── Assignments ──────────────────────────────────────────────────────────
  openAssignDialog(): void {
    this.assignForm.reset();
    this.assignDialogVisible = true;
  }

  saveAssignment(): void {
    if (this.assignForm.invalid) return;
    this.saving = true;
    const raw = this.assignForm.value;
    this.transport.assignStudent({
      student_id: raw.student_id,
      route_id: raw.route_id,
      academic_year_id: raw.academic_year_id,
      pickup_stop: raw.pickup_stop || null,
      drop_stop: raw.drop_stop || null,
    }).subscribe({
      next: () => {
        this.saving = false;
        this.assignDialogVisible = false;
        this.ok('Student assigned to transport');
        this.loadAssignments();
      },
      error: (err) => {
        this.saving = false;
        this.fail(err?.error?.message ?? 'Failed to assign student');
      },
    });
  }

  unassign(a: StudentTransportAssignment): void {
    if (!window.confirm(`Remove ${a.student_name} from ${a.route_name}?`)) return;
    this.transport.unassign(a.id).subscribe({
      next: () => { this.ok('Student unassigned'); this.loadAssignments(); },
      error: () => this.fail('Failed to unassign'),
    });
  }

  onAssignmentFilterChange(): void {
    this.loadAssignments();
  }

  // ── Helpers ────────────────────────────────────────────────────────────────
  fareFrequencyLabel(value: string | null | undefined): string {
    const opt = this.fareFrequencyOptions.find(o => o.value === value);
    return opt ? opt.label : (value ?? '');
  }

  private parseStops(value: string): string[] {
    if (!value) return [];
    return value.split(',').map(s => s.trim()).filter(s => s.length > 0);
  }

  private ok(detail: string): void {
    this.toast.add({ severity: 'success', summary: 'Success', detail });
  }

  private fail(detail: string): void {
    this.toast.add({ severity: 'error', summary: 'Error', detail });
  }
}
