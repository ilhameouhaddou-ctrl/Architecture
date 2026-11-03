-- Gold : indicateurs climatiques annuels par station.
-- Compte les jours "chauds" (tx > 30), "froids" (tn < 0), extrêmes atteints.
-- Base d'évaluation pour la détection d'anomalies et la cohérence spatiale.
COPY (
    SELECT
        o.station_code,
        o.annee,
        COUNT(*) AS nb_jours_mesures,
        SUM(CASE WHEN o.tx > 30 THEN 1 ELSE 0 END) AS nb_jours_tx_sup_30,
        SUM(CASE WHEN o.tx > 35 THEN 1 ELSE 0 END) AS nb_jours_tx_sup_35,
        SUM(CASE WHEN o.tn < 0 THEN 1 ELSE 0 END) AS nb_jours_tn_inf_0,
        SUM(CASE WHEN o.tn < -5 THEN 1 ELSE 0 END) AS nb_jours_tn_inf_moins_5,
        MAX(o.tx) AS tx_max,
        MIN(o.tn) AS tn_min,
        AVG(o.tntxm) AS tntxm_moy,
        s.lon,
        s.lat,
        s.nom AS station_nom,
        s.dep AS departement
    FROM 'data/silver/obs_journaliere.parquet' o
    LEFT JOIN 'data/silver/stations.parquet' s
        ON o.station_code = s.code
    GROUP BY o.station_code, o.annee, s.lon, s.lat, s.nom, s.dep
) TO 'data/gold/indicateurs_annuels.parquet' (FORMAT 'parquet', COMPRESSION 'zstd');
