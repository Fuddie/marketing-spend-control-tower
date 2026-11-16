from pathlib import Path

import duckdb


TABLES = (
    "fct_campaign_daily_performance",
    "mart_campaign_daily_pacing",
    "mart_campaign_alerts",
)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    database = root / "warehouse" / "marketing_spend.duckdb"
    output_dir = root / "warehouse" / "wren_export"

    if not database.exists():
        raise FileNotFoundError(f"Warehouse not found: {database}")

    output_dir.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(database), read_only=True)

    try:
        for table in TABLES:
            destination = (output_dir / f"{table}.parquet").as_posix()
            row_count = connection.execute(
                f"SELECT COUNT(*) FROM gold.{table}"
            ).fetchone()[0]

            connection.execute(
                f"COPY gold.{table} TO '{destination}' "
                "(FORMAT PARQUET, OVERWRITE_OR_IGNORE TRUE)"
            )
            print(f"Exported {table}: {row_count} rows")
    finally:
        connection.close()


if __name__ == "__main__":
    main()

