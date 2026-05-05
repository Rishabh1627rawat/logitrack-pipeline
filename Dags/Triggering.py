from airflow import DAG
from datetime import datetime
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.microsoft.azure.hooks.data_lake import AzureDataLakeStorageV2Hook
from airflow.providers.standard.operators.python import PythonOperator
from pathlib import Path
from airflow.providers.databricks.operators.databricks import DatabricksRunNowOperator


def upload_directorty_adls():
    hook = AzureDataLakeStorageV2Hook(adls_conn_id= 'adls_conn')
    local_folder = '/opt/airflow/dags/data/raw'
    date_folder = datetime.now().strftime("%Y-%m-%d")
    
    
    for files in Path(local_folder).iterdir():
        if files.is_file():
            hook.upload_file_to_directory( 
                file_system_name = "bronzeshippingdata",
                directory_name = f"bronze/{date_folder}",
                file_name = files.name,
                file_path = str(files),
                overwrite = True
)

with DAG(
    dag_id='my_first_dag',
    start_date=datetime(2026, 4, 13),
    schedule='@daily',
    catchup=False
) as dag:

    run_this = BashOperator(
        task_id='run_this_task',
        bash_command='python /opt/airflow/dags/shippement_orders.py',
    )

    upload_data = PythonOperator(
    task_id= 'upload_the_data',
    python_callable= upload_directorty_adls,

    )

    run_databricks_notebook = DatabricksRunNowOperator(
    task_id = 'run_silver_job',
    databricks_conn_id = 'databricks_default',
    job_id = 835879684233382,

    )
run_this >> upload_data >> run_databricks_notebook
