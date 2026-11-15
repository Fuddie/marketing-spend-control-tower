import pendulum

from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator


PROJECT_DIR = (
    "/mnt/c/Users/HP/OneDrive/Documents/"
    "marketing-spend-control-tower"
)
PYTHON = "/home/fuad/marketing-spend-venv/bin/python"
DBT = "/home/fuad/marketing-spend-venv/bin/dbt"


with DAG(
    dag_id="marketing_spend_control_tower",
    description="Generate, validate, transform and monitor marketing spend.",
    schedule=None,
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["marketing", "dbt", "duckdb"],
) as dag:

    generate_data = BashOperator(
        task_id="generate_data",
        bash_command=f"cd '{PROJECT_DIR}' && {PYTHON} generator/generate_data.py",
    )

    ingest_bronze = BashOperator(
        task_id="ingest_bronze",
        bash_command=f"cd '{PROJECT_DIR}' && {PYTHON} pipeline/ingest_bronze.py",
    )

    validate_bronze = BashOperator(
        task_id="validate_bronze",
        bash_command=f"cd '{PROJECT_DIR}' && {PYTHON} pipeline/validate_bronze.py",
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            f"cd '{PROJECT_DIR}' && {DBT} build "
            "--project-dir dbt --profiles-dir dbt"
        ),
    )

    preview_campaign_alerts = BashOperator(
        task_id="preview_campaign_alerts",
        bash_command=(
            f"cd '{PROJECT_DIR}' && "
            f"{PYTHON} alerts/send_campaign_alerts.py"
        ),
    )

    (
        generate_data
        >> ingest_bronze
        >> validate_bronze
        >> dbt_build
        >> preview_campaign_alerts
    )
