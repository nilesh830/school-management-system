"""
Generic Excel (.xlsx) generation helper for report exports (SMS-060).

Pure-Python via openpyxl — no system libraries required. The single public
function build_xlsx() takes a sheet title, a list of column headers, and a list
of row value-lists, and returns the workbook as raw xlsx bytes (in a BytesIO).

Reusable across all report exporters; contains no business logic.
"""

from datetime import date, datetime
from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment


# Header styling — dark fill + white bold text to match the PDF table headers.
_HEADER_FONT = Font(bold=True, color="FFFFFF")
_HEADER_FILL = PatternFill(start_color="333333", end_color="333333", fill_type="solid")
_HEADER_ALIGN = Alignment(horizontal="left", vertical="center")


def build_xlsx(sheet_title: str, headers: list, rows: list) -> bytes:
    """
    Build an .xlsx workbook with a single sheet and return its bytes.

    Args:
        sheet_title: Worksheet name (truncated to 31 chars — Excel's limit).
        headers:     List of column header strings (the first row).
        rows:        List of row value-lists; each inner list is one row.

    Returns:
        The workbook serialized to xlsx as bytes.
    """
    wb = Workbook()
    ws = wb.active
    # Excel caps sheet titles at 31 characters.
    ws.title = (sheet_title or "Report")[:31]

    # Header row
    ws.append(list(headers))
    for col_idx, _ in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = _HEADER_ALIGN

    # Data rows
    for row in rows:
        ws.append(list(row))

    # Best-effort column auto-width based on the longest value per column.
    for col_idx, header in enumerate(headers, start=1):
        max_len = len(str(header))
        for row in rows:
            if col_idx - 1 < len(row):
                value = row[col_idx - 1]
                max_len = max(max_len, len(str(value)) if value is not None else 0)
        # +2 padding, capped so a stray long value doesn't blow out the sheet.
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = min(max_len + 2, 60)

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Bulk student import (SMS — bulk registration)
# ---------------------------------------------------------------------------

# Column order for the downloadable template AND the header row parse_xlsx
# expects. `key` maps to the StudentBulkRowSchema field names. No password
# column — logins get an auto-generated temp password server-side.
STUDENT_IMPORT_COLUMNS = [
    {"key": "first_name", "label": "First Name*", "example": "Alice"},
    {"key": "last_name", "label": "Last Name*", "example": "Johnson"},
    {"key": "date_of_birth", "label": "Date of Birth* (YYYY-MM-DD)", "example": "2012-05-14"},
    {"key": "gender", "label": "Gender* (Male/Female/Other)", "example": "Female"},
    {"key": "admission_date", "label": "Admission Date* (YYYY-MM-DD)", "example": "2024-06-01"},
    {"key": "admission_no", "label": "Admission No*", "example": "ADM2024001"},
    {"key": "blood_group", "label": "Blood Group", "example": "O+"},
    {"key": "address", "label": "Address", "example": "12 Oak Street"},
    {"key": "phone", "label": "Phone", "example": "+1 555 0100"},
    {"key": "section_id", "label": "Section ID", "example": ""},
    {"key": "email", "label": "Email (for login)", "example": "alice@example.com"},
]

_INT_KEYS = {"section_id"}


def _style_header_row(ws, ncols):
    for col_idx in range(1, ncols + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = _HEADER_ALIGN


def _autosize(ws, headers, rows):
    for col_idx, header in enumerate(headers, start=1):
        max_len = len(str(header))
        for row in rows:
            if col_idx - 1 < len(row):
                value = row[col_idx - 1]
                max_len = max(max_len, len(str(value)) if value is not None else 0)
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = min(max_len + 2, 60)


def build_student_import_template(sections: list | None = None) -> bytes:
    """Return an .xlsx template for bulk student import.

    Sheet 1 ("Students"): the header row + one example row to fill in.
    Sheet 2 ("Sections"): a reference list of the school's active sections with
    their IDs, so an admin knows which number to put in the "Section ID" column.
    The reference is omitted when no sections are supplied.

    ``sections`` is a list of dicts: {id, label, class_name, capacity}.
    """
    headers = [c["label"] for c in STUDENT_IMPORT_COLUMNS]
    example = [c["example"] for c in STUDENT_IMPORT_COLUMNS]

    wb = Workbook()
    ws = wb.active
    ws.title = "Students"
    ws.append(headers)
    ws.append(example)
    _style_header_row(ws, len(headers))
    _autosize(ws, headers, [example])

    if sections:
        ref = wb.create_sheet("Sections")
        ref_headers = ["Section ID", "Section", "Class", "Capacity"]
        ref.append(ref_headers)
        ref_rows = [
            [s.get("id"), s.get("label"), s.get("class_name"), s.get("capacity")]
            for s in sections
        ]
        for r in ref_rows:
            ref.append(r)
        _style_header_row(ref, len(ref_headers))
        _autosize(ref, ref_headers, ref_rows)

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _normalize_cell(key: str, value):
    """Coerce an openpyxl cell value into what StudentBulkRowSchema expects."""
    if value is None:
        return None
    # Excel dates come back as datetime/date — schema Date fields want ISO strings.
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, float):
        # Integer-valued floats (e.g. a section id typed as 3) → int.
        if value.is_integer():
            return int(value)
        return value
    return value


def parse_xlsx(file_or_bytes) -> list:
    """Parse an uploaded .xlsx into a list of row dicts.

    Row 1 is treated as the header row and matched positionally against
    STUDENT_IMPORT_COLUMNS (extra trailing columns are ignored). Fully blank
    rows are skipped. Each returned dict carries a 1-based ``_row`` number
    (matching the spreadsheet, header = row 1) for per-row error reporting.

    Raises ValueError on an unreadable / empty workbook.
    """
    try:
        wb = load_workbook(filename=BytesIO(file_or_bytes.read() if hasattr(file_or_bytes, "read") else file_or_bytes), read_only=True, data_only=True)
    except Exception as exc:
        raise ValueError(f"Could not read the Excel file: {exc}")

    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)

    try:
        header = next(rows_iter)
    except StopIteration:
        raise ValueError("The Excel file is empty.")

    keys = [c["key"] for c in STUDENT_IMPORT_COLUMNS]
    parsed = []
    row_number = 1  # header was row 1
    for raw in rows_iter:
        row_number += 1
        if raw is None or all(cell is None or (isinstance(cell, str) and not cell.strip()) for cell in raw):
            continue  # skip blank row
        record = {"_row": row_number}
        for idx, key in enumerate(keys):
            cell = raw[idx] if idx < len(raw) else None
            value = _normalize_cell(key, cell)
            if value is not None:
                record[key] = value
        parsed.append(record)

    wb.close()
    return parsed
