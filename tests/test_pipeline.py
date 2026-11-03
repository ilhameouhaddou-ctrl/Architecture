"""Tests end-to-end sur un sample Bronze local qui joue le rôle de l'API.

On réinjecte la fixture dans data/bronze/, puis on fait tourner Silver + Gold
en pointant les SQL vers des chemins temporaires. On vérifie le compte de
lignes et la détection d'épisode caniculaire sur S1 (4 jours > 30°C).
"""
from pathlib import Path

import duckdb

FIXTURE = Path(__file__).parent / "fixtures" / "sample_obs.json"


def _silver_sql(bronze_glob: str, out: Path) -> str:
    return f"""
    COPY (
        WITH pages AS (
            SELECT UNNEST(mesures) AS m
            FROM read_json_auto('{bronze_glob}', maximum_object_size => 268435456)
        )
        SELECT
            m.station_code,
            CAST(m.date AS DATE) AS date,
            CAST(strftime(CAST(m.date AS DATE), '%Y') AS INTEGER) AS annee,
            m.tn, m.tx, m.tntxm
        FROM pages
    ) TO '{out}' (FORMAT 'parquet', COMPRESSION 'zstd');
    """


def _gold_canicule_sql(silver_parquet: Path, out: Path) -> str:
    return f"""
    COPY (
        WITH chauds AS (
            SELECT station_code, date, tx,
                   date - CAST(ROW_NUMBER() OVER (
                     PARTITION BY station_code ORDER BY date
                   ) AS INTEGER) AS grp
            FROM '{silver_parquet}'
            WHERE tx > 30
        ),
        episodes AS (
            SELECT station_code, MIN(date) debut, MAX(date) fin,
                   COUNT(*) duree, MAX(tx) tx_max
            FROM chauds GROUP BY station_code, grp
            HAVING COUNT(*) >= 3
        )
        SELECT * FROM episodes
    ) TO '{out}' (FORMAT 'parquet', COMPRESSION 'zstd');
    """


def test_silver_obs_from_envelope(tmp_path: Path) -> None:
    # Simule une page bronze
    bronze_dir = tmp_path / "bronze"
    bronze_dir.mkdir()
    (bronze_dir / "page-00001.json").write_bytes(FIXTURE.read_bytes())

    silver_out = tmp_path / "silver" / "obs.parquet"
    silver_out.parent.mkdir()

    con = duckdb.connect(":memory:")
    con.execute(_silver_sql(str(bronze_dir / "page-*.json"), silver_out))

    rows = con.sql(f"SELECT COUNT(*) FROM read_parquet('{silver_out}')").fetchone()
    assert rows[0] == 10


def test_gold_canicule_detection(tmp_path: Path) -> None:
    bronze_dir = tmp_path / "bronze"
    bronze_dir.mkdir()
    (bronze_dir / "page-00001.json").write_bytes(FIXTURE.read_bytes())

    silver = tmp_path / "obs.parquet"
    gold = tmp_path / "canicules.parquet"

    con = duckdb.connect(":memory:")
    con.execute(_silver_sql(str(bronze_dir / "page-*.json"), silver))
    con.execute(_gold_canicule_sql(silver, gold))

    # S1 a 4 jours consécutifs > 30 (2024-07-01..04), S2 n'en a qu'un.
    episodes = con.sql(
        f"SELECT station_code, duree FROM '{gold}' ORDER BY station_code"
    ).fetchall()
    assert episodes == [("S1", 4)]
