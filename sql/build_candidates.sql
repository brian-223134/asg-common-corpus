-- Single pass over openalex.works: canonical columns + filter flags for the pooled works.
-- Filters/audit run on this temp table so works.parquet (135 GB) is scanned exactly once.
CREATE OR REPLACE TEMP TABLE candidates AS
SELECT
    regexp_extract(w.id, 'W\d+$')                       AS paper_id,
    regexp_extract(w.id, 'W\d+$')                       AS openalex_id,
    lower(replace(w.doi, 'https://doi.org/', ''))       AS doi,
    a.arxiv_id                                          AS arxiv_id,
    CAST(NULL AS VARCHAR)                               AS version_family_id,
    w.title                                             AS title,
    w.abstract                                          AS abstract,
    w.language                                          AS language,
    CAST(NULL AS DATE)                                  AS first_public_date,
    TRY_CAST(w.publication_date AS DATE)               AS publication_date,  -- parquet stores it as VARCHAR
    'unresolved'                                        AS date_source,
    'unknown'                                           AS date_precision,
    w.type                                              AS paper_type,
    w.publication_year                                  AS year,
    w.cited_by_count                                    AS citation_count,
    'openalex'                                          AS citation_source,
    CAST($citation_snapshot AS DATE)                    AS citation_snapshot_date,
    'openalex'                                          AS metadata_source,
    $source_snapshot                                    AS source_snapshot,
    w.has_fulltext                                      AS fulltext_available_hint,
    w.valid_title_abstract                              AS _valid,
    w.is_retracted                                      AS _retracted,
    w.is_paratext                                       AS _paratext
FROM openalex.works w
JOIN pool p ON w.id = p.work_id
LEFT JOIN arxiv_map a ON w.id = a.work_id;
