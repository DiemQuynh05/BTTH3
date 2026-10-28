-- Deterministic sample data for local/demo PostgreSQL databases.
-- Password hashes are placeholders; never use them for production authentication.

INSERT INTO users (id, email, password_hash, full_name, role) VALUES
    (1, 'an.nguyen@example.com', 'demo-hash-an', 'Nguyen Van An', 'applicant'),
    (2, 'binh.tran@example.com', 'demo-hash-binh', 'Tran Thi Binh', 'applicant'),
    (3, 'tuyendung@techcorp.example', 'demo-hash-techcorp', 'TechCorp HR', 'employer'),
    (4, 'hr@dataworks.example', 'demo-hash-dataworks', 'DataWorks HR', 'employer')
ON CONFLICT (id) DO NOTHING;

INSERT INTO applicants (id, user_id, phone, location, headline, summary, cv_url) VALUES
    (1, 1, '0900000001', 'Ha Noi', 'Backend Developer', 'Python backend developer with API experience.', 'https://example.com/cv/an'),
    (2, 2, '0900000002', 'Da Nang', 'Data Analyst', 'Analyst experienced with SQL and dashboards.', 'https://example.com/cv/binh')
ON CONFLICT (id) DO NOTHING;

INSERT INTO employers (id, user_id, company_name, company_size, industry, website) VALUES
    (1, 3, 'TechCorp', '51-200', 'Software', 'https://techcorp.example'),
    (2, 4, 'DataWorks', '11-50', 'Analytics', 'https://dataworks.example')
ON CONFLICT (id) DO NOTHING;

INSERT INTO skills (id, name, category) VALUES
    (1, 'Python', 'Programming'),
    (2, 'PostgreSQL', 'Database'),
    (3, 'SQL', 'Database'),
    (4, 'FastAPI', 'Backend'),
    (5, 'Power BI', 'BI'),
    (6, 'Pandas', 'Data')
ON CONFLICT (id) DO NOTHING;

INSERT INTO job_postings
    (id, employer_id, title, description, location, employment_type, salary_min, salary_max, status, deadline)
VALUES
    (1, 1, 'Backend Python Developer', 'Build and maintain backend services.', 'Ha Noi', 'full-time', 18000000, 30000000, 'open', CURRENT_DATE + 30),
    (2, 2, 'Data Analyst', 'Prepare data and build management dashboards.', 'Da Nang', 'full-time', 15000000, 25000000, 'open', CURRENT_DATE + 45)
ON CONFLICT (id) DO NOTHING;

INSERT INTO applicant_skills (applicant_id, skill_id, proficiency_level, years_experience) VALUES
    (1, 1, 4, 3.0), (1, 2, 4, 2.0), (1, 4, 4, 2.0),
    (2, 3, 5, 4.0), (2, 5, 4, 2.0), (2, 6, 4, 3.0)
ON CONFLICT (applicant_id, skill_id) DO NOTHING;

INSERT INTO job_skills (job_id, skill_id, is_required, minimum_years) VALUES
    (1, 1, TRUE, 2.0), (1, 2, TRUE, 1.0), (1, 4, FALSE, 1.0),
    (2, 3, TRUE, 2.0), (2, 5, TRUE, 1.0), (2, 6, FALSE, 1.0)
ON CONFLICT (job_id, skill_id) DO NOTHING;

INSERT INTO applications (id, applicant_id, job_id, status, matching_score, cover_letter) VALUES
    (1, 1, 1, 'screening', 88.00, 'I have relevant backend experience.'),
    (2, 2, 2, 'interview', 94.00, 'I can build SQL reports and BI dashboards.'),
    (3, 2, 1, 'submitted', NULL, 'I am interested in the backend role.')
ON CONFLICT (id) DO NOTHING;

SELECT setval(pg_get_serial_sequence('users', 'id'), GREATEST((SELECT MAX(id) FROM users), 1));
SELECT setval(pg_get_serial_sequence('applicants', 'id'), GREATEST((SELECT MAX(id) FROM applicants), 1));
SELECT setval(pg_get_serial_sequence('employers', 'id'), GREATEST((SELECT MAX(id) FROM employers), 1));
SELECT setval(pg_get_serial_sequence('skills', 'id'), GREATEST((SELECT MAX(id) FROM skills), 1));
SELECT setval(pg_get_serial_sequence('job_postings', 'id'), GREATEST((SELECT MAX(id) FROM job_postings), 1));
SELECT setval(pg_get_serial_sequence('applications', 'id'), GREATEST((SELECT MAX(id) FROM applications), 1));
