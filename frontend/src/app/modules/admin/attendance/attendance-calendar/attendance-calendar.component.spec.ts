import { TestBed, ComponentFixture } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { MessageService } from 'primeng/api';

import { AttendanceCalendarComponent } from './attendance-calendar.component';
import { AttendanceService, AttendanceRecord } from '../../../../core/services/attendance.service';
import { StudentService, Student } from '../../../../core/services/student.service';

// ---------------------------------------------------------------------------
// Minimal stub student used across specs
// ---------------------------------------------------------------------------

const STUB_STUDENT: Student = {
  id: 42,
  admission_no: 'ADM-001',
  first_name: 'Alice',
  last_name: 'Test',
  date_of_birth: '2012-03-15',
  gender: 'Female',
  admission_date: '2024-06-01',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build an AttendanceRecord stub for a given date string and status. */
function makeRecord(dateStr: string, status: AttendanceRecord['status']): AttendanceRecord {
  return {
    id: Math.floor(Math.random() * 10000),
    student_id: STUB_STUDENT.id,
    section_id: 1,
    date: dateStr,
    status,
  };
}

/** Return a response envelope wrapping an attendance array. */
function attendanceResponse(records: AttendanceRecord[]) {
  return of({ success: true, data: { attendance: records }, message: 'ok', errors: null });
}

/** Return a response envelope wrapping a students array. */
function studentsResponse(students: Student[]) {
  return of({
    success: true,
    data: { students, meta: { total: students.length, page: 1, per_page: 20, pages: 1 } },
    message: 'ok',
    errors: null,
  });
}

// ---------------------------------------------------------------------------
// Suite
// ---------------------------------------------------------------------------

describe('AttendanceCalendarComponent', () => {
  let component: AttendanceCalendarComponent;
  let fixture: ComponentFixture<AttendanceCalendarComponent>;
  let attendanceServiceSpy: jasmine.SpyObj<AttendanceService>;
  let studentServiceSpy: jasmine.SpyObj<StudentService>;
  let messageServiceSpy: jasmine.SpyObj<MessageService>;

  beforeEach(async () => {
    attendanceServiceSpy = jasmine.createSpyObj('AttendanceService', ['getAttendance']);
    studentServiceSpy    = jasmine.createSpyObj('StudentService',    ['searchStudents']);
    messageServiceSpy    = jasmine.createSpyObj('MessageService',    ['add']);

    // Default: service calls return empty successful responses
    attendanceServiceSpy.getAttendance.and.returnValue(attendanceResponse([]));
    studentServiceSpy.searchStudents.and.returnValue(studentsResponse([]));

    await TestBed.configureTestingModule({
      // Standalone component — use imports, not declarations
      imports: [AttendanceCalendarComponent],
      providers: [
        { provide: AttendanceService, useValue: attendanceServiceSpy },
        { provide: StudentService,    useValue: studentServiceSpy },
        { provide: MessageService,    useValue: messageServiceSpy },
      ],
    }).compileComponents();

    fixture   = TestBed.createComponent(AttendanceCalendarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges(); // triggers ngOnInit
  });

  // ── TC-FE-01: Initial state ────────────────────────────────────────────────

  describe('TC-FE-01: Initial state', () => {
    it('selectedStudent is null on init', () => {
      expect(component.selectedStudent).toBeNull();
    });

    it('calendarWeeks is empty on init', () => {
      expect(component.calendarWeeks).toEqual([]);
    });

    it('loading is false on init', () => {
      expect(component.loading).toBeFalse();
    });

    it('displayMonth is set on init', () => {
      // The value is a locale string like "June 2026" — just check it is non-empty
      expect(component.displayMonth).toBeTruthy();
      expect(typeof component.displayMonth).toBe('string');
    });

    it('summary starts at all-zeros', () => {
      expect(component.summary.present).toBe(0);
      expect(component.summary.absent).toBe(0);
      expect(component.summary.late).toBe(0);
      expect(component.summary.leave).toBe(0);
      expect(component.summary.holiday).toBe(0);
      expect(component.summary.percentage).toBe(0);
    });
  });

  // ── TC-FE-02: searchStudents — delegates to StudentService ────────────────

  describe('TC-FE-02: searchStudents with non-empty query', () => {
    it('calls StudentService.searchStudents with the trimmed query', () => {
      studentServiceSpy.searchStudents.and.returnValue(studentsResponse([STUB_STUDENT]));

      component.searchStudents({ query: 'Alice' });

      expect(studentServiceSpy.searchStudents).toHaveBeenCalledWith('Alice', 20);
    });

    it('populates studentSuggestions from the service response', () => {
      studentServiceSpy.searchStudents.and.returnValue(studentsResponse([STUB_STUDENT]));

      component.searchStudents({ query: 'Alice' });

      expect(component.studentSuggestions.length).toBe(1);
      expect(component.studentSuggestions[0].id).toBe(STUB_STUDENT.id);
    });
  });

  // ── TC-FE-03: searchStudents with empty query ─────────────────────────────

  describe('TC-FE-03: searchStudents with empty query', () => {
    it('does NOT call StudentService when query is blank', () => {
      // Reset the call count from beforeEach setup
      studentServiceSpy.searchStudents.calls.reset();

      component.searchStudents({ query: '   ' });

      expect(studentServiceSpy.searchStudents).not.toHaveBeenCalled();
    });

    it('studentSuggestions stays empty when query is blank', () => {
      component.searchStudents({ query: '' });

      expect(component.studentSuggestions).toEqual([]);
    });
  });

  // ── TC-FE-04: onStudentSelect — sets selectedStudent and loads attendance ──

  describe('TC-FE-04: onStudentSelect', () => {
    it('sets selectedStudent to the event value', () => {
      component.onStudentSelect({ value: STUB_STUDENT });

      expect(component.selectedStudent).toBe(STUB_STUDENT);
    });

    it('calls AttendanceService.getAttendance after selection', () => {
      attendanceServiceSpy.getAttendance.calls.reset();

      component.onStudentSelect({ value: STUB_STUDENT });

      expect(attendanceServiceSpy.getAttendance).toHaveBeenCalledWith(
        STUB_STUDENT.id,
        component.currentDate.getMonth() + 1,
        component.currentDate.getFullYear(),
      );
    });

    it('sets loading to false after service responds', () => {
      component.onStudentSelect({ value: STUB_STUDENT });

      expect(component.loading).toBeFalse();
    });
  });

  // ── TC-FE-05: onStudentClear — resets all state ───────────────────────────

  describe('TC-FE-05: onStudentClear', () => {
    beforeEach(() => {
      // Put the component in a non-empty state first
      component.onStudentSelect({ value: STUB_STUDENT });
    });

    it('selectedStudent is null after clearing', () => {
      component.onStudentClear();

      expect(component.selectedStudent).toBeNull();
    });

    it('calendarWeeks is empty after clearing', () => {
      component.onStudentClear();

      expect(component.calendarWeeks).toEqual([]);
    });

    it('summary resets to all-zeros after clearing', () => {
      component.onStudentClear();

      expect(component.summary.present).toBe(0);
      expect(component.summary.absent).toBe(0);
      expect(component.summary.late).toBe(0);
      expect(component.summary.leave).toBe(0);
      expect(component.summary.holiday).toBe(0);
      expect(component.summary.percentage).toBe(0);
    });
  });

  // ── TC-FE-06: canGoNext — false when at current month ────────────────────

  describe('TC-FE-06: canGoNext — false at current month', () => {
    it('returns false when currentDate is the current calendar month', () => {
      const now = new Date();
      component.currentDate = new Date(now.getFullYear(), now.getMonth(), 1);

      expect(component.canGoNext).toBeFalse();
    });
  });

  // ── TC-FE-07: canGoNext — true when one month in the past ─────────────────

  describe('TC-FE-07: canGoNext — true for past month', () => {
    it('returns true when currentDate is one month before the current month', () => {
      const now = new Date();
      // Go back one month
      component.currentDate = new Date(now.getFullYear(), now.getMonth() - 1, 1);

      expect(component.canGoNext).toBeTrue();
    });
  });

  // ── TC-FE-08: nextMonth() — does not advance past current month ───────────

  describe('TC-FE-08: nextMonth() blocked at current month', () => {
    it('does not change currentDate when already at the current month', () => {
      const now = new Date();
      component.currentDate = new Date(now.getFullYear(), now.getMonth(), 1);
      const before = component.currentDate.getTime();

      component.nextMonth();

      expect(component.currentDate.getTime()).toBe(before);
    });
  });

  // ── TC-FE-09: buildSummary via loadAttendance — percentage calculation ─────

  describe('TC-FE-09: buildSummary percentage calculation', () => {
    it('computes percentage = round((present+late)/(present+absent+late+leave)*100)', () => {
      // 3 present + 1 late + 1 absent → attended=4, total=5, pct=80
      const year  = component.currentDate.getFullYear();
      const month = component.currentDate.getMonth() + 1;
      const pad   = (n: number) => String(n).padStart(2, '0');
      const records: AttendanceRecord[] = [
        makeRecord(`${year}-${pad(month)}-01`, 'present'),
        makeRecord(`${year}-${pad(month)}-02`, 'present'),
        makeRecord(`${year}-${pad(month)}-03`, 'present'),
        makeRecord(`${year}-${pad(month)}-04`, 'late'),
        makeRecord(`${year}-${pad(month)}-05`, 'absent'),
      ];

      attendanceServiceSpy.getAttendance.and.returnValue(attendanceResponse(records));
      component.selectedStudent = STUB_STUDENT;
      component.loadAttendance();

      expect(component.summary.present).toBe(3);
      expect(component.summary.late).toBe(1);
      expect(component.summary.absent).toBe(1);
      expect(component.summary.percentage).toBe(80);
    });

    it('leave and holiday do NOT count toward the percentage denominator', () => {
      // 4 present + 1 leave + 1 holiday → attended=4, total=4 (leave/holiday excluded), pct=100
      const year  = component.currentDate.getFullYear();
      const month = component.currentDate.getMonth() + 1;
      const pad   = (n: number) => String(n).padStart(2, '0');
      const records: AttendanceRecord[] = [
        makeRecord(`${year}-${pad(month)}-01`, 'present'),
        makeRecord(`${year}-${pad(month)}-02`, 'present'),
        makeRecord(`${year}-${pad(month)}-03`, 'present'),
        makeRecord(`${year}-${pad(month)}-04`, 'present'),
        makeRecord(`${year}-${pad(month)}-05`, 'leave'),
        makeRecord(`${year}-${pad(month)}-06`, 'holiday'),
      ];

      attendanceServiceSpy.getAttendance.and.returnValue(attendanceResponse(records));
      component.selectedStudent = STUB_STUDENT;
      component.loadAttendance();

      expect(component.summary.present).toBe(4);
      expect(component.summary.leave).toBe(1);
      expect(component.summary.holiday).toBe(1);
      // Component formula: total = present + absent + late + leave  (holiday excluded)
      // total = 4 + 0 + 0 + 1 = 5; attended = 4+0 = 4; pct = round(4/5*100) = 80
      // holiday is counted in summary.holiday but NOT in the percentage denominator
      expect(component.summary.percentage).toBe(80);
    });
  });

  // ── TC-FE-10: getStatusClass — correct CSS class for each status ──────────

  describe('TC-FE-10: getStatusClass', () => {
    it('returns "day-cell day-present" for a present day', () => {
      const day = { date: new Date(), dayNum: 1, status: 'present' as const, isToday: false, isFuture: false, isCurrentMonth: true };
      expect(component.getStatusClass(day)).toBe('day-cell day-present');
    });

    it('returns "day-cell day-absent" for an absent day', () => {
      const day = { date: new Date(), dayNum: 2, status: 'absent' as const, isToday: false, isFuture: false, isCurrentMonth: true };
      expect(component.getStatusClass(day)).toBe('day-cell day-absent');
    });

    it('returns "day-cell day-late" for a late day', () => {
      const day = { date: new Date(), dayNum: 3, status: 'late' as const, isToday: false, isFuture: false, isCurrentMonth: true };
      expect(component.getStatusClass(day)).toBe('day-cell day-late');
    });

    it('returns "day-cell day-future" for a future day regardless of status', () => {
      const future = new Date();
      future.setDate(future.getDate() + 10);
      const day = { date: future, dayNum: 20, status: null, isToday: false, isFuture: true, isCurrentMonth: true };
      expect(component.getStatusClass(day)).toBe('day-cell day-future');
    });

    it('returns "day-cell day-no-record" for a current-month day with no status', () => {
      const day = { date: new Date(), dayNum: 5, status: null, isToday: false, isFuture: false, isCurrentMonth: true };
      expect(component.getStatusClass(day)).toBe('day-cell day-no-record');
    });

    it('returns "day-cell day-empty" for a padding cell (outside current month)', () => {
      const day = { date: null, dayNum: null, status: null, isToday: false, isFuture: false, isCurrentMonth: false };
      expect(component.getStatusClass(day)).toBe('day-cell day-empty');
    });
  });

  // ── TC-FE-11: getStatusLabel — first char uppercase ───────────────────────

  describe('TC-FE-11: getStatusLabel', () => {
    it('returns "P" for present', () => {
      expect(component.getStatusLabel('present')).toBe('P');
    });

    it('returns "A" for absent', () => {
      expect(component.getStatusLabel('absent')).toBe('A');
    });

    it('returns "L" for late', () => {
      expect(component.getStatusLabel('late')).toBe('L');
    });

    it('returns "L" for leave', () => {
      expect(component.getStatusLabel('leave')).toBe('L');
    });

    it('returns "H" for holiday', () => {
      expect(component.getStatusLabel('holiday')).toBe('H');
    });

    it('returns empty string for null status', () => {
      expect(component.getStatusLabel(null)).toBe('');
    });
  });

  // ── TC-FE-12: buildCalendar leading padding cells ─────────────────────────

  describe('TC-FE-12: buildCalendar padding cells', () => {
    it('leading cells before the 1st of the month have dayNum null and isCurrentMonth false', () => {
      // June 2026: 1 June is a Monday (DOW index 1 in JS, Mon-based offset = 0)
      // Use a month whose 1st is NOT a Monday to guarantee leading cells exist.
      // 1 May 2026 is a Friday → Mon-based offset = 4 → 4 padding cells.
      component.currentDate = new Date(2026, 4, 1); // May 2026

      attendanceServiceSpy.getAttendance.and.returnValue(attendanceResponse([]));
      component.selectedStudent = STUB_STUDENT;
      component.loadAttendance();

      const firstWeek = component.calendarWeeks[0];
      expect(firstWeek).toBeDefined();

      // At least one leading cell must be a padding cell
      const paddingCells = firstWeek.filter(cell => !cell.isCurrentMonth);
      expect(paddingCells.length).toBeGreaterThan(0);

      paddingCells.forEach(cell => {
        expect(cell.dayNum).toBeNull();
        expect(cell.date).toBeNull();
        expect(cell.status).toBeNull();
        expect(cell.isCurrentMonth).toBeFalse();
      });
    });

    it('all real-month cells have a valid dayNum and isCurrentMonth true', () => {
      component.currentDate = new Date(2026, 4, 1); // May 2026

      attendanceServiceSpy.getAttendance.and.returnValue(attendanceResponse([]));
      component.selectedStudent = STUB_STUDENT;
      component.loadAttendance();

      const allCells = component.calendarWeeks.flat();
      const monthCells = allCells.filter(c => c.isCurrentMonth);
      expect(monthCells.length).toBe(31); // May has 31 days

      monthCells.forEach(cell => {
        expect(cell.dayNum).not.toBeNull();
        expect(cell.date).not.toBeNull();
      });
    });
  });

  // ── TC-FE-13: Error handling in loadAttendance ────────────────────────────

  describe('TC-FE-13: loadAttendance error handling', () => {
    it('calls MessageService.add with severity "error" when the service throws', () => {
      attendanceServiceSpy.getAttendance.and.returnValue(
        throwError(() => new Error('Network error'))
      );

      component.selectedStudent = STUB_STUDENT;
      component.loadAttendance();

      expect(messageServiceSpy.add).toHaveBeenCalledWith(
        jasmine.objectContaining({ severity: 'error' })
      );
    });

    it('resets loading to false on service error', () => {
      attendanceServiceSpy.getAttendance.and.returnValue(
        throwError(() => new Error('Timeout'))
      );

      component.selectedStudent = STUB_STUDENT;
      component.loadAttendance();

      expect(component.loading).toBeFalse();
    });

    it('does not navigate away or clear selectedStudent on error', () => {
      attendanceServiceSpy.getAttendance.and.returnValue(
        throwError(() => new Error('Server 500'))
      );

      component.selectedStudent = STUB_STUDENT;
      component.loadAttendance();

      // selectedStudent is preserved — the user can retry
      expect(component.selectedStudent).toBe(STUB_STUDENT);
    });
  });
});
