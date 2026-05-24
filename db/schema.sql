-- ISPPS Database Schema
-- Intelligent Student Performance Prediction System
--
-- Apply on a PostgreSQL 14+ database:
--   psql "$DATABASE_URL" -f db/schema.sql
--   psql "$DATABASE_URL" -f db/seed.sql

-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- ============================================================
-- SCHOOLS
-- ============================================================
create table schools (
  id         uuid primary key default uuid_generate_v4(),
  name       text not null,
  address    text,
  created_at timestamptz not null default now()
);

-- ============================================================
-- USERS (auth-linked)
-- ============================================================
create table users (
  id         uuid primary key default uuid_generate_v4(),
  email      text unique not null,
  full_name  text not null,
  role       text not null check (role in ('admin','lecturer','student')),
  avatar_url text,
  password_hash text not null,
  school_id  uuid references schools(id) on delete set null,
  created_at timestamptz not null default now()
);

create index idx_users_email on users(email);
create index idx_users_role on users(role);

-- ============================================================
-- ACADEMIC YEARS
-- ============================================================
create table academic_years (
  id         uuid primary key default uuid_generate_v4(),
  school_id  uuid not null references schools(id) on delete cascade,
  label      text not null,
  start_date date not null,
  end_date   date not null,
  is_active  boolean not null default false
);

create index idx_academic_years_school on academic_years(school_id);

-- ============================================================
-- COURSES
-- ============================================================
create table courses (
  id               uuid primary key default uuid_generate_v4(),
  school_id        uuid not null references schools(id) on delete cascade,
  lecturer_id       uuid references users(id) on delete set null,
  academic_year_id uuid not null references academic_years(id) on delete cascade,
  name             text not null,
  subject          text not null,
  grade_level      text,
  credit_hours     int not null default 3
);

create index idx_courses_school on courses(school_id);
create index idx_courses_lecturer on courses(lecturer_id);

-- ============================================================
-- STUDENTS
-- ============================================================
create table students (
  id              uuid primary key default uuid_generate_v4(),
  user_id         uuid unique references users(id) on delete cascade,
  school_id       uuid not null references schools(id) on delete cascade,
  student_number  text unique not null,
  date_of_birth   date,
  gender          text check (gender in ('male','female','other')),
  guardian_name   text,
  guardian_email  text,
  enrolled_at     timestamptz not null default now()
);

create index idx_students_school on students(school_id);
create index idx_students_user on students(user_id);

-- ============================================================
-- ENROLLMENTS
-- ============================================================
create table enrollments (
  id          uuid primary key default uuid_generate_v4(),
  student_id  uuid not null references students(id) on delete cascade,
  course_id   uuid not null references courses(id) on delete cascade,
  enrolled_at timestamptz not null default now(),
  status      text not null default 'active' check (status in ('active','dropped','completed')),
  unique(student_id, course_id)
);

create index idx_enrollments_student on enrollments(student_id);
create index idx_enrollments_course on enrollments(course_id);

-- ============================================================
-- GRADES
-- ============================================================
create table grades (
  id              uuid primary key default uuid_generate_v4(),
  enrollment_id   uuid not null references enrollments(id) on delete cascade,
  assessment_type text not null check (assessment_type in ('quiz','midterm','final','assignment','project','lab')),
  title           text not null,
  score           float not null,
  max_score       float not null,
  weight          float not null default 1.0,
  assessed_on     date not null default current_date,
  recorded_by     uuid references users(id) on delete set null
);

create index idx_grades_enrollment on grades(enrollment_id);

-- ============================================================
-- ATTENDANCE
-- ============================================================
create table attendance (
  id            uuid primary key default uuid_generate_v4(),
  enrollment_id uuid not null references enrollments(id) on delete cascade,
  date          date not null,
  status        text not null check (status in ('present','absent','late','excused')),
  note          text,
  recorded_by   uuid references users(id) on delete set null,
  unique(enrollment_id, date)
);

create index idx_attendance_enrollment on attendance(enrollment_id);
create index idx_attendance_date on attendance(date);

-- ============================================================
-- PREDICTIONS
-- ============================================================
create table predictions (
  id               uuid primary key default uuid_generate_v4(),
  student_id       uuid not null references students(id) on delete cascade,
  course_id        uuid references courses(id) on delete set null,
  predicted_grade  float not null,
  pass_probability float not null,
  risk_level       text not null check (risk_level in ('low','medium','high','critical')),
  factors          jsonb not null default '[]'::jsonb,
  recommendations  jsonb not null default '[]'::jsonb,
  ai_summary       text,
  generated_at     timestamptz not null default now()
);

create index idx_predictions_student on predictions(student_id);
create index idx_predictions_course on predictions(course_id);
create index idx_predictions_risk on predictions(risk_level);

-- ============================================================
-- AI INSIGHTS
-- ============================================================
create table ai_insights (
  id           uuid primary key default uuid_generate_v4(),
  student_id   uuid not null references students(id) on delete cascade,
  insight_type text not null check (insight_type in ('performance','behavior','recommendation','warning','trend')),
  content      text not null,
  metadata     jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now()
);

create index idx_ai_insights_student on ai_insights(student_id);
create index idx_ai_insights_type on ai_insights(insight_type);

-- ============================================================
-- NOTIFICATIONS
-- ============================================================
create table notifications (
  id           uuid primary key default uuid_generate_v4(),
  recipient_id uuid not null references users(id) on delete cascade,
  type         text not null check (type in ('prediction','warning','grade','attendance','system')),
  title        text not null,
  body         text not null,
  is_read      boolean not null default false,
  created_at   timestamptz not null default now()
);

create index idx_notifications_recipient on notifications(recipient_id);
create index idx_notifications_unread on notifications(recipient_id) where is_read = false;

-- Authorization is enforced in the FastAPI layer via app/deps.py
-- (role + school scoping). The backend connects as a single Postgres
-- user, so row-level security is intentionally not used here.
