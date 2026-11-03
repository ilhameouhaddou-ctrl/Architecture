-- Gold : catalogue d'épisodes caniculaires détectés.
-- Définition simple : >=3 jours consécutifs avec tx > 30°C sur la même station.
-- Technique gaps-and-islands : date - row_number donne un groupe stable par run.
-- Ce catalogue est le produit cible mentionné dans la slide de cadrage
-- (variante "Épisodes extrêmes") et servira de base à la détection IA.
COPY (
    WITH chauds AS (
        SELECT
            station_code,
            date,
            tx,
            date - CAST(
                ROW_NUMBER() OVER (PARTITION BY station_code ORDER BY date)
                AS INTEGER
            ) AS grp
        FROM 'data/silver/obs_journaliere.parquet'
        WHERE tx > 30
    ),
    episodes AS (
        SELECT
            station_code,
            grp,
            MIN(date) AS date_debut,
            MAX(date) AS date_fin,
            COUNT(*) AS duree_jours,
            MAX(tx) AS tx_max,
            AVG(tx) AS tx_moy
        FROM chauds
        GROUP BY station_code, grp
        HAVING COUNT(*) >= 3
    )
    SELECT
        ROW_NUMBER() OVER (ORDER BY e.station_code, e.date_debut) AS event_id,
        e.station_code,
        'canicule' AS type_evt,
        e.date_debut,
        e.date_fin,
        e.duree_jours,
        e.tx_max,
        e.tx_moy,
        s.lon,
        s.lat,
        s.nom AS station_nom,
        s.dep AS departement
    FROM episodes e
    LEFT JOIN 'data/silver/stations.parquet' s
        ON e.station_code = s.code
    ORDER BY e.date_debut, e.station_code
) TO 'data/gold/evenements_canicule.parquet' (FORMAT 'parquet', COMPRESSION 'zstd');
