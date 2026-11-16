from pathlib import Path

import duckdb


TABLES = (
    "fct_campaign_daily_performance",
    "mart_campaign_daily_pacing",
    "mart_campaign_alerts",
)


def sql_path(path: Path) -> str:
    return path.as_posix().replace("'", "''")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    export_dir = root / "warehouse" / "wren_export"
    snapshot_dir = root / "warehouse" / "wren_warehouse"
    database = snapshot_dir / "marketing_spend.duckdb"

    missing = [
        export_dir / f"{table}.parquet"
        for table in TABLES
        if not (export_dir / f"{table}.parquet").exists()
    ]
    if missing:
        missing_list = "\n".join(str(path) for path in missing)
        raise FileNotFoundError(f"Missing Parquet exports:\n{missing_list}")

    snapshot_dir.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(database))

    try:
        connection.execute("BEGIN TRANSACTION")
        connection.execute("CREATE SCHEMA IF NOT EXISTS gold")

        for table in TABLES:
            source = sql_path(export_dir / f"{table}.parquet")
            connection.execute(
                f"CREATE OR REPLACE TABLE gold.{table} "
                f"AS SELECT * FROM read_parquet('{source}')"
            )
            row_count = connection.execute(
                f"SELECT COUNT(*) FROM gold.{table}"
            ).fetchone()[0]
            print(f"Loaded {table}: {row_count} rows")

        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
