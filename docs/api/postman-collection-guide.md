# SMS API — Postman / Testing Guide
**Author:** @qa-engineer | **Date:** 2026-06-06

---

## Environment Variables (Postman)

Set up a Postman Environment with these variables:

| Variable | Value (Dev) | Description |
|----------|------------|-------------|
| `base_url` | `http://localhost:5000/api/v1` | API base URL |
| `access_token` | *(set by login script)* | JWT access token |
| `refresh_token` | *(set by login script)* | JWT refresh token |
| `admin_email` | `admin@school.com` | Admin test account |
| `admin_password` | `Admin@1234` | Admin test password |

---

## Pre-request Script (Auto-login)

Add this to the Collection's Pre-request Script to auto-refresh tokens:

```javascript
// Postman pre-request script — auto-refresh access token
const accessToken = pm.environment.get('access_token');
const refreshToken = pm.environment.get('refresh_token');

if (!accessToken && refreshToken) {
    pm.sendRequest({
        url: pm.environment.get('base_url') + '/auth/refresh',
        method: 'POST',
        header: { 'Authorization': 'Bearer ' + refreshToken }
    }, (err, res) => {
        if (!err && res.code === 200) {
            pm.environment.set('access_token', res.json().data.access_token);
        }
    });
}
```

---

## Auth Header

All protected requests use:
```
Authorization: Bearer {{access_token}}
```

---

## Test Sequence (Golden Path)

Run these requests in order for end-to-end validation:

### 1. Login as Admin
```
POST {{base_url}}/auth/login
Body: { "email": "{{admin_email}}", "password": "{{admin_password}}" }
Test: pm.environment.set('access_token', pm.response.json().data.access_token)
```

### 2. Create Teacher User
```
POST {{base_url}}/users
Body: { "email": "teacher1@school.com", "password": "Teacher@123",
        "role": "teacher", "first_name": "Priya", "last_name": "Sharma" }
Test: pm.environment.set('teacher_id', pm.response.json().data.user.id)
```

### 3. Create Student User
```
POST {{base_url}}/users
Body: { "email": "alice@school.com", "password": "Student@123",
        "role": "student", "first_name": "Alice", "last_name": "Johnson" }
```

### 4. Create Parent User
```
POST {{base_url}}/users
Body: { "email": "parent1@school.com", "password": "Parent@123",
        "role": "parent", "first_name": "Robert", "last_name": "Johnson" }
Test: pm.environment.set('parent_user_id', pm.response.json().data.user.id)
```

### 5. Enroll Student
```
POST {{base_url}}/students
Body: { "admission_no": "ADM2024001", "first_name": "Alice",
        "last_name": "Johnson", "date_of_birth": "2010-05-15",
        "gender": "Female", "admission_date": "2024-01-15", "user_id": 3 }
Test: pm.environment.set('student_id', pm.response.json().data.id)
```

### 6. Link Parent to Student
```
POST {{base_url}}/students/{{student_id}}/parents
Body: { "parent_id": 1, "is_primary_contact": true }
```

### 7. Login as Parent
```
POST {{base_url}}/auth/login
Body: { "email": "parent1@school.com", "password": "Parent@123" }
Test: pm.environment.set('parent_token', pm.response.json().data.access_token)
```

### 8. Parent: View Dashboard
```
GET {{base_url}}/parent-portal/dashboard
Header: Authorization: Bearer {{parent_token}}
Test: pm.expect(pm.response.json().data.children.length).to.be.greaterThan(0)
```

### 9. Parent: Submit Leave
```
POST {{base_url}}/leave-applications
Header: Authorization: Bearer {{parent_token}}
Body: { "student_id": {{student_id}}, "from_date": "2026-06-10",
        "to_date": "2026-06-10", "leave_type": "sick", "reason": "Child has fever" }
Test: pm.expect(pm.response.json().data.status).to.eql('pending')
```

### 10. Admin: Approve Leave
```
PUT {{base_url}}/leave-applications/1/review
Body: { "status": "approved", "remarks": "Approved" }
Test: pm.expect(pm.response.json().data.status).to.eql('approved')
```

---

## Common Error Scenarios to Test

| Scenario | Expected |
|----------|----------|
| Login with wrong password | 401 |
| Login 6 times in 1 min | 429 |
| Access `/admin` route as teacher | 403 |
| Access `/parent-portal/children/999/attendance` as parent (not your child) | 403 |
| Create student with duplicate admission_no | 409 |
| Submit leave for a past date | 422 |
| Upload a .exe file as student document | 400 |
| Mark attendance for a section you don't teach (as teacher) | 403 |
| Enter marks > max_marks | 422 |
| Expired access token | 401 |

---

## curl Examples

```bash
# Login
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@school.com","password":"Admin@1234"}'

# Get students (with token)
curl http://localhost:5000/api/v1/students \
  -H "Authorization: Bearer eyJ..."

# Mark attendance
curl -X POST http://localhost:5000/api/v1/attendance/mark \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "section_id": 1,
    "date": "2026-06-06",
    "records": [
      {"student_id": 1, "status": "present"},
      {"student_id": 2, "status": "absent"}
    ]
  }'

# Parent portal dashboard
curl http://localhost:5000/api/v1/parent-portal/dashboard \
  -H "Authorization: Bearer <parent_jwt>"
```
