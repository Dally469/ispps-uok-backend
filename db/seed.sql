-- ISPPS Seed Data
-- Run after creating the schema

-- ============================================================
-- School
-- ============================================================
insert into schools (id, name, address) values
  ('a0000000-0000-0000-0000-000000000001', 'University of Kelaniya', 'Dalugama, Kelaniya, Sri Lanka');

-- ============================================================
-- Academic Year
-- ============================================================
insert into academic_years (id, school_id, label, start_date, end_date, is_active) values
  ('b0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001', '2025/2026', '2025-09-01', '2026-06-30', true),
  ('b0000000-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000001', '2024/2025', '2024-09-01', '2025-06-30', false);

-- ============================================================
-- Users (password is "password123" hashed with bcrypt)
-- ============================================================
insert into users (id, email, full_name, role, password_hash, school_id) values
  ('c0000000-0000-0000-0000-000000000001', 'admin@uok.lk', 'System Administrator', 'admin', '$2b$10$jmX9QF7SmhpTc7fqc1lpR.KpcR0FpvRFH6bTLdtOv4SJHRGng/PeW', 'a0000000-0000-0000-0000-000000000001'),
  ('c0000000-0000-0000-0000-000000000002', 'drsilva@uok.lk', 'Dr. Kamal Silva', 'lecturer', '$2b$10$jmX9QF7SmhpTc7fqc1lpR.KpcR0FpvRFH6bTLdtOv4SJHRGng/PeW', 'a0000000-0000-0000-0000-000000000001'),
  ('c0000000-0000-0000-0000-000000000003', 'drperera@uok.lk', 'Dr. Nimali Perera', 'lecturer', '$2b$10$jmX9QF7SmhpTc7fqc1lpR.KpcR0FpvRFH6bTLdtOv4SJHRGng/PeW', 'a0000000-0000-0000-0000-000000000001'),
  ('c0000000-0000-0000-0000-000000000004', 'drfernando@uok.lk', 'Dr. Ruwan Fernando', 'lecturer', '$2b$10$jmX9QF7SmhpTc7fqc1lpR.KpcR0FpvRFH6bTLdtOv4SJHRGng/PeW', 'a0000000-0000-0000-0000-000000000001');

-- Student users
insert into users (id, email, full_name, role, password_hash, school_id) values
  ('d0000000-0000-0000-0000-000000000001', 'ashan@student.uok.lk', 'Ashan Bandara', 'student', '$2b$10$jmX9QF7SmhpTc7fqc1lpR.KpcR0FpvRFH6bTLdtOv4SJHRGng/PeW', 'a0000000-0000-0000-0000-000000000001'),
  ('d0000000-0000-0000-0000-000000000002', 'dilini@student.uok.lk', 'Dilini Jayawardena', 'student', '$2b$10$jmX9QF7SmhpTc7fqc1lpR.KpcR0FpvRFH6bTLdtOv4SJHRGng/PeW', 'a0000000-0000-0000-0000-000000000001'),
  ('d0000000-0000-0000-0000-000000000003', 'kasun@student.uok.lk', 'Kasun Rathnayake', 'student', '$2b$10$jmX9QF7SmhpTc7fqc1lpR.KpcR0FpvRFH6bTLdtOv4SJHRGng/PeW', 'a0000000-0000-0000-0000-000000000001'),
  ('d0000000-0000-0000-0000-000000000004', 'sachini@student.uok.lk', 'Sachini De Silva', 'student', '$2b$10$jmX9QF7SmhpTc7fqc1lpR.KpcR0FpvRFH6bTLdtOv4SJHRGng/PeW', 'a0000000-0000-0000-0000-000000000001'),
  ('d0000000-0000-0000-0000-000000000005', 'tharindu@student.uok.lk', 'Tharindu Wickrama', 'student', '$2b$10$jmX9QF7SmhpTc7fqc1lpR.KpcR0FpvRFH6bTLdtOv4SJHRGng/PeW', 'a0000000-0000-0000-0000-000000000001'),
  ('d0000000-0000-0000-0000-000000000006', 'nethmi@student.uok.lk', 'Nethmi Amarasinghe', 'student', '$2b$10$jmX9QF7SmhpTc7fqc1lpR.KpcR0FpvRFH6bTLdtOv4SJHRGng/PeW', 'a0000000-0000-0000-0000-000000000001'),
  ('d0000000-0000-0000-0000-000000000007', 'chamara@student.uok.lk', 'Chamara Gunawardena', 'student', '$2b$10$jmX9QF7SmhpTc7fqc1lpR.KpcR0FpvRFH6bTLdtOv4SJHRGng/PeW', 'a0000000-0000-0000-0000-000000000001'),
  ('d0000000-0000-0000-0000-000000000008', 'imalka@student.uok.lk', 'Imalka Herath', 'student', '$2b$10$jmX9QF7SmhpTc7fqc1lpR.KpcR0FpvRFH6bTLdtOv4SJHRGng/PeW', 'a0000000-0000-0000-0000-000000000001');

-- ============================================================
-- Students
-- ============================================================
insert into students (id, user_id, school_id, student_number, date_of_birth, gender, guardian_name, guardian_email) values
  ('f0000000-0000-0000-0000-000000000001', 'd0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001', 'UOK-2024-001', '2002-03-15', 'male', 'Mahinda Bandara', 'mbandara@gmail.com'),
  ('f0000000-0000-0000-0000-000000000002', 'd0000000-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000001', 'UOK-2024-002', '2003-07-22', 'female', 'Sriya Jayawardena', 'sjayawardena@gmail.com'),
  ('f0000000-0000-0000-0000-000000000003', 'd0000000-0000-0000-0000-000000000003', 'a0000000-0000-0000-0000-000000000001', 'UOK-2024-003', '2002-11-08', 'male', 'Nimal Rathnayake', 'nrathnayake@gmail.com'),
  ('f0000000-0000-0000-0000-000000000004', 'd0000000-0000-0000-0000-000000000004', 'a0000000-0000-0000-0000-000000000001', 'UOK-2024-004', '2003-01-30', 'female', 'Kumari De Silva', 'kdesilva@gmail.com'),
  ('f0000000-0000-0000-0000-000000000005', 'd0000000-0000-0000-0000-000000000005', 'a0000000-0000-0000-0000-000000000001', 'UOK-2024-005', '2002-05-12', 'male', 'Saman Wickrama', 'swickrama@gmail.com'),
  ('f0000000-0000-0000-0000-000000000006', 'd0000000-0000-0000-0000-000000000006', 'a0000000-0000-0000-0000-000000000001', 'UOK-2024-006', '2003-09-18', 'female', 'Lalitha Amarasinghe', 'lamarasinghe@gmail.com'),
  ('f0000000-0000-0000-0000-000000000007', 'd0000000-0000-0000-0000-000000000007', 'a0000000-0000-0000-0000-000000000001', 'UOK-2024-007', '2002-08-25', 'male', 'Pradeep Gunawardena', 'pgunawardena@gmail.com'),
  ('f0000000-0000-0000-0000-000000000008', 'd0000000-0000-0000-0000-000000000008', 'a0000000-0000-0000-0000-000000000001', 'UOK-2024-008', '2003-04-05', 'female', 'Kamani Herath', 'kherath@gmail.com');

-- ============================================================
-- Courses
-- ============================================================
insert into courses (id, school_id, lecturer_id, academic_year_id, name, subject, grade_level, credit_hours) values
  ('aa000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000002', 'b0000000-0000-0000-0000-000000000001', 'Data Structures & Algorithms', 'Computer Science', 'Year 2', 4),
  ('aa000000-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000003', 'b0000000-0000-0000-0000-000000000001', 'Database Management Systems', 'Computer Science', 'Year 2', 3),
  ('aa000000-0000-0000-0000-000000000003', 'a0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000004', 'b0000000-0000-0000-0000-000000000001', 'Software Engineering', 'Computer Science', 'Year 3', 3),
  ('aa000000-0000-0000-0000-000000000004', 'a0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000002', 'b0000000-0000-0000-0000-000000000001', 'Calculus II', 'Mathematics', 'Year 1', 4),
  ('aa000000-0000-0000-0000-000000000005', 'a0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000003', 'b0000000-0000-0000-0000-000000000001', 'Physics I', 'Physics', 'Year 1', 3);

-- ============================================================
-- Enrollments
-- ============================================================
insert into enrollments (id, student_id, course_id, status) values
  ('bb000000-0000-0000-0000-000000000001', 'f0000000-0000-0000-0000-000000000001', 'aa000000-0000-0000-0000-000000000001', 'active'),
  ('bb000000-0000-0000-0000-000000000002', 'f0000000-0000-0000-0000-000000000001', 'aa000000-0000-0000-0000-000000000002', 'active'),
  ('bb000000-0000-0000-0000-000000000003', 'f0000000-0000-0000-0000-000000000002', 'aa000000-0000-0000-0000-000000000001', 'active'),
  ('bb000000-0000-0000-0000-000000000004', 'f0000000-0000-0000-0000-000000000002', 'aa000000-0000-0000-0000-000000000003', 'active'),
  ('bb000000-0000-0000-0000-000000000005', 'f0000000-0000-0000-0000-000000000003', 'aa000000-0000-0000-0000-000000000002', 'active'),
  ('bb000000-0000-0000-0000-000000000006', 'f0000000-0000-0000-0000-000000000003', 'aa000000-0000-0000-0000-000000000004', 'active'),
  ('bb000000-0000-0000-0000-000000000007', 'f0000000-0000-0000-0000-000000000004', 'aa000000-0000-0000-0000-000000000001', 'active'),
  ('bb000000-0000-0000-0000-000000000008', 'f0000000-0000-0000-0000-000000000004', 'aa000000-0000-0000-0000-000000000005', 'active'),
  ('bb000000-0000-0000-0000-000000000009', 'f0000000-0000-0000-0000-000000000005', 'aa000000-0000-0000-0000-000000000003', 'active'),
  ('bb000000-0000-0000-0000-000000000010', 'f0000000-0000-0000-0000-000000000005', 'aa000000-0000-0000-0000-000000000004', 'active'),
  ('bb000000-0000-0000-0000-000000000011', 'f0000000-0000-0000-0000-000000000006', 'aa000000-0000-0000-0000-000000000001', 'active'),
  ('bb000000-0000-0000-0000-000000000012', 'f0000000-0000-0000-0000-000000000006', 'aa000000-0000-0000-0000-000000000002', 'active'),
  ('bb000000-0000-0000-0000-000000000013', 'f0000000-0000-0000-0000-000000000007', 'aa000000-0000-0000-0000-000000000004', 'active'),
  ('bb000000-0000-0000-0000-000000000014', 'f0000000-0000-0000-0000-000000000007', 'aa000000-0000-0000-0000-000000000005', 'active'),
  ('bb000000-0000-0000-0000-000000000015', 'f0000000-0000-0000-0000-000000000008', 'aa000000-0000-0000-0000-000000000003', 'active'),
  ('bb000000-0000-0000-0000-000000000016', 'f0000000-0000-0000-0000-000000000008', 'aa000000-0000-0000-0000-000000000005', 'active');

-- ============================================================
-- Grades (sample assessment data)
-- ============================================================
insert into grades (id, enrollment_id, assessment_type, title, score, max_score, weight, assessed_on, recorded_by) values
  ('cc000000-0000-0000-0000-000000000001', 'bb000000-0000-0000-0000-000000000001', 'quiz', 'Quiz 1', 85, 100, 0.10, '2025-10-15', 'c0000000-0000-0000-0000-000000000002'),
  ('cc000000-0000-0000-0000-000000000002', 'bb000000-0000-0000-0000-000000000001', 'quiz', 'Quiz 2', 78, 100, 0.10, '2025-11-12', 'c0000000-0000-0000-0000-000000000002'),
  ('cc000000-0000-0000-0000-000000000003', 'bb000000-0000-0000-0000-000000000001', 'midterm', 'Midterm Exam', 72, 100, 0.30, '2025-12-01', 'c0000000-0000-0000-0000-000000000002'),
  ('cc000000-0000-0000-0000-000000000004', 'bb000000-0000-0000-0000-000000000001', 'assignment', 'Assignment 1', 90, 100, 0.15, '2025-10-30', 'c0000000-0000-0000-0000-000000000002'),
  ('cc000000-0000-0000-0000-000000000005', 'bb000000-0000-0000-0000-000000000002', 'quiz', 'Quiz 1', 92, 100, 0.10, '2025-10-18', 'c0000000-0000-0000-0000-000000000003'),
  ('cc000000-0000-0000-0000-000000000006', 'bb000000-0000-0000-0000-000000000002', 'midterm', 'Midterm Exam', 88, 100, 0.30, '2025-12-05', 'c0000000-0000-0000-0000-000000000003'),
  ('cc000000-0000-0000-0000-000000000007', 'bb000000-0000-0000-0000-000000000002', 'project', 'ER Modeling Project', 95, 100, 0.25, '2025-11-20', 'c0000000-0000-0000-0000-000000000003'),
  ('cc000000-0000-0000-0000-000000000008', 'bb000000-0000-0000-0000-000000000003', 'quiz', 'Quiz 1', 95, 100, 0.10, '2025-10-15', 'c0000000-0000-0000-0000-000000000002'),
  ('cc000000-0000-0000-0000-000000000009', 'bb000000-0000-0000-0000-000000000003', 'midterm', 'Midterm Exam', 91, 100, 0.30, '2025-12-01', 'c0000000-0000-0000-0000-000000000002'),
  ('cc000000-0000-0000-0000-000000000010', 'bb000000-0000-0000-0000-000000000003', 'assignment', 'Assignment 1', 88, 100, 0.15, '2025-10-30', 'c0000000-0000-0000-0000-000000000002'),
  ('cc000000-0000-0000-0000-000000000011', 'bb000000-0000-0000-0000-000000000005', 'quiz', 'Quiz 1', 45, 100, 0.10, '2025-10-18', 'c0000000-0000-0000-0000-000000000003'),
  ('cc000000-0000-0000-0000-000000000012', 'bb000000-0000-0000-0000-000000000005', 'midterm', 'Midterm Exam', 38, 100, 0.30, '2025-12-05', 'c0000000-0000-0000-0000-000000000003'),
  ('cc000000-0000-0000-0000-000000000013', 'bb000000-0000-0000-0000-000000000005', 'assignment', 'Assignment 1', 55, 100, 0.15, '2025-11-10', 'c0000000-0000-0000-0000-000000000003'),
  ('cc000000-0000-0000-0000-000000000014', 'bb000000-0000-0000-0000-000000000007', 'quiz', 'Quiz 1', 76, 100, 0.10, '2025-10-15', 'c0000000-0000-0000-0000-000000000002'),
  ('cc000000-0000-0000-0000-000000000015', 'bb000000-0000-0000-0000-000000000007', 'midterm', 'Midterm Exam', 68, 100, 0.30, '2025-12-01', 'c0000000-0000-0000-0000-000000000002'),
  ('cc000000-0000-0000-0000-000000000016', 'bb000000-0000-0000-0000-000000000011', 'quiz', 'Quiz 1', 98, 100, 0.10, '2025-10-15', 'c0000000-0000-0000-0000-000000000002'),
  ('cc000000-0000-0000-0000-000000000017', 'bb000000-0000-0000-0000-000000000011', 'midterm', 'Midterm Exam', 96, 100, 0.30, '2025-12-01', 'c0000000-0000-0000-0000-000000000002'),
  ('cc000000-0000-0000-0000-000000000018', 'bb000000-0000-0000-0000-000000000011', 'assignment', 'Assignment 1', 100, 100, 0.15, '2025-10-30', 'c0000000-0000-0000-0000-000000000002');

-- ============================================================
-- Attendance samples
-- ============================================================
insert into attendance (id, enrollment_id, date, status, recorded_by) values
  ('dd000000-0000-0000-0000-000000000001', 'bb000000-0000-0000-0000-000000000001', '2025-10-01', 'present', 'c0000000-0000-0000-0000-000000000002'),
  ('dd000000-0000-0000-0000-000000000002', 'bb000000-0000-0000-0000-000000000001', '2025-10-03', 'present', 'c0000000-0000-0000-0000-000000000002'),
  ('dd000000-0000-0000-0000-000000000003', 'bb000000-0000-0000-0000-000000000001', '2025-10-08', 'present', 'c0000000-0000-0000-0000-000000000002'),
  ('dd000000-0000-0000-0000-000000000004', 'bb000000-0000-0000-0000-000000000001', '2025-10-10', 'late', 'c0000000-0000-0000-0000-000000000002'),
  ('dd000000-0000-0000-0000-000000000005', 'bb000000-0000-0000-0000-000000000001', '2025-10-15', 'present', 'c0000000-0000-0000-0000-000000000002'),
  ('dd000000-0000-0000-0000-000000000006', 'bb000000-0000-0000-0000-000000000005', '2025-10-01', 'absent', 'c0000000-0000-0000-0000-000000000003'),
  ('dd000000-0000-0000-0000-000000000007', 'bb000000-0000-0000-0000-000000000005', '2025-10-03', 'absent', 'c0000000-0000-0000-0000-000000000003'),
  ('dd000000-0000-0000-0000-000000000008', 'bb000000-0000-0000-0000-000000000005', '2025-10-08', 'present', 'c0000000-0000-0000-0000-000000000003'),
  ('dd000000-0000-0000-0000-000000000009', 'bb000000-0000-0000-0000-000000000005', '2025-10-10', 'absent', 'c0000000-0000-0000-0000-000000000003'),
  ('dd000000-0000-0000-0000-000000000010', 'bb000000-0000-0000-0000-000000000005', '2025-10-15', 'late', 'c0000000-0000-0000-0000-000000000003'),
  ('dd000000-0000-0000-0000-000000000011', 'bb000000-0000-0000-0000-000000000011', '2025-10-01', 'present', 'c0000000-0000-0000-0000-000000000002'),
  ('dd000000-0000-0000-0000-000000000012', 'bb000000-0000-0000-0000-000000000011', '2025-10-03', 'present', 'c0000000-0000-0000-0000-000000000002'),
  ('dd000000-0000-0000-0000-000000000013', 'bb000000-0000-0000-0000-000000000011', '2025-10-08', 'present', 'c0000000-0000-0000-0000-000000000002'),
  ('dd000000-0000-0000-0000-000000000014', 'bb000000-0000-0000-0000-000000000011', '2025-10-10', 'present', 'c0000000-0000-0000-0000-000000000002'),
  ('dd000000-0000-0000-0000-000000000015', 'bb000000-0000-0000-0000-000000000011', '2025-10-15', 'present', 'c0000000-0000-0000-0000-000000000002');

-- ============================================================
-- Predictions
-- ============================================================
insert into predictions (
  id, student_id, course_id, predicted_grade, pass_probability, risk_level, factors, recommendations, ai_summary, generated_at
) values
  (
    'ff000000-0000-0000-0000-000000000001',
    'f0000000-0000-0000-0000-000000000001',
    'aa000000-0000-0000-0000-000000000001',
    81,
    0.91,
    'low',
    jsonb_build_array(
      jsonb_build_object('factor', 'attendance', 'impact', 'positive', 'detail', 'Consistent class participation and strong attendance.'),
      jsonb_build_object('factor', 'assessment_trend', 'impact', 'positive', 'detail', 'Quiz and assignment scores are stable above course average.')
    ),
    jsonb_build_array('Keep the current study cadence', 'Start midterm revision one week earlier'),
    'Ashan is on track for a strong pass with steady performance and manageable risk.',
    '2026-01-10 09:00:00+00'
  ),
  (
    'ff000000-0000-0000-0000-000000000002',
    'f0000000-0000-0000-0000-000000000002',
    'aa000000-0000-0000-0000-000000000003',
    87,
    0.96,
    'low',
    jsonb_build_array(
      jsonb_build_object('factor', 'midterm', 'impact', 'positive', 'detail', 'Midterm performance indicates strong concept retention.'),
      jsonb_build_object('factor', 'assignment_quality', 'impact', 'positive', 'detail', 'Assignment submissions are complete and accurate.')
    ),
    jsonb_build_array('Introduce advanced practice problems', 'Encourage peer mentoring in project work'),
    'Dilini is performing at a high level and shows strong confidence across assessed work.',
    '2026-01-11 09:15:00+00'
  ),
  (
    'ff000000-0000-0000-0000-000000000003',
    'f0000000-0000-0000-0000-000000000003',
    'aa000000-0000-0000-0000-000000000002',
    46,
    0.38,
    'critical',
    jsonb_build_array(
      jsonb_build_object('factor', 'attendance', 'impact', 'negative', 'detail', 'Repeated absences are reducing continuity of learning.'),
      jsonb_build_object('factor', 'midterm', 'impact', 'negative', 'detail', 'Midterm score indicates major gaps in database fundamentals.')
    ),
    jsonb_build_array('Schedule weekly remedial sessions', 'Contact guardian and agree on an attendance plan', 'Prioritize SQL practice and ER modeling exercises'),
    'Kasun is at critical risk and needs immediate academic and attendance intervention.',
    '2026-01-11 10:00:00+00'
  ),
  (
    'ff000000-0000-0000-0000-000000000004',
    'f0000000-0000-0000-0000-000000000004',
    'aa000000-0000-0000-0000-000000000001',
    69,
    0.74,
    'medium',
    jsonb_build_array(
      jsonb_build_object('factor', 'midterm', 'impact', 'neutral', 'detail', 'Midterm result is slightly below target for an A or B outcome.'),
      jsonb_build_object('factor', 'attendance', 'impact', 'positive', 'detail', 'Attendance is regular enough to support recovery.')
    ),
    jsonb_build_array('Reinforce problem-solving drills', 'Review recursion and time complexity concepts'),
    'Sachini can recover into a solid B range with targeted practice in core DSA topics.',
    '2026-01-12 08:45:00+00'
  ),
  (
    'ff000000-0000-0000-0000-000000000005',
    'f0000000-0000-0000-0000-000000000005',
    'aa000000-0000-0000-0000-000000000003',
    63,
    0.67,
    'medium',
    jsonb_build_array(
      jsonb_build_object('factor', 'course_load', 'impact', 'negative', 'detail', 'Performance is uneven across concurrent technical courses.'),
      jsonb_build_object('factor', 'engagement', 'impact', 'positive', 'detail', 'Participation remains strong during interactive sessions.')
    ),
    jsonb_build_array('Break project work into weekly milestones', 'Increase code review practice with peers'),
    'Tharindu is likely to pass but needs steadier execution on project-oriented tasks.',
    '2026-01-12 11:20:00+00'
  ),
  (
    'ff000000-0000-0000-0000-000000000006',
    'f0000000-0000-0000-0000-000000000006',
    'aa000000-0000-0000-0000-000000000001',
    93,
    0.99,
    'low',
    jsonb_build_array(
      jsonb_build_object('factor', 'assessment_trend', 'impact', 'positive', 'detail', 'All graded components show excellent consistency.'),
      jsonb_build_object('factor', 'attendance', 'impact', 'positive', 'detail', 'Perfect attendance supports continued high performance.')
    ),
    jsonb_build_array('Sustain the current revision pattern', 'Introduce enrichment problems to maintain challenge'),
    'Nethmi is the strongest performer in the cohort and is expected to finish with distinction-level results.',
    '2026-01-13 09:40:00+00'
  ),
  (
    'ff000000-0000-0000-0000-000000000007',
    'f0000000-0000-0000-0000-000000000007',
    'aa000000-0000-0000-0000-000000000004',
    58,
    0.61,
    'high',
    jsonb_build_array(
      jsonb_build_object('factor', 'concept_mastery', 'impact', 'negative', 'detail', 'Foundational calculus topics need reinforcement.'),
      jsonb_build_object('factor', 'attendance', 'impact', 'neutral', 'detail', 'Attendance is acceptable but not enough to offset weak assessment depth.')
    ),
    jsonb_build_array('Provide focused calculus tutoring', 'Assign weekly derivative and integration practice'),
    'Chamara shows elevated risk because assessment performance is not yet stable in mathematics.',
    '2026-01-13 12:05:00+00'
  ),
  (
    'ff000000-0000-0000-0000-000000000008',
    'f0000000-0000-0000-0000-000000000008',
    'aa000000-0000-0000-0000-000000000005',
    71,
    0.79,
    'medium',
    jsonb_build_array(
      jsonb_build_object('factor', 'project_work', 'impact', 'positive', 'detail', 'Applied tasks show stronger understanding than timed quizzes.'),
      jsonb_build_object('factor', 'exam_readiness', 'impact', 'negative', 'detail', 'Timed assessments still show hesitation under pressure.')
    ),
    jsonb_build_array('Add timed practice sets', 'Use retrieval practice before each lecture'),
    'Imalka is trending toward a comfortable pass but would benefit from better exam pacing.',
    '2026-01-14 08:30:00+00'
  );

-- ============================================================
-- AI Insights
-- ============================================================
insert into ai_insights (id, student_id, insight_type, content, metadata, created_at) values
  (
    'fa000000-0000-0000-0000-000000000001',
    'f0000000-0000-0000-0000-000000000001',
    'trend',
    'Ashan has maintained a stable upward trend in coursework and should be considered for peer-support roles.',
    jsonb_build_object('confidence', 0.88, 'source', 'seed', 'priority', 'medium'),
    '2026-01-10 10:00:00+00'
  ),
  (
    'fa000000-0000-0000-0000-000000000002',
    'f0000000-0000-0000-0000-000000000002',
    'recommendation',
    'Dilini is ready for stretch assignments and collaborative leadership in software engineering activities.',
    jsonb_build_object('confidence', 0.93, 'source', 'seed', 'priority', 'low'),
    '2026-01-11 10:20:00+00'
  ),
  (
    'fa000000-0000-0000-0000-000000000003',
    'f0000000-0000-0000-0000-000000000003',
    'warning',
    'Kasun is at immediate risk due to poor attendance and weak assessment outcomes in DBMS.',
    jsonb_build_object('confidence', 0.97, 'source', 'seed', 'priority', 'high'),
    '2026-01-11 10:10:00+00'
  ),
  (
    'fa000000-0000-0000-0000-000000000004',
    'f0000000-0000-0000-0000-000000000003',
    'recommendation',
    'Create a two-week intervention plan combining attendance follow-up, tutorial support, and SQL basics review.',
    jsonb_build_object('confidence', 0.95, 'source', 'seed', 'priority', 'high'),
    '2026-01-11 10:12:00+00'
  ),
  (
    'fa000000-0000-0000-0000-000000000005',
    'f0000000-0000-0000-0000-000000000004',
    'performance',
    'Sachini is performing in the middle band and can improve significantly with stronger consistency in core algorithm exercises.',
    jsonb_build_object('confidence', 0.78, 'source', 'seed', 'priority', 'medium'),
    '2026-01-12 09:00:00+00'
  ),
  (
    'fa000000-0000-0000-0000-000000000006',
    'f0000000-0000-0000-0000-000000000005',
    'behavior',
    'Tharindu engages well in discussion-based sessions but needs more consistent independent follow-through.',
    jsonb_build_object('confidence', 0.75, 'source', 'seed', 'priority', 'medium'),
    '2026-01-12 11:45:00+00'
  ),
  (
    'fa000000-0000-0000-0000-000000000007',
    'f0000000-0000-0000-0000-000000000006',
    'performance',
    'Nethmi is performing at the top of the cohort with exceptional assessment reliability and attendance.',
    jsonb_build_object('confidence', 0.99, 'source', 'seed', 'priority', 'low'),
    '2026-01-13 09:50:00+00'
  ),
  (
    'fa000000-0000-0000-0000-000000000008',
    'f0000000-0000-0000-0000-000000000007',
    'warning',
    'Chamara may struggle in upcoming mathematics assessments without structured weekly support.',
    jsonb_build_object('confidence', 0.84, 'source', 'seed', 'priority', 'high'),
    '2026-01-13 12:15:00+00'
  ),
  (
    'fa000000-0000-0000-0000-000000000009',
    'f0000000-0000-0000-0000-000000000008',
    'trend',
    'Imalka shows gradual improvement in applied tasks but still needs timed-practice support.',
    jsonb_build_object('confidence', 0.8, 'source', 'seed', 'priority', 'medium'),
    '2026-01-14 08:40:00+00'
  ),
  (
    'fa000000-0000-0000-0000-000000000010',
    'f0000000-0000-0000-0000-000000000001',
    'recommendation',
    'Invite Ashan to lead a revision group before the next algorithm assessment window.',
    jsonb_build_object('confidence', 0.82, 'source', 'seed', 'priority', 'low'),
    '2026-01-14 09:10:00+00'
  );

-- ============================================================
-- Notifications
-- ============================================================
insert into notifications (id, recipient_id, type, title, body, is_read, created_at) values
  (
    'fb000000-0000-0000-0000-000000000001',
    'd0000000-0000-0000-0000-000000000001',
    'prediction',
    'New performance prediction available',
    'Your latest prediction for Data Structures & Algorithms indicates a low-risk outcome and a projected grade of 81.',
    false,
    '2026-01-10 09:05:00+00'
  ),
  (
    'fb000000-0000-0000-0000-000000000002',
    'd0000000-0000-0000-0000-000000000003',
    'warning',
    'Attendance intervention needed',
    'Your recent attendance and DBMS performance indicate urgent follow-up is required this week.',
    false,
    '2026-01-11 10:05:00+00'
  ),
  (
    'fb000000-0000-0000-0000-000000000003',
    'c0000000-0000-0000-0000-000000000001',
    'warning',
    'Student risk alert',
    'Ashan remains stable, but the system recommends continued lecturer follow-up ahead of the next midterm cycle.',
    true,
    '2026-01-11 18:00:00+00'
  ),
  (
    'fb000000-0000-0000-0000-000000000004',
    'c0000000-0000-0000-0000-000000000001',
    'prediction',
    'Positive performance update',
    'Dilini is projected to maintain a strong result in Software Engineering with low academic risk.',
    false,
    '2026-01-11 18:10:00+00'
  ),
  (
    'fb000000-0000-0000-0000-000000000005',
    'c0000000-0000-0000-0000-000000000002',
    'attendance',
    'Attendance pattern flagged',
    'A student in your cohort has crossed the threshold for repeated absences and late arrivals.',
    false,
    '2026-01-12 07:45:00+00'
  ),
  (
    'fb000000-0000-0000-0000-000000000006',
    'c0000000-0000-0000-0000-000000000003',
    'grade',
    'Low assessment cluster detected',
    'DBMS results show a student falling below the expected pass band across multiple assessments.',
    false,
    '2026-01-12 08:00:00+00'
  ),
  (
    'fb000000-0000-0000-0000-000000000007',
    'c0000000-0000-0000-0000-000000000004',
    'system',
    'AI insights refreshed',
    'New AI-generated student insights are available for your current course roster.',
    true,
    '2026-01-12 08:05:00+00'
  ),
  (
    'fb000000-0000-0000-0000-000000000008',
    'c0000000-0000-0000-0000-000000000001',
    'system',
    'Daily analytics digest ready',
    'The school-level analytics summary has been updated with the latest prediction and attendance data.',
    false,
    '2026-01-12 08:15:00+00'
  ),
  (
    'fb000000-0000-0000-0000-000000000009',
    'd0000000-0000-0000-0000-000000000006',
    'prediction',
    'Excellent progress recorded',
    'Your latest academic prediction indicates distinction-level performance with very low risk.',
    false,
    '2026-01-13 09:45:00+00'
  ),
  (
    'fb000000-0000-0000-0000-000000000010',
    'd0000000-0000-0000-0000-000000000007',
    'warning',
    'Math support recommended',
    'Your projected result in Calculus II has moved into a higher-risk band. Please meet your instructor this week.',
    false,
    '2026-01-13 12:20:00+00'
  ),
  (
    'fb000000-0000-0000-0000-000000000011',
    'd0000000-0000-0000-0000-000000000008',
    'attendance',
    'Preparation reminder',
    'Maintain attendance and complete timed practice sets before the next Physics I assessment.',
    true,
    '2026-01-14 08:45:00+00'
  ),
  (
    'fb000000-0000-0000-0000-000000000012',
    'd0000000-0000-0000-0000-000000000004',
    'grade',
    'Revision plan suggested',
    'Targeted revision in algorithms and complexity analysis could improve your projected grade band.',
    false,
    '2026-01-14 09:00:00+00'
  );

-- ============================================================
-- Expanded Seed Pack
-- ============================================================

-- Additional student users
insert into users (id, email, full_name, role, password_hash, school_id) values
  ('d0000000-0000-0000-0000-000000000009', 'shehan@student.uok.lk', 'Shehan Peris', 'student', '$2b$10$jmX9QF7SmhpTc7fqc1lpR.KpcR0FpvRFH6bTLdtOv4SJHRGng/PeW', 'a0000000-0000-0000-0000-000000000001'),
  ('d0000000-0000-0000-0000-000000000010', 'piumi@student.uok.lk', 'Piumi Senanayake', 'student', '$2b$10$jmX9QF7SmhpTc7fqc1lpR.KpcR0FpvRFH6bTLdtOv4SJHRGng/PeW', 'a0000000-0000-0000-0000-000000000001'),
  ('d0000000-0000-0000-0000-000000000011', 'ravindu@student.uok.lk', 'Ravindu Jayasuriya', 'student', '$2b$10$jmX9QF7SmhpTc7fqc1lpR.KpcR0FpvRFH6bTLdtOv4SJHRGng/PeW', 'a0000000-0000-0000-0000-000000000001'),
  ('d0000000-0000-0000-0000-000000000012', 'tharushi@student.uok.lk', 'Tharushi Wickremasinghe', 'student', '$2b$10$jmX9QF7SmhpTc7fqc1lpR.KpcR0FpvRFH6bTLdtOv4SJHRGng/PeW', 'a0000000-0000-0000-0000-000000000001');

-- Additional students
insert into students (id, user_id, school_id, student_number, date_of_birth, gender, guardian_name, guardian_email) values
  ('f0000000-0000-0000-0000-000000000009', 'd0000000-0000-0000-0000-000000000009', 'a0000000-0000-0000-0000-000000000001', 'UOK-2024-009', '2002-06-11', 'male', 'Nadeesha Peris', 'nperis@gmail.com'),
  ('f0000000-0000-0000-0000-000000000010', 'd0000000-0000-0000-0000-000000000010', 'a0000000-0000-0000-0000-000000000001', 'UOK-2024-010', '2003-02-14', 'female', 'Sulochana Senanayake', 'ssenanayake@gmail.com'),
  ('f0000000-0000-0000-0000-000000000011', 'd0000000-0000-0000-0000-000000000011', 'a0000000-0000-0000-0000-000000000001', 'UOK-2024-011', '2002-12-21', 'male', 'Anura Jayasuriya', 'ajayasuriya@gmail.com'),
  ('f0000000-0000-0000-0000-000000000012', 'd0000000-0000-0000-0000-000000000012', 'a0000000-0000-0000-0000-000000000001', 'UOK-2024-012', '2003-06-03', 'female', 'Lakmali Wickremasinghe', 'lwick@gmail.com');

-- Additional enrollments
insert into enrollments (id, student_id, course_id, status) values
  ('bb000000-0000-0000-0000-000000000017', 'f0000000-0000-0000-0000-000000000009', 'aa000000-0000-0000-0000-000000000001', 'active'),
  ('bb000000-0000-0000-0000-000000000018', 'f0000000-0000-0000-0000-000000000009', 'aa000000-0000-0000-0000-000000000003', 'active'),
  ('bb000000-0000-0000-0000-000000000019', 'f0000000-0000-0000-0000-000000000010', 'aa000000-0000-0000-0000-000000000002', 'active'),
  ('bb000000-0000-0000-0000-000000000020', 'f0000000-0000-0000-0000-000000000010', 'aa000000-0000-0000-0000-000000000005', 'active'),
  ('bb000000-0000-0000-0000-000000000021', 'f0000000-0000-0000-0000-000000000011', 'aa000000-0000-0000-0000-000000000002', 'active'),
  ('bb000000-0000-0000-0000-000000000022', 'f0000000-0000-0000-0000-000000000011', 'aa000000-0000-0000-0000-000000000004', 'active'),
  ('bb000000-0000-0000-0000-000000000023', 'f0000000-0000-0000-0000-000000000012', 'aa000000-0000-0000-0000-000000000003', 'active'),
  ('bb000000-0000-0000-0000-000000000024', 'f0000000-0000-0000-0000-000000000012', 'aa000000-0000-0000-0000-000000000005', 'active');

-- Additional grades
insert into grades (id, enrollment_id, assessment_type, title, score, max_score, weight, assessed_on, recorded_by) values
  ('cc000000-0000-0000-0000-000000000019', 'bb000000-0000-0000-0000-000000000017', 'quiz', 'Quiz 1', 74, 100, 0.10, '2025-10-15', 'c0000000-0000-0000-0000-000000000002'),
  ('cc000000-0000-0000-0000-000000000020', 'bb000000-0000-0000-0000-000000000017', 'midterm', 'Midterm Exam', 70, 100, 0.30, '2025-12-01', 'c0000000-0000-0000-0000-000000000002'),
  ('cc000000-0000-0000-0000-000000000021', 'bb000000-0000-0000-0000-000000000018', 'assignment', 'Sprint Planning Report', 81, 100, 0.20, '2025-11-04', 'c0000000-0000-0000-0000-000000000004'),
  ('cc000000-0000-0000-0000-000000000022', 'bb000000-0000-0000-0000-000000000018', 'project', 'Group Prototype', 86, 100, 0.30, '2025-11-29', 'c0000000-0000-0000-0000-000000000004'),
  ('cc000000-0000-0000-0000-000000000023', 'bb000000-0000-0000-0000-000000000019', 'quiz', 'Normalization Quiz', 89, 100, 0.10, '2025-10-18', 'c0000000-0000-0000-0000-000000000003'),
  ('cc000000-0000-0000-0000-000000000024', 'bb000000-0000-0000-0000-000000000019', 'midterm', 'DBMS Midterm', 84, 100, 0.30, '2025-12-05', 'c0000000-0000-0000-0000-000000000003'),
  ('cc000000-0000-0000-0000-000000000025', 'bb000000-0000-0000-0000-000000000020', 'quiz', 'Mechanics Quiz', 67, 100, 0.10, '2025-10-20', 'c0000000-0000-0000-0000-000000000003'),
  ('cc000000-0000-0000-0000-000000000026', 'bb000000-0000-0000-0000-000000000020', 'assignment', 'Lab Report 1', 72, 100, 0.15, '2025-11-07', 'c0000000-0000-0000-0000-000000000003'),
  ('cc000000-0000-0000-0000-000000000027', 'bb000000-0000-0000-0000-000000000021', 'quiz', 'SQL Query Quiz', 58, 100, 0.10, '2025-10-18', 'c0000000-0000-0000-0000-000000000003'),
  ('cc000000-0000-0000-0000-000000000028', 'bb000000-0000-0000-0000-000000000021', 'midterm', 'DBMS Midterm', 61, 100, 0.30, '2025-12-05', 'c0000000-0000-0000-0000-000000000003'),
  ('cc000000-0000-0000-0000-000000000029', 'bb000000-0000-0000-0000-000000000022', 'quiz', 'Derivatives Quiz', 64, 100, 0.10, '2025-10-22', 'c0000000-0000-0000-0000-000000000002'),
  ('cc000000-0000-0000-0000-000000000030', 'bb000000-0000-0000-0000-000000000022', 'assignment', 'Integration Worksheet', 69, 100, 0.15, '2025-11-12', 'c0000000-0000-0000-0000-000000000002'),
  ('cc000000-0000-0000-0000-000000000031', 'bb000000-0000-0000-0000-000000000023', 'quiz', 'Agile Quiz', 91, 100, 0.10, '2025-10-19', 'c0000000-0000-0000-0000-000000000004'),
  ('cc000000-0000-0000-0000-000000000032', 'bb000000-0000-0000-0000-000000000023', 'project', 'Requirements Model', 94, 100, 0.25, '2025-11-26', 'c0000000-0000-0000-0000-000000000004'),
  ('cc000000-0000-0000-0000-000000000033', 'bb000000-0000-0000-0000-000000000024', 'quiz', 'Wave Motion Quiz', 78, 100, 0.10, '2025-10-24', 'c0000000-0000-0000-0000-000000000003'),
  ('cc000000-0000-0000-0000-000000000034', 'bb000000-0000-0000-0000-000000000024', 'midterm', 'Physics Midterm', 82, 100, 0.30, '2025-12-08', 'c0000000-0000-0000-0000-000000000003');

-- Additional attendance
insert into attendance (id, enrollment_id, date, status, recorded_by) values
  ('dd000000-0000-0000-0000-000000000016', 'bb000000-0000-0000-0000-000000000017', '2025-10-01', 'present', 'c0000000-0000-0000-0000-000000000002'),
  ('dd000000-0000-0000-0000-000000000017', 'bb000000-0000-0000-0000-000000000017', '2025-10-03', 'present', 'c0000000-0000-0000-0000-000000000002'),
  ('dd000000-0000-0000-0000-000000000018', 'bb000000-0000-0000-0000-000000000018', '2025-10-05', 'late', 'c0000000-0000-0000-0000-000000000004'),
  ('dd000000-0000-0000-0000-000000000019', 'bb000000-0000-0000-0000-000000000018', '2025-10-12', 'present', 'c0000000-0000-0000-0000-000000000004'),
  ('dd000000-0000-0000-0000-000000000020', 'bb000000-0000-0000-0000-000000000019', '2025-10-02', 'present', 'c0000000-0000-0000-0000-000000000003'),
  ('dd000000-0000-0000-0000-000000000021', 'bb000000-0000-0000-0000-000000000019', '2025-10-09', 'present', 'c0000000-0000-0000-0000-000000000003'),
  ('dd000000-0000-0000-0000-000000000022', 'bb000000-0000-0000-0000-000000000020', '2025-10-04', 'absent', 'c0000000-0000-0000-0000-000000000003'),
  ('dd000000-0000-0000-0000-000000000023', 'bb000000-0000-0000-0000-000000000020', '2025-10-11', 'present', 'c0000000-0000-0000-0000-000000000003'),
  ('dd000000-0000-0000-0000-000000000024', 'bb000000-0000-0000-0000-000000000021', '2025-10-02', 'late', 'c0000000-0000-0000-0000-000000000003'),
  ('dd000000-0000-0000-0000-000000000025', 'bb000000-0000-0000-0000-000000000021', '2025-10-09', 'absent', 'c0000000-0000-0000-0000-000000000003'),
  ('dd000000-0000-0000-0000-000000000026', 'bb000000-0000-0000-0000-000000000022', '2025-10-06', 'present', 'c0000000-0000-0000-0000-000000000002'),
  ('dd000000-0000-0000-0000-000000000027', 'bb000000-0000-0000-0000-000000000022', '2025-10-13', 'present', 'c0000000-0000-0000-0000-000000000002'),
  ('dd000000-0000-0000-0000-000000000028', 'bb000000-0000-0000-0000-000000000023', '2025-10-07', 'present', 'c0000000-0000-0000-0000-000000000004'),
  ('dd000000-0000-0000-0000-000000000029', 'bb000000-0000-0000-0000-000000000023', '2025-10-14', 'present', 'c0000000-0000-0000-0000-000000000004'),
  ('dd000000-0000-0000-0000-000000000030', 'bb000000-0000-0000-0000-000000000024', '2025-10-08', 'present', 'c0000000-0000-0000-0000-000000000003'),
  ('dd000000-0000-0000-0000-000000000031', 'bb000000-0000-0000-0000-000000000024', '2025-10-15', 'late', 'c0000000-0000-0000-0000-000000000003');

-- Additional predictions
insert into predictions (id, student_id, course_id, predicted_grade, pass_probability, risk_level, factors, recommendations, ai_summary, generated_at) values
  ('ff000000-0000-0000-0000-000000000009', 'f0000000-0000-0000-0000-000000000009', 'aa000000-0000-0000-0000-000000000001', 73, 0.78, 'medium', jsonb_build_array(jsonb_build_object('factor', 'consistency', 'impact', 'positive', 'detail', 'Stable attendance supports moderate performance'), jsonb_build_object('factor', 'problem_solving', 'impact', 'neutral', 'detail', 'Algorithmic performance is steady but not exceptional')), jsonb_build_array('Increase timed algorithm practice', 'Revise linked list and tree questions weekly'), 'Shehan is likely to pass comfortably but needs more consistency to move into the top band.', '2026-01-15 09:00:00+00'),
  ('ff000000-0000-0000-0000-000000000010', 'f0000000-0000-0000-0000-000000000010', 'aa000000-0000-0000-0000-000000000002', 84, 0.92, 'low', jsonb_build_array(jsonb_build_object('factor', 'database_theory', 'impact', 'positive', 'detail', 'Strong normalization and schema design understanding'), jsonb_build_object('factor', 'lab_work', 'impact', 'positive', 'detail', 'Practical work is consistently accurate')), jsonb_build_array('Keep current DBMS revision plan', 'Start exam summaries two weeks earlier'), 'Piumi is showing strong database performance with low academic risk.', '2026-01-15 10:10:00+00'),
  ('ff000000-0000-0000-0000-000000000011', 'f0000000-0000-0000-0000-000000000011', 'aa000000-0000-0000-0000-000000000004', 59, 0.64, 'high', jsonb_build_array(jsonb_build_object('factor', 'attendance', 'impact', 'negative', 'detail', 'Missed sessions are slowing progress in calculus'), jsonb_build_object('factor', 'quiz_scores', 'impact', 'negative', 'detail', 'Quiz results remain below desired threshold')), jsonb_build_array('Provide weekly calculus tutoring', 'Assign focused practice on derivatives and integration'), 'Ravindu remains at elevated risk in mathematics and needs regular intervention.', '2026-01-15 11:20:00+00'),
  ('ff000000-0000-0000-0000-000000000012', 'f0000000-0000-0000-0000-000000000012', 'aa000000-0000-0000-0000-000000000003', 90, 0.97, 'low', jsonb_build_array(jsonb_build_object('factor', 'project_delivery', 'impact', 'positive', 'detail', 'Project work quality is consistently high'), jsonb_build_object('factor', 'class_engagement', 'impact', 'positive', 'detail', 'Active participation supports strong retention')), jsonb_build_array('Maintain project leadership responsibilities', 'Attempt advanced system design exercises'), 'Tharushi is trending toward an excellent result with strong project-based performance.', '2026-01-15 12:15:00+00');

-- Additional AI insights
insert into ai_insights (id, student_id, insight_type, content, metadata, created_at) values
  ('fa000000-0000-0000-0000-000000000011', 'f0000000-0000-0000-0000-000000000009', 'performance', 'Shehan is maintaining stable performance and would benefit from more advanced algorithm practice.', jsonb_build_object('confidence', 0.81, 'source', 'seed-expansion', 'priority', 'medium'), '2026-01-15 09:15:00+00'),
  ('fa000000-0000-0000-0000-000000000012', 'f0000000-0000-0000-0000-000000000010', 'trend', 'Piumi shows a strong upward trend in DBMS and practical science coursework.', jsonb_build_object('confidence', 0.9, 'source', 'seed-expansion', 'priority', 'low'), '2026-01-15 10:20:00+00'),
  ('fa000000-0000-0000-0000-000000000013', 'f0000000-0000-0000-0000-000000000011', 'warning', 'Ravindu needs structured calculus support before the next assessment cycle.', jsonb_build_object('confidence', 0.88, 'source', 'seed-expansion', 'priority', 'high'), '2026-01-15 11:30:00+00'),
  ('fa000000-0000-0000-0000-000000000014', 'f0000000-0000-0000-0000-000000000012', 'recommendation', 'Tharushi is ready for higher-complexity software engineering assignments and peer mentoring opportunities.', jsonb_build_object('confidence', 0.93, 'source', 'seed-expansion', 'priority', 'low'), '2026-01-15 12:25:00+00');

-- Additional notifications
insert into notifications (id, recipient_id, type, title, body, is_read, created_at) values
  ('fb000000-0000-0000-0000-000000000013', 'd0000000-0000-0000-0000-000000000009', 'prediction', 'Updated DSA forecast', 'Your latest DSA projection remains stable in the medium-risk band.', false, '2026-01-15 09:18:00+00'),
  ('fb000000-0000-0000-0000-000000000014', 'd0000000-0000-0000-0000-000000000010', 'prediction', 'Strong DBMS performance', 'Your latest DBMS prediction shows low risk and strong pass probability.', false, '2026-01-15 10:22:00+00'),
  ('fb000000-0000-0000-0000-000000000015', 'd0000000-0000-0000-0000-000000000011', 'warning', 'Calculus intervention required', 'Your current Calculus II trend requires extra support before the next quiz.', false, '2026-01-15 11:35:00+00'),
  ('fb000000-0000-0000-0000-000000000016', 'd0000000-0000-0000-0000-000000000012', 'grade', 'Excellent project result', 'Your Software Engineering project performance remains among the highest in the cohort.', false, '2026-01-15 12:28:00+00'),
  ('fb000000-0000-0000-0000-000000000017', 'c0000000-0000-0000-0000-000000000001', 'attendance', 'Attendance summary available', 'A fresh attendance summary is available for Shehan Peris.', true, '2026-01-15 13:00:00+00'),
  ('fb000000-0000-0000-0000-000000000018', 'c0000000-0000-0000-0000-000000000001', 'warning', 'Academic support recommended', 'Ravindu would benefit from immediate calculus tutoring support this week.', false, '2026-01-15 13:10:00+00');

-- ============================================================
-- ML training backfill
-- ----
-- Adds non-final grades to enrollments that have none, then adds
-- a 'final' grade to every enrollment. Without these, ml/dataset.py
-- produces zero training rows (it filters on assessment_type='final').
-- Values are deterministic and produce a mixed pass/fail label
-- distribution so the classifier has both classes during training.
-- ============================================================

-- Non-final grades for the 10 enrollments that were previously empty.
-- Score patterns are tuned to cover both passing and failing student
-- profiles so the trained model sees real variance across all features.
insert into grades (enrollment_id, assessment_type, title, score, max_score, weight, assessed_on) values
  -- bb...004 (Software Eng) - struggling
  ('bb000000-0000-0000-0000-000000000004', 'quiz',       'Requirements quiz',  12, 30, 0.10, '2025-09-12'),
  ('bb000000-0000-0000-0000-000000000004', 'assignment', 'UML diagrams',       28, 60, 0.20, '2025-09-26'),
  ('bb000000-0000-0000-0000-000000000004', 'midterm',    'Midterm exam',       34, 80, 0.30, '2025-10-24'),
  -- bb...006 (Calculus II) - struggling
  ('bb000000-0000-0000-0000-000000000006', 'quiz',       'Derivatives quiz',   14, 30, 0.10, '2025-09-15'),
  ('bb000000-0000-0000-0000-000000000006', 'assignment', 'Integration set',    24, 50, 0.20, '2025-10-01'),
  ('bb000000-0000-0000-0000-000000000006', 'midterm',    'Calculus midterm',   42, 80, 0.30, '2025-10-28'),
  -- bb...008 (Physics I) - borderline pass
  ('bb000000-0000-0000-0000-000000000008', 'quiz',       'Mechanics quiz',     17, 30, 0.10, '2025-09-17'),
  ('bb000000-0000-0000-0000-000000000008', 'assignment', 'Lab report 1',       35, 60, 0.20, '2025-10-05'),
  ('bb000000-0000-0000-0000-000000000008', 'midterm',    'Physics midterm',    52, 80, 0.30, '2025-10-30'),
  -- bb...009 (Software Eng) - mid-tier
  ('bb000000-0000-0000-0000-000000000009', 'quiz',       'Agile quiz',         21, 30, 0.10, '2025-09-20'),
  ('bb000000-0000-0000-0000-000000000009', 'assignment', 'Architecture doc',   42, 60, 0.20, '2025-10-08'),
  ('bb000000-0000-0000-0000-000000000009', 'midterm',    'SE midterm',         58, 80, 0.30, '2025-11-02'),
  -- bb...010 (Calculus II) - solid
  ('bb000000-0000-0000-0000-000000000010', 'quiz',       'Limits quiz',        24, 30, 0.10, '2025-09-22'),
  ('bb000000-0000-0000-0000-000000000010', 'assignment', 'Series problem set', 48, 60, 0.20, '2025-10-10'),
  ('bb000000-0000-0000-0000-000000000010', 'midterm',    'Calculus midterm',   62, 80, 0.30, '2025-11-05'),
  -- bb...012 (DBMS) - failing
  ('bb000000-0000-0000-0000-000000000012', 'quiz',       'Normalization quiz', 11, 30, 0.10, '2025-09-12'),
  ('bb000000-0000-0000-0000-000000000012', 'assignment', 'ER diagrams',        24, 60, 0.20, '2025-09-30'),
  ('bb000000-0000-0000-0000-000000000012', 'midterm',    'DBMS midterm',       32, 80, 0.30, '2025-10-26'),
  -- bb...013 (Calculus II) - passing
  ('bb000000-0000-0000-0000-000000000013', 'quiz',       'Functions quiz',     19, 30, 0.10, '2025-09-17'),
  ('bb000000-0000-0000-0000-000000000013', 'assignment', 'Application set',    38, 60, 0.20, '2025-10-04'),
  ('bb000000-0000-0000-0000-000000000013', 'midterm',    'Calculus midterm',   52, 80, 0.30, '2025-10-30'),
  -- bb...014 (Physics I) - strong
  ('bb000000-0000-0000-0000-000000000014', 'quiz',       'Vectors quiz',       26, 30, 0.10, '2025-09-19'),
  ('bb000000-0000-0000-0000-000000000014', 'assignment', 'Lab report 2',       52, 60, 0.20, '2025-10-06'),
  ('bb000000-0000-0000-0000-000000000014', 'midterm',    'Physics midterm',    68, 80, 0.30, '2025-10-31'),
  -- bb...015 (Software Eng) - critically failing
  ('bb000000-0000-0000-0000-000000000015', 'quiz',       'Testing quiz',       9,  30, 0.10, '2025-09-24'),
  ('bb000000-0000-0000-0000-000000000015', 'assignment', 'Test plan',          18, 60, 0.20, '2025-10-12'),
  ('bb000000-0000-0000-0000-000000000015', 'midterm',    'SE midterm',         24, 80, 0.30, '2025-11-07'),
  -- bb...016 (Physics I) - borderline pass
  ('bb000000-0000-0000-0000-000000000016', 'quiz',       'Waves quiz',         15, 30, 0.10, '2025-09-26'),
  ('bb000000-0000-0000-0000-000000000016', 'assignment', 'Lab report 3',       32, 60, 0.20, '2025-10-14'),
  ('bb000000-0000-0000-0000-000000000016', 'midterm',    'Physics midterm',    42, 80, 0.30, '2025-11-09');

-- Final exam scores for every enrollment - this is the regression
-- target and (after thresholding at 50%) the classification label.
insert into grades (enrollment_id, assessment_type, title, score, max_score, weight, assessed_on) values
  ('bb000000-0000-0000-0000-000000000001', 'final', 'DSA final',       80, 100, 0.40, '2026-01-18'),
  ('bb000000-0000-0000-0000-000000000002', 'final', 'DBMS final',      88, 100, 0.40, '2026-01-18'),
  ('bb000000-0000-0000-0000-000000000003', 'final', 'DSA final',       85, 100, 0.40, '2026-01-18'),
  ('bb000000-0000-0000-0000-000000000004', 'final', 'SE final',        38, 100, 0.40, '2026-01-18'),
  ('bb000000-0000-0000-0000-000000000005', 'final', 'DBMS final',      44, 100, 0.40, '2026-01-18'),
  ('bb000000-0000-0000-0000-000000000006', 'final', 'Calculus final',  42, 100, 0.40, '2026-01-18'),
  ('bb000000-0000-0000-0000-000000000007', 'final', 'DSA final',       70, 100, 0.40, '2026-01-18'),
  ('bb000000-0000-0000-0000-000000000008', 'final', 'Physics final',   58, 100, 0.40, '2026-01-18'),
  ('bb000000-0000-0000-0000-000000000009', 'final', 'SE final',        67, 100, 0.40, '2026-01-18'),
  ('bb000000-0000-0000-0000-000000000010', 'final', 'Calculus final',  78, 100, 0.40, '2026-01-18'),
  ('bb000000-0000-0000-0000-000000000011', 'final', 'DSA final',       95, 100, 0.40, '2026-01-18'),
  ('bb000000-0000-0000-0000-000000000012', 'final', 'DBMS final',      36, 100, 0.40, '2026-01-18'),
  ('bb000000-0000-0000-0000-000000000013', 'final', 'Calculus final',  65, 100, 0.40, '2026-01-18'),
  ('bb000000-0000-0000-0000-000000000014', 'final', 'Physics final',   88, 100, 0.40, '2026-01-18'),
  ('bb000000-0000-0000-0000-000000000015', 'final', 'SE final',        28, 100, 0.40, '2026-01-18'),
  ('bb000000-0000-0000-0000-000000000016', 'final', 'Physics final',   52, 100, 0.40, '2026-01-18'),
  ('bb000000-0000-0000-0000-000000000017', 'final', 'DSA final',       68, 100, 0.40, '2026-01-18'),
  ('bb000000-0000-0000-0000-000000000018', 'final', 'SE final',        82, 100, 0.40, '2026-01-18'),
  ('bb000000-0000-0000-0000-000000000019', 'final', 'DBMS final',      84, 100, 0.40, '2026-01-18'),
  ('bb000000-0000-0000-0000-000000000020', 'final', 'Physics final',   65, 100, 0.40, '2026-01-18'),
  ('bb000000-0000-0000-0000-000000000021', 'final', 'DBMS final',      55, 100, 0.40, '2026-01-18'),
  ('bb000000-0000-0000-0000-000000000022', 'final', 'Calculus final',  62, 100, 0.40, '2026-01-18'),
  ('bb000000-0000-0000-0000-000000000023', 'final', 'SE final',        90, 100, 0.40, '2026-01-18'),
  ('bb000000-0000-0000-0000-000000000024', 'final', 'Physics final',   78, 100, 0.40, '2026-01-18');

-- Attendance for the 10 previously-empty enrollments, with patterns
-- that correlate with grade performance (low attendance for failing
-- profiles, high for passing) so the model can pick up the signal.
insert into attendance (enrollment_id, date, status) values
  ('bb000000-0000-0000-0000-000000000004', '2025-09-08', 'absent'),
  ('bb000000-0000-0000-0000-000000000004', '2025-09-15', 'absent'),
  ('bb000000-0000-0000-0000-000000000004', '2025-09-22', 'late'),
  ('bb000000-0000-0000-0000-000000000004', '2025-09-29', 'present'),
  ('bb000000-0000-0000-0000-000000000004', '2025-10-06', 'absent'),
  ('bb000000-0000-0000-0000-000000000006', '2025-09-09', 'absent'),
  ('bb000000-0000-0000-0000-000000000006', '2025-09-16', 'late'),
  ('bb000000-0000-0000-0000-000000000006', '2025-09-23', 'absent'),
  ('bb000000-0000-0000-0000-000000000006', '2025-09-30', 'present'),
  ('bb000000-0000-0000-0000-000000000006', '2025-10-07', 'late'),
  ('bb000000-0000-0000-0000-000000000008', '2025-09-10', 'present'),
  ('bb000000-0000-0000-0000-000000000008', '2025-09-17', 'present'),
  ('bb000000-0000-0000-0000-000000000008', '2025-09-24', 'late'),
  ('bb000000-0000-0000-0000-000000000008', '2025-10-01', 'present'),
  ('bb000000-0000-0000-0000-000000000008', '2025-10-08', 'absent'),
  ('bb000000-0000-0000-0000-000000000009', '2025-09-11', 'present'),
  ('bb000000-0000-0000-0000-000000000009', '2025-09-18', 'present'),
  ('bb000000-0000-0000-0000-000000000009', '2025-09-25', 'present'),
  ('bb000000-0000-0000-0000-000000000009', '2025-10-02', 'late'),
  ('bb000000-0000-0000-0000-000000000009', '2025-10-09', 'present'),
  ('bb000000-0000-0000-0000-000000000010', '2025-09-12', 'present'),
  ('bb000000-0000-0000-0000-000000000010', '2025-09-19', 'present'),
  ('bb000000-0000-0000-0000-000000000010', '2025-09-26', 'present'),
  ('bb000000-0000-0000-0000-000000000010', '2025-10-03', 'present'),
  ('bb000000-0000-0000-0000-000000000010', '2025-10-10', 'present'),
  ('bb000000-0000-0000-0000-000000000012', '2025-09-08', 'absent'),
  ('bb000000-0000-0000-0000-000000000012', '2025-09-15', 'absent'),
  ('bb000000-0000-0000-0000-000000000012', '2025-09-22', 'absent'),
  ('bb000000-0000-0000-0000-000000000012', '2025-09-29', 'late'),
  ('bb000000-0000-0000-0000-000000000012', '2025-10-06', 'present'),
  ('bb000000-0000-0000-0000-000000000013', '2025-09-09', 'present'),
  ('bb000000-0000-0000-0000-000000000013', '2025-09-16', 'present'),
  ('bb000000-0000-0000-0000-000000000013', '2025-09-23', 'late'),
  ('bb000000-0000-0000-0000-000000000013', '2025-09-30', 'present'),
  ('bb000000-0000-0000-0000-000000000013', '2025-10-07', 'present'),
  ('bb000000-0000-0000-0000-000000000014', '2025-09-10', 'present'),
  ('bb000000-0000-0000-0000-000000000014', '2025-09-17', 'present'),
  ('bb000000-0000-0000-0000-000000000014', '2025-09-24', 'present'),
  ('bb000000-0000-0000-0000-000000000014', '2025-10-01', 'present'),
  ('bb000000-0000-0000-0000-000000000014', '2025-10-08', 'present'),
  ('bb000000-0000-0000-0000-000000000015', '2025-09-11', 'absent'),
  ('bb000000-0000-0000-0000-000000000015', '2025-09-18', 'absent'),
  ('bb000000-0000-0000-0000-000000000015', '2025-09-25', 'absent'),
  ('bb000000-0000-0000-0000-000000000015', '2025-10-02', 'late'),
  ('bb000000-0000-0000-0000-000000000015', '2025-10-09', 'absent'),
  ('bb000000-0000-0000-0000-000000000016', '2025-09-12', 'present'),
  ('bb000000-0000-0000-0000-000000000016', '2025-09-19', 'late'),
  ('bb000000-0000-0000-0000-000000000016', '2025-09-26', 'absent'),
  ('bb000000-0000-0000-0000-000000000016', '2025-10-03', 'present'),
  ('bb000000-0000-0000-0000-000000000016', '2025-10-10', 'late');