-- Silver : observations journalières consolidées à partir des pages Bronze
-- de /dataclimat/quotidienne. Chaque page Bronze = JSON {mesures: [...]}.
-- On déplie `mesures` et on type la date pour les requêtes temporelles.
COPY (
    WITH pages AS (
        SELECT UNNEST(mesures) AS m
        FROM read_json_auto(
            'data/bronze/dataclimat_quotidienne/page-*.json',
            maximum_object_size => 268435456
        )
    )
    SELECT
        m.station_code,
        CAST(m.date AS DATE) AS date,
        CAST(strftime(CAST(m.date AS DATE), '%Y') AS INTEGER) AS annee,
        m.tn,
        m.tx,
        m.tntxm
    FROM pages
) TO 'data/silver/obs_journaliere.parquet' (FORMAT 'parquet', COMPRESSION 'zstd');
