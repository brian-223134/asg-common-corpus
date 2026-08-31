-- Final selection from candidates (see build_candidates.sql). Deterministic order.
SELECT * EXCLUDE (_valid, _retracted, _paratext)
FROM candidates
WHERE ($require_valid IS FALSE OR _valid)
  AND ($language IS NULL OR language = $language)
  AND ($exclude_retracted IS FALSE OR NOT _retracted)
  AND ($exclude_paratext IS FALSE OR NOT _paratext)
  AND ($require_arxiv IS FALSE OR arxiv_id IS NOT NULL)
ORDER BY paper_id
