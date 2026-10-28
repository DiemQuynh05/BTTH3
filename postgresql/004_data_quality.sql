-- Checklist 4 and 7: every query should return zero rows.

-- Duplicate business keys (should be prevented by UNIQUE constraints).
SELECT LOWER(TRIM(email)) AS normalized_email, COUNT(*)
FROM users
GROUP BY LOWER(TRIM(email))
HAVING COUNT(*) > 1;

SELECT LOWER(TRIM(name)) AS normalized_skill_name, COUNT(*)
FROM skills
GROUP BY LOWER(TRIM(name))
HAVING COUNT(*) > 1;

-- Required fields and invalid numeric ranges.
SELECT id, 'user_missing_required_field' AS issue FROM users
WHERE NULLIF(TRIM(email), '') IS NULL OR NULLIF(TRIM(full_name), '') IS NULL
UNION ALL
SELECT id, 'job_invalid_salary' FROM job_postings
WHERE salary_min < 0 OR salary_max < 0 OR salary_min > salary_max
UNION ALL
SELECT applicant_id, 'applicant_skill_invalid_experience' FROM applicant_skills
WHERE years_experience < 0 OR proficiency_level NOT BETWEEN 1 AND 5
UNION ALL
SELECT job_id, 'job_skill_invalid_minimum_years' FROM job_skills
WHERE minimum_years < 0
UNION ALL
SELECT id, 'application_invalid_score' FROM applications
WHERE matching_score < 0 OR matching_score > 100;

-- Orphan checks (should be redundant with foreign keys, but useful for Checklist 5).
SELECT a.id AS application_id
FROM applications a
LEFT JOIN applicants p ON p.id = a.applicant_id
LEFT JOIN job_postings j ON j.id = a.job_id
WHERE p.id IS NULL OR j.id IS NULL;

-- Reconciliation counts for a test report.
SELECT 'users' AS entity, COUNT(*) AS row_count FROM users
UNION ALL SELECT 'applicants', COUNT(*) FROM applicants
UNION ALL SELECT 'employers', COUNT(*) FROM employers
UNION ALL SELECT 'skills', COUNT(*) FROM skills
UNION ALL SELECT 'job_postings', COUNT(*) FROM job_postings
UNION ALL SELECT 'applications', COUNT(*) FROM applications;
