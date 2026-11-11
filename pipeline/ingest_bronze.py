"""Load daily landing CSV files into DuckDB Bronze tables."""

import argparse
from datetime import date
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LANDING_ROOT = PROJECT_ROOT / "data" / "landing"

WAREHOUSE_PATH = (
    PROJECT_ROOT
    / "warehouse"
    / "marketing_spend.duckdb"
)

SOURCE_TABLES = {
    "campaigns": {
        "file_name": "campaigns.csv",
        "primary_key": "campaign_id",
    },
    "campaign_budget_changes": {
        "file_name": "campaign_budget_changes.csv",
        "primary_key": "budget_change_id",
    },
    "ad_spend_daily": {
        "file_name": "ad_spend_daily.csv",
        "primary_key": "spend_record_id",
    },
    "orders": {
        "file_name": "orders.csv",
        "primary_key": "order_id",
    },
    "attribution_events": {
        "file_name": "attribution_events.csv",
        "primary_key": "attribution_id",
    },
    "refunds": {
        "file_name": "refunds.csv",
        "primary_key": "refund_id",
    },
}


def parse_arguments():
    """Read the requested extract date from the command line."""

    parser = argparse.ArgumentParser(
        description=(
            "Load daily landing CSV files into "
            "DuckDB Bronze tables."
        )
    )

    parser.add_argument(
        "--extract-date",
        type=date.fromisoformat,
        default=date.today(),
        help=(
            "Landing partition date in YYYY-MM-DD format. "
            "Defaults to today's date."
        ),
    )

    return parser.parse_args()

def create_bronze_tables(connection):
    """Create the Bronze schema and source tables."""

    connection.execute(
        "CREATE SCHEMA IF NOT EXISTS bronze"
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS bronze.campaigns (
            campaign_id VARCHAR PRIMARY KEY,
            campaign_name VARCHAR NOT NULL,
            channel VARCHAR NOT NULL,
            objective VARCHAR NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            status VARCHAR NOT NULL,
            created_at TIMESTAMP NOT NULL,
            source_updated_at TIMESTAMP NOT NULL,
            extract_date DATE NOT NULL,
            ingested_at TIMESTAMP NOT NULL,
            source_file VARCHAR NOT NULL
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS
        bronze.campaign_budget_changes (
            budget_change_id VARCHAR PRIMARY KEY,
            campaign_id VARCHAR NOT NULL,
            budget_month DATE NOT NULL,
            budget_amount DECIMAL(18, 2) NOT NULL,
            currency_code VARCHAR NOT NULL,
            effective_at TIMESTAMP NOT NULL,
            change_reason VARCHAR NOT NULL,
            source_updated_at TIMESTAMP NOT NULL,
            extract_date DATE NOT NULL,
            ingested_at TIMESTAMP NOT NULL,
            source_file VARCHAR NOT NULL
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS bronze.ad_spend_daily (
            spend_record_id VARCHAR PRIMARY KEY,
            campaign_id VARCHAR NOT NULL,
            spend_date DATE NOT NULL,
            spend_amount DECIMAL(18, 2) NOT NULL,
            impressions BIGINT NOT NULL,
            clicks BIGINT NOT NULL,
            platform_conversions BIGINT NOT NULL,
            currency_code VARCHAR NOT NULL,
            source_updated_at TIMESTAMP NOT NULL,
            extract_date DATE NOT NULL,
            ingested_at TIMESTAMP NOT NULL,
            source_file VARCHAR NOT NULL
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS bronze.orders (
            order_id VARCHAR PRIMARY KEY,
            customer_id VARCHAR NOT NULL,
            order_timestamp TIMESTAMP NOT NULL,
            order_status VARCHAR NOT NULL,
            gross_revenue DECIMAL(18, 2) NOT NULL,
            currency_code VARCHAR NOT NULL,
            source_updated_at TIMESTAMP NOT NULL,
            extract_date DATE NOT NULL,
            ingested_at TIMESTAMP NOT NULL,
            source_file VARCHAR NOT NULL
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS
        bronze.attribution_events (
            attribution_id VARCHAR PRIMARY KEY,
            order_id VARCHAR NOT NULL,
            campaign_id VARCHAR NOT NULL,
            touchpoint_timestamp TIMESTAMP NOT NULL,
            attribution_model VARCHAR NOT NULL,
            attribution_weight DECIMAL(5, 4) NOT NULL,
            source_updated_at TIMESTAMP NOT NULL,
            extract_date DATE NOT NULL,
            ingested_at TIMESTAMP NOT NULL,
            source_file VARCHAR NOT NULL
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS bronze.refunds (
            refund_id VARCHAR PRIMARY KEY,
            order_id VARCHAR NOT NULL,
            refund_timestamp TIMESTAMP NOT NULL,
            refund_amount DECIMAL(18, 2) NOT NULL,
            refund_status VARCHAR NOT NULL,
            refund_reason VARCHAR NOT NULL,
            currency_code VARCHAR NOT NULL,
            source_updated_at TIMESTAMP NOT NULL,
            extract_date DATE NOT NULL,
            ingested_at TIMESTAMP NOT NULL,
            source_file VARCHAR NOT NULL
        )
        """
    )

def resolve_source_files(extract_date):
    """Locate every CSV required for one extract date."""

    source_files = {}
    missing_files = []

    partition_name = (
        f"extract_date={extract_date.isoformat()}"
    )

    for table_name, config in SOURCE_TABLES.items():
        source_path = (
            LANDING_ROOT
            / table_name
            / partition_name
            / config["file_name"]
        )

        if not source_path.is_file():
            missing_files.append(source_path)
            continue

        source_files[table_name] = source_path

    if missing_files:
        missing_list = "\n".join(
            f"- {path}"
            for path in missing_files
        )

        raise FileNotFoundError(
            "The following source files are missing:\n"
            f"{missing_list}"
        )

    return source_files

def upsert_source_file(
    connection,
    table_name,
    source_path,
    extract_date,
):
    """Insert new records and update newer source versions."""

    primary_key = SOURCE_TABLES[
        table_name
    ]["primary_key"]

    table_reference = f"bronze.{table_name}"

    table_columns = connection.execute(
        f"PRAGMA table_info('{table_reference}')"
    ).fetchall()

    column_names = [
        column[1]
        for column in table_columns
    ]

    update_columns = [
        column_name
        for column_name in column_names
        if column_name != primary_key
    ]

    update_assignments = ",\n".join(
        (
            f"{column_name} = "
            f"source.{column_name}"
        )
        for column_name in update_columns
    )

    insert_columns = ", ".join(column_names)

    insert_values = ", ".join(
        f"source.{column_name}"
        for column_name in column_names
    )

    safe_source_path = (
        source_path
        .resolve()
        .as_posix()
        .replace("'", "''")
    )

    safe_source_file = (
        str(source_path.resolve())
        .replace("'", "''")
    )

    staging_view = f"staging_{table_name}"

    connection.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW {staging_view} AS
        SELECT
            *,
            DATE '{extract_date.isoformat()}'
                AS extract_date,
            CURRENT_TIMESTAMP AS ingested_at,
            '{safe_source_file}' AS source_file
        FROM read_csv_auto(
            '{safe_source_path}',
            header = true
        )
        """
    )

    source_count = connection.execute(
        f"SELECT COUNT(*) FROM {staging_view}"
    ).fetchone()[0]

    connection.execute(
        f"""
        MERGE INTO {table_reference} AS target
        USING {staging_view} AS source
            ON target.{primary_key}
                = source.{primary_key}

        WHEN MATCHED
            AND source.source_updated_at
                >= target.source_updated_at
        THEN UPDATE SET
            {update_assignments}

        WHEN NOT MATCHED
        THEN INSERT ({insert_columns})
        VALUES ({insert_values})
        """
    )

    return source_count

def main():
    """Load one complete daily extract into Bronze."""

    arguments = parse_arguments()
    extract_date = arguments.extract_date

    source_files = resolve_source_files(
        extract_date=extract_date
    )

    WAREHOUSE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = duckdb.connect(
        str(WAREHOUSE_PATH)
    )

    load_results = []

    try:
        create_bronze_tables(
            connection=connection
        )

        connection.execute(
            "BEGIN TRANSACTION"
        )

        for table_name in SOURCE_TABLES:
            source_count = upsert_source_file(
                connection=connection,
                table_name=table_name,
                source_path=source_files[table_name],
                extract_date=extract_date,
            )

            final_count = connection.execute(
                f"""
                SELECT COUNT(*)
                FROM bronze.{table_name}
                """
            ).fetchone()[0]

            load_results.append(
                {
                    "table_name": table_name,
                    "source_count": source_count,
                    "final_count": final_count,
                }
            )

        connection.execute("COMMIT")

    except Exception:
        connection.execute("ROLLBACK")
        raise

    finally:
        connection.close()

    print(
        "Bronze ingestion completed for "
        f"{extract_date.isoformat()}."
    )

    for result in load_results:
        print(
            f"{result['table_name']}: "
            f"{result['source_count']} source rows, "
            f"{result['final_count']} Bronze rows"
        )

    print(f"Warehouse: {WAREHOUSE_PATH}")


if __name__ == "__main__":
    main()

    
    