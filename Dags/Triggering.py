from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.microsoft.azure.hooks.data_lake import AzureDataLakeStorageV2Hook
from airflow.providers.databricks.operators.databricks import DatabricksRunNowOperator
from airflow.exceptions import AirflowException

logger = logging.getLogger(__name__)

# --- Configuration (pull from Airflow Variables / env, not hardcoded) ---
ADLS_CONN_ID = "adls_conn"
DATABRICKS_CONN_ID = "databricks_default"
RAW_DATA_PATH = "/opt/airflow/dags/data/raw"
FILE_SYSTEM_NAME = "bronzeshippingdata"
SILVER_JOB_ID = Variable.get("silver_databricks_job_id")

default_args = {
    "owner": "data-engineering",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
    "execution_timeout": timedelta(minutes=30),
    "email_on_failure": True,
    "email": ["data-alerts@yourcompany.com"],
}


def upload_directory_to_adls(**context) -> None:
    """Upload all files in the raw data folder to ADLS under a date-partitioned path.

    Uses the DAG's logical date (not wall-clock time) so retries and
    backfills are idempotent.
    """
    hook = AzureDataLakeStorageV2Hook(adls_conn_id=ADLS_CONN_ID)

    # logical date -> deterministic partition, safe for retries/backfill
    date_folder = context["ds"]  # 'YYYY-MM-DD'
    local_folder = Path(RAW_DATA_PATH)

    if not local_folder.exists():
        raise AirflowException(f"Raw data path does not exist: {local_folder}")

    files = [f for f in local_folder.iterdir() if f.is_file()]
    if not files:
        # decide: is an empty folder an error or a no-op? Be explicit.
        raise AirflowException(f"No files found to upload in {local_folder}")

    logger.info("Uploading %d file(s) to bronze/%s", len(files), date_folder)

    uploaded = 0
    for file in files:
        try:
            hook.upload_file_to_directory(
                file_system_name=FILE_SYSTEM_NAME,
                directory_name=f"bronze/{date_folder}",
                file_name=file.name,
                file_path=str(file),
                overwrite=True,
            )
            uploaded += 1
            logger.info("Uploaded %s", file.name)
        except Exception:
            logger.exception("Failed to upload %s", file.name)
            raise  # fail the task so retries kick in

    logger.info("Upload complete: %d/%d files", uploaded, len(files))


with DAG(
    dag_id="shipping_bronze_ingestion",
    description="Ingest raw shipping orders, land in ADLS bronze, trigger silver job.",
    start_date=datetime(2026, 4, 13),
    schedule="@daily",
    catchup=False,
    default_args=default_args,
    max_active_runs=1,
    tags=["shipping", "bronze", "ingestion"],
) as dag:

    generate_orders = BashOperator(
        task_id="generate_shipment_orders",
        bash_command="python /opt/airflow/dags/shippement_orders.py",
        doc_md="Runs the source script that produces raw shipment order files.",
    )

    upload_to_adls = PythonOperator(
        task_id="upload_raw_to_adls_bronze",
        python_callable=upload_directory_to_adls,
        doc_md="Uploads raw files to the ADLS bronze container, date-partitioned.",
    )

    run_silver_job = DatabricksRunNowOperator(
        task_id="run_silver_transformation",
        databricks_conn_id=DATABRICKS_CONN_ID,
        job_id=SILVER_JOB_ID,
    )

    generate_orders >> upload_to_adls >> run_silver_job
