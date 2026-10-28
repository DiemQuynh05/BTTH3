-- Views for TV2 (AI matching) and TV3 (BI reporting).

CREATE OR REPLACE VIEW ai_candidate_job_skill_match AS
WITH required AS (
    SELECT job_id, COUNT(*) AS required_skill_count
    FROM job_skills
    WHERE is_required
    GROUP BY job_id
),
matched AS (
    SELECT
        a.id AS applicant_id,
        j.id AS job_id,
        COUNT(*) FILTER (
            WHERE ask.years_experience >= COALESCE(js.minimum_years, 0)
        ) AS matched_skill_count,
        COUNT(*) AS candidate_skill_count
    FROM applicants a
    CROSS JOIN job_postings j
    JOIN job_skills js ON js.job_id = j.id AND js.is_required
    LEFT JOIN applicant_skills ask
        ON ask.applicant_id = a.id AND ask.skill_id = js.skill_id
    GROUP BY a.id, j.id
)
SELECT
    m.applicant_id,
    m.job_id,
    r.required_skill_count,
    m.matched_skill_count,
    ROUND(100.0 * m.matched_skill_count / NULLIF(r.required_skill_count, 0), 2) AS skill_match_score,
    j.status AS job_status
FROM matched m
JOIN required r ON r.job_id = m.job_id
JOIN job_postings j ON j.id = m.job_id;

CREATE OR REPLACE VIEW bi_application_kpi_daily AS
SELECT
    DATE(a.created_at) AS application_date,
    j.id AS job_id,
    j.title,
    e.company_name,
    COUNT(*) AS total_applications,
    COUNT(*) FILTER (WHERE a.status = 'screening') AS screening_count,
    COUNT(*) FILTER (WHERE a.status = 'interview') AS interview_count,
    COUNT(*) FILTER (WHERE a.status = 'hired') AS hired_count,
    COUNT(*) FILTER (WHERE a.status = 'rejected') AS rejected_count,
    ROUND(AVG(a.matching_score), 2) AS average_matching_score
FROM applications a
JOIN job_postings j ON j.id = a.job_id
JOIN employers e ON e.id = j.employer_id
GROUP BY DATE(a.created_at), j.id, j.title, e.company_name;

CREATE OR REPLACE VIEW bi_job_funnel AS
SELECT
    j.id AS job_id,
    j.title,
    e.company_name,
    j.status AS job_status,
    COUNT(a.id) AS applications,
    COUNT(a.id) FILTER (WHERE a.status IN ('screening', 'interview', 'offered', 'hired')) AS progressed,
    COUNT(a.id) FILTER (WHERE a.status = 'hired') AS hired,
    ROUND(100.0 * COUNT(a.id) FILTER (WHERE a.status = 'hired') / NULLIF(COUNT(a.id), 0), 2) AS hire_rate_percent
FROM job_postings j
JOIN employers e ON e.id = j.employer_id
LEFT JOIN applications a ON a.job_id = j.id
GROUP BY j.id, j.title, e.company_name, j.status;
