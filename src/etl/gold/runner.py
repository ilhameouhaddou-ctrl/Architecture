from pathlib import Path

import duckdb

SQL_DIR = Path(__file__).parent / "sql"


def list_sql_files() -> list[Path]:
    return sorted(SQL_DIR.glob("*.sql"))


def run_sql_file(sql_path: Path) -> None:
    con = duckdb.connect(":memory:")
    try:
        con.execute(sql_path.read_text(encoding="utf-8"))
    finally:
        con.close()


def run_all(filter_name: str | None = None) -> list[Path]:
    executed: list[Path] = []
    for sql in list_sql_files():
        if filter_name and sql.stem != filter_name:
            continue
        run_sql_file(sql)
        executed.append(sql)
    return executed
