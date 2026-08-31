-- one arXiv base id per pooled work, from location URLs; version stripped, archive lowercased.
-- deterministic pick: min(base id); conflicts counted for the audit.
CREATE OR REPLACE TEMP TABLE arxiv_map AS
WITH hits AS (
    SELECT l.work_id,
           lower(regexp_extract(
               coalesce(l.pdf_url, '') || ' ' || coalesce(l.landing_page_url, ''),
               'arxiv\.org/(?:abs|pdf)/((?:\d{4}\.\d{4,5}|[a-zA-Z-]+(?:\.[a-zA-Z]{2})?/\d{7}))',
               1)) AS arxiv_id
    FROM openalex.works_locations l
    JOIN pool p ON l.work_id = p.work_id
)
SELECT work_id, min(arxiv_id) AS arxiv_id, count(DISTINCT arxiv_id) AS n_distinct_ids
FROM hits
WHERE arxiv_id <> ''
GROUP BY work_id;
