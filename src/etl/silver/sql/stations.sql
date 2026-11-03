-- Silver : stations_ref aplaties à partir du GeoJSON FeatureCollection Bronze.
-- Une ligne par station, lon/lat en colonnes de premier niveau.
COPY (
    WITH f AS (
        SELECT UNNEST(features) AS feat
        FROM read_json_auto(
            'data/bronze/stations_ref.json',
            maximum_object_size => 268435456
        )
    ),
    g AS (
        SELECT
            feat.geometry.coordinates[1] AS lon,
            feat.geometry.coordinates[2] AS lat,
            feat.properties AS p
        FROM f
    )
    SELECT lon, lat, p.* FROM g
) TO 'data/silver/stations.parquet' (FORMAT 'parquet', COMPRESSION 'zstd');
