-- Final selection from candidates + temporal resolution (docs/decisions.md D2). Deterministic order.
SELECT c.* EXCLUDE (_valid, _retracted, _paratext) REPLACE (
    CASE
        WHEN d.snap_date IS NOT NULL AND date_trunc('month', d.snap_date) = d.id_month THEN d.snap_date
        WHEN d.id_month IS NOT NULL THEN d.id_month
        ELSE c.publication_date
    END AS first_public_date,
    CASE
        WHEN d.snap_date IS NOT NULL AND date_trunc('month', d.snap_date) = d.id_month THEN 'arxiv_snapshot'
        WHEN d.id_month IS NOT NULL THEN 'arxiv_id'
        WHEN c.publication_date IS NOT NULL THEN 'openalex'
        ELSE 'unresolved'
    END AS date_source,
    CASE
        WHEN d.snap_date IS NOT NULL AND date_trunc('month', d.snap_date) = d.id_month THEN 'day'
        WHEN d.id_month IS NOT NULL THEN 'month'
        WHEN c.publication_date IS NOT NULL THEN 'day'
        ELSE 'unknown'
    END AS date_precision
)
FROM candidates c
LEFT JOIN arxiv_dates d ON c.paper_id = d.paper_id
WHERE ($require_valid IS FALSE OR _valid)
  AND ($language IS NULL OR c.language = $language)
  AND ($exclude_retracted IS FALSE OR NOT _retracted)
  AND ($exclude_paratext IS FALSE OR NOT _paratext)
  AND ($require_arxiv IS FALSE OR c.arxiv_id IS NOT NULL)
ORDER BY paper_id
