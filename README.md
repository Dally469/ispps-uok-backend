# ISPPS API Documentation

## Overview

This backend is a FastAPI service for the Intelligent Student Performance Prediction System.

- App title: `ISPPS API`
- Version: `1.0.0`
- Verified local health endpoint: `GET /api/health`
- Verified local base URL during setup: `http://127.0.0.1:8001`

If you run the server on another host or port, replace the base URL accordingly.

## Built-in FastAPI Docs

FastAPI already exposes interactive API docs:

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

Examples:

- `http://127.0.0.1:8001/docs`
- `http://127.0.0.1:8001/redoc`
- `http://127.0.0.1:8001/openapi.json`

## Authentication

The API uses JWT auth and also writes the token to an `auth_token` HTTP-only cookie.

Supported auth sources:

- `Authorization: Bearer <token>` header
- `auth_token` cookie

### Login

`POST /api/auth/login`

Request body:

```json
{
  "email": "admin@uok.lk",
  "password": "password123"
}
```

Response shape:

```json
{
  "token": "<jwt>",
  "user": {
    "id": "c0000000-0000-0000-0000-000000000001",
    "email": "admin@uok.lk",
    "full_name": "System Administrator",
    "role": "admin",
    "avatar_url": null,
    "school_id": "a0000000-0000-0000-0000-000000000001",
    "created_at": "2026-01-01T00:00:00Z"
  }
}
```

### Session

- `GET /api/auth/session`: returns the authenticated user
- `POST /api/auth/logout`: clears the auth cookie

## Seed Login Accounts

These accounts are available in the seeded local database.

- Admin: `admin@uok.lk` / `password123`
- Teacher: `drsilva@uok.lk` / `password123`
- Teacher: `drperera@uok.lk` / `password123`
- Teacher: `drfernando@uok.lk` / `password123`
- Student: `ashan@student.uok.lk` / `password123`
- Parent: `mbandara@gmail.com` / `password123`

## Common Roles

- `admin`
- `teacher`
- `student`
- `parent`

Role restrictions are enforced across the main data endpoints.

## Data Visibility Rules

- `admin`: can view records for their school
- `teacher`: can view their assigned courses and the students enrolled in those courses
- `student`: can view only their own student record, enrollments, predictions, attendance, and reports
- `parent`: can view only student records linked through `parent_links`

Additional scoping behavior:

- Endpoints that accept `school_id` now reject cross-school access with `403`
- Teacher analytics, reports, and AI endpoints are trimmed to the teacher's own courses
- Student and parent requests for unrelated student IDs return `404`

## Endpoints

### Health

- `GET /api/health`

Response:

```json
{
  "status": "ok"
}
```

### Auth

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/session`

### Students

- `GET /api/students`
  - Auth required
  - Query params:
    - `search` optional string
    - `gender` optional string
    - `course_id` optional UUID
    - `risk_level` optional string
    - `has_predictions` optional boolean
    - `limit` optional integer, default `50`
    - `offset` optional integer, default `0`
  - Returns students scoped to `auth.schoolId`

- `POST /api/students`
  - Roles: `admin`, `teacher`
  - Request body:

```json
{
  "user_id": null,
  "school_id": "a0000000-0000-0000-0000-000000000001",
  "student_number": "UOK-2024-009",
  "date_of_birth": "2003-02-12",
  "gender": "female",
  "guardian_name": "Guardian Name",
  "guardian_email": "guardian@example.com"
}
```

- `GET /api/students/{student_id}`
  - Auth required
  - Returns:
    - student profile
    - linked user
    - enrollments with course, teacher, grades, attendance
    - recent predictions
    - recent AI insights

- `PUT /api/students/{student_id}`
  - Roles: `admin`, `teacher`
  - Partial request body:

```json
{
  "guardian_name": "Updated Guardian",
  "guardian_email": "updated@example.com"
}
```

- `DELETE /api/students/{student_id}`
  - Role: `admin`

### Attendance

- `GET /api/attendance`
  - Auth required
  - Query params:
    - `enrollment_id` optional UUID
    - `student_id` optional UUID
    - `course_id` optional UUID
    - `school_id` optional UUID
    - `status` optional string
    - `recorded_by` optional UUID
    - `date_from` optional date string
    - `date_to` optional date string
    - `limit` optional integer, default `100`
    - `offset` optional integer, default `0`

- `POST /api/attendance`
  - Roles: `admin`, `teacher`

```json
{
  "enrollment_id": "bb000000-0000-0000-0000-000000000001",
  "date": "2026-01-20",
  "status": "present",
  "note": "On time"
}
```

- `POST /api/attendance/bulk`
  - Roles: `admin`, `teacher`
  - Upserts by unique pair `(enrollment_id, date)`

```json
{
  "course_id": "aa000000-0000-0000-0000-000000000001",
  "date": "2026-01-20",
  "records": [
    {
      "enrollment_id": "bb000000-0000-0000-0000-000000000001",
      "status": "present",
      "note": ""
    },
    {
      "enrollment_id": "bb000000-0000-0000-0000-000000000003",
      "status": "late",
      "note": "Arrived after quiz started"
    }
  ]
}
```

### Courses

- `GET /api/courses`
  - Auth required
  - Query params:
    - `school_id` optional UUID
    - `subject` optional string
    - `teacher_id` optional UUID
    - `academic_year_id` optional UUID
    - `grade_level` optional string
    - `is_active_year` optional boolean
    - `search` optional string
    - `limit` optional integer, default `100`
    - `offset` optional integer, default `0`
  - Defaults to authenticated user's school when `school_id` is omitted

- `POST /api/courses`
  - Role: `admin`

```json
{
  "school_id": "a0000000-0000-0000-0000-000000000001",
  "teacher_id": "c0000000-0000-0000-0000-000000000002",
  "academic_year_id": "b0000000-0000-0000-0000-000000000001",
  "name": "Machine Learning Fundamentals",
  "subject": "Computer Science",
  "grade_level": "Year 3",
  "credit_hours": 3
}
```

### Predictions

- `GET /api/predictions`
  - Auth required
  - Query params:
    - `student_id` optional UUID
    - `course_id` optional UUID
    - `school_id` optional UUID
    - `risk_level` optional one of `low`, `medium`, `high`, `critical`
    - `search` optional string
    - `min_predicted_grade` optional number
    - `max_predicted_grade` optional number
    - `generated_from` optional datetime
    - `generated_to` optional datetime
    - `limit` optional integer, default `50`
    - `offset` optional integer, default `0`
  - Defaults to authenticated user's school when `school_id` is omitted

- `POST /api/predictions`
  - Auth required

```json
{
  "student_id": "f0000000-0000-0000-0000-000000000001",
  "course_id": "aa000000-0000-0000-0000-000000000001",
  "predicted_grade": 78,
  "pass_probability": 0.84,
  "risk_level": "low",
  "factors": [
    {
      "name": "Attendance",
      "score": 92,
      "weight": 0.3,
      "impact": "positive"
    }
  ],
  "recommendations": [
    "Keep current revision pace",
    "Review recursion questions weekly"
  ],
  "ai_summary": "Student is projected to pass comfortably."
}
```

### Analytics

- `GET /api/analytics/summary`
  - Auth required
  - Query params:
    - `school_id` optional UUID
    - `course_id` optional UUID
    - `subject` optional string
    - `risk_level` optional string
  - Uses authenticated user `schoolId` if omitted
  - Returns:
    - total students
    - total courses
    - average GPA
    - at-risk count
    - attendance rate
    - risk distribution
    - grade distribution
    - department performance
    - recent predictions

### AI / Claude

- `POST /api/claude/chat`
  - Auth required
  - Returns Server-Sent Events (`text/event-stream`)

```json
{
  "message": "How is Ashan performing this semester?",
  "student_id": "f0000000-0000-0000-0000-000000000001",
  "history": [
    {
      "role": "user",
      "content": "Give me a quick summary"
    }
  ]
}
```

- `POST /api/claude/insights`
  - Auth required

```json
{
  "student_id": "f0000000-0000-0000-0000-000000000001"
}
```

- `POST /api/claude/predict`
  - Auth required

```json
{
  "student_id": "f0000000-0000-0000-0000-000000000001",
  "course_id": "aa000000-0000-0000-0000-000000000001"
}
```

- `POST /api/claude/recommend`
  - Auth required

```json
{
  "student_id": "f0000000-0000-0000-0000-000000000001"
}
```

- `POST /api/claude/risk`
  - Roles: `admin`, `teacher`
  - Query params:
    - `school_id` optional UUID
  - Returns school-level risk warnings and optional AI summary

### Admin

- `GET /api/admin/users`
  - Role: `admin`
  - Query params:
    - `search` optional string
    - `role` optional string
    - `school_id` optional UUID
    - `limit` optional integer, default `100`
    - `offset` optional integer, default `0`
  - Returns user list ordered by latest created

### Reports

- `GET /api/reports/export`
  - Auth required
  - Query params:
    - `school_id` required UUID
    - `format` optional string, default `csv`
    - `student_id` optional UUID
    - `course_id` optional UUID
    - `subject` optional string
    - `assessment_type` optional string
    - `date_from` optional date string
    - `date_to` optional date string
  - Supported formats:
    - `csv`: file download
    - any other value: JSON payload

Example:

- `/api/reports/export?school_id=a0000000-0000-0000-0000-000000000001&format=csv`

### Import

- `POST /api/import/students`
  - Role: `admin`
  - Body expects raw CSV content as a string

```json
{
  "csv_data": "student_number,full_name,email,school_id,date_of_birth,gender,guardian_name,guardian_email\nUOK-2024-010,Jane Doe,jane@example.com,a0000000-0000-0000-0000-000000000001,2003-01-01,female,Parent Doe,parent@example.com"
}
```

Response:

```json
{
  "imported": 1,
  "errors": []
}
```

## Example Authenticated Curl Flow

### 1. Log in and capture the token

```bash
curl -X POST http://127.0.0.1:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@uok.lk","password":"password123"}'
```

### 2. Call a protected endpoint

```bash
curl http://127.0.0.1:8001/api/students \
  -H "Authorization: Bearer <token>"
```

## Notes

- CORS currently allows `http://localhost:3000`.
- Auth cookies are `HttpOnly` and use `SameSite=Lax`.
- AI endpoints depend on the Anthropic client configuration in the backend environment.
- The most complete live contract remains `/openapi.json` when the server is running.# ispps-uok-backend
