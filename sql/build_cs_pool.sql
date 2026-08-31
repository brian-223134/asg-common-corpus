-- work_ids with at least one topic in the target field
CREATE OR REPLACE TEMP TABLE pool AS
SELECT DISTINCT wt.work_id
FROM openalex.works_topics wt
JOIN openalex.topics t ON wt.topic_id = t.id
WHERE t.field_display_name = $field;
