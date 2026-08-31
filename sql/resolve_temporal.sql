-- D2: deterministic first_public_date sources for arXiv-backed candidates.
-- id_month = year-month encoded in the arXiv id (v1 announcement month, exact by construction).
-- snap_date qualifies as a day-precision v1 date only when it falls in that same month.
CREATE OR REPLACE TEMP TABLE arxiv_dates AS
WITH snap AS (
    SELECT base_id, min(date) AS snap_date FROM arxiv_snapshot.papers GROUP BY base_id
)
SELECT
    c.paper_id,
    CASE
        WHEN regexp_matches(c.arxiv_id, '^\d{4}\.')
        THEN make_date(2000 + CAST(substr(c.arxiv_id, 1, 2) AS INT), CAST(substr(c.arxiv_id, 3, 2) AS INT), 1)
        ELSE make_date(
            CASE WHEN CAST(regexp_extract(c.arxiv_id, '/(\d{2})', 1) AS INT) >= 91 THEN 1900 ELSE 2000 END
                + CAST(regexp_extract(c.arxiv_id, '/(\d{2})', 1) AS INT),
            CAST(regexp_extract(c.arxiv_id, '/\d{2}(\d{2})', 1) AS INT), 1)
    END AS id_month,
    s.snap_date
FROM candidates c
LEFT JOIN snap s ON c.arxiv_id = s.base_id
WHERE c.arxiv_id IS NOT NULL;
