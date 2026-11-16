import os
import shlex
import sys
from pathlib import Path

import pendulum

from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator


PROJECT_DIR = Path(
    os.environ.get(
        "MARKETING_SPEND_PROJECT_DIR",
        Path(__file__).resolve().parents[1],
    )
).resolve()
PYTHON = os.environ.get("MARKETING_SPEND_PYTHON", sys.executable)
DBT = os.environ.get("MARKETING_SPEND_DBT", "dbt")

PROJECT_DIR_COMMAND = shlex.quote(str(PROJECT_DIR))
PYTHON_COMMAND = shlex.quote(PYTHON)
DBT_COMMAND = shlex.quote(DBT)


with DAG(
    dag_id="marketing_spend_control_tower",
    description="Generate, validate, transform and monitor marketing spend.",
    schedule=None,
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 1,
        "retry_delay": pendulum.duration(minutes=1),
        "execution_timeout": pendulum.duration(minutes=10),
    },
    tags=["marketing", "dbt", "duckdb"],
) as dag:

    generate_data = BashOperator(
        task_id="generate_data",
        bash_command=(
            f"cd {PROJECT_DIR_COMMAND} && "
            f"{PYTHON_COMMAND} generator/generate_data.py"
        ),
    )

    ingest_bronze = BashOperator(
        task_id="ingest_bronze",
        bash_command=(
            f"cd {PROJECT_DIR_COMMAND} && "
            f"{PYTHON_COMMAND} pipeline/ingest_bronze.py"
        ),
    )

    validate_bronze = BashOperator(
        task_id="validate_bronze",
        bash_command=(
            f"cd {PROJECT_DIR_COMMAND} && "
            f"{PYTHON_COMMAND} pipeline/validate_bronze.py"
        ),
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            f"cd {PROJECT_DIR_COMMAND} && {DBT_COMMAND} build "
            "--project-dir dbt --profiles-dir dbt"
        ),
    )

    preview_campaign_alerts = BashOperator(
        task_id="preview_campaign_alerts",
        bash_command=(
            f"cd {PROJECT_DIR_COMMAND} && "
            f"{PYTHON_COMMAND} alerts/send_campaign_alerts.py"
        ),
    )

    (
        generate_data
        >> ingest_bronze
        >> validate_bronze
        >> dbt_build
        >> preview_campaign_alerts
    )
