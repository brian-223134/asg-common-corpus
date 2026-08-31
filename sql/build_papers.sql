-- Final selection from candidates + temporal resolution (docs/decisions.md D2). Deterministic order.
SELECT c.* EXCLUDE (_valid, _retracted, _paratext) REPLACE (
    CASE WHEN c.arxiv_id IS NOT NULL THEN 'arxiv:' || c.arxiv_id END AS version_family_id,
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
-- §18.3 dedup: 같은 arXiv 논문이 복수 OpenAlex work로 존재(preprint+출판본 등, 6.6%) →
-- citation 최다, 동률이면 paper_id 순으로 1건만 채택. arxiv_id 없는 행은 각자 유지.
QUALIFY row_number() OVER (
    PARTITION BY coalesce(c.arxiv_id, c.paper_id)
    ORDER BY c.citation_count DESC NULLS LAST, c.paper_id
) = 1
ORDER BY paper_id
