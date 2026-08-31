-- paper_topics relation (spec §7) for the selected papers only.
SELECT
    regexp_extract(wt.work_id, 'W\d+$')  AS paper_id,
    regexp_extract(t.id, 'T\d+$')        AS topic_id,
    t.display_name                       AS topic_name,
    wt.score                             AS score,
    t.subfield_display_name              AS subfield,
    t.field_display_name                 AS field,
    t.domain_display_name                AS domain
FROM openalex.works_topics wt
JOIN openalex.topics t ON wt.topic_id = t.id
JOIN selected s ON regexp_extract(wt.work_id, 'W\d+$') = s.paper_id
ORDER BY paper_id, score DESC, topic_id
