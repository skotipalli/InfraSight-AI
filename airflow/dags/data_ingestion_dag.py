"""
InfraSight-AI: Data Ingestion DAG
Orchestrates daily data loading from CSV to PostgreSQL and Neo4j.

Schedule: Daily at 2:00 AM
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Default arguments
default_args = {
    'owner': 'infrasight',
    'depends_on_past': False,
    'email': ['alerts@infrasight.local'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=1),
}

# DAG definition
dag = DAG(
    'infrasight_data_ingestion',
    default_args=default_args,
    description='Daily data ingestion from CSV to PostgreSQL and Neo4j',
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    start_date=days_ago(1),
    catchup=False,
    tags=['infrasight', 'ingestion', 'etl'],
    doc_md="""
    ## InfraSight Data Ingestion Pipeline

    This DAG performs the following tasks:
    1. Validates CSV data files
    2. Loads data into PostgreSQL
    3. Loads data into Neo4j graph database
    4. Computes graph metrics
    5. Generates embeddings for RAG

    ### Schedule
    Runs daily at 2:00 AM

    ### Dependencies
    - PostgreSQL must be running
    - Neo4j must be running
    - CSV files must be present in data/raw/
    """
)


def validate_csv_files(**context):
    """Validate that all required CSV files exist and have data."""
    from config.settings import CSV_FILES

    missing_files = []
    empty_files = []

    for name, filepath in CSV_FILES.items():
        if not filepath.exists():
            missing_files.append(name)
        else:
            # Check if file has content (more than just header)
            with open(filepath, 'r') as f:
                lines = f.readlines()
                if len(lines) <= 1:
                    empty_files.append(name)

    if missing_files:
        raise FileNotFoundError(f"Missing CSV files: {missing_files}")

    if empty_files:
        raise ValueError(f"Empty CSV files: {empty_files}")

    context['ti'].xcom_push(key='validation_status', value='success')
    return f"Validated {len(CSV_FILES)} CSV files successfully"


def load_postgres(**context):
    """Load all CSV data into PostgreSQL."""
    from src.ingestion.postgres_loader import PostgresLoader

    loader = PostgresLoader()
    try:
        loader.connect()
        loader.load_all()
        context['ti'].xcom_push(key='postgres_status', value='success')
        return "PostgreSQL load completed successfully"
    except Exception as e:
        context['ti'].xcom_push(key='postgres_status', value='failed')
        raise
    finally:
        loader.disconnect()


def load_neo4j(**context):
    """Load all data into Neo4j graph database."""
    from src.ingestion.neo4j_loader import Neo4jLoader

    loader = Neo4jLoader()
    try:
        loader.connect()
        loader.load_all(clear_first=False)
        context['ti'].xcom_push(key='neo4j_status', value='success')
        return "Neo4j load completed successfully"
    except Exception as e:
        context['ti'].xcom_push(key='neo4j_status', value='failed')
        raise
    finally:
        loader.disconnect()


def compute_graph_metrics(**context):
    """Compute and update graph metrics in Neo4j."""
    from src.ingestion.neo4j_loader import Neo4jLoader

    loader = Neo4jLoader()
    try:
        loader.connect()
        loader.compute_graph_metrics()
        return "Graph metrics computed successfully"
    finally:
        loader.disconnect()


def generate_embeddings(**context):
    """Generate embeddings for incidents and resolutions."""
    from src.rag.embedding_generator import EmbeddingGenerator

    try:
        generator = EmbeddingGenerator()
        generator.generate_all_embeddings()
        return "Embeddings generated successfully"
    except ImportError:
        # If RAG module not yet implemented, skip
        return "Embedding generation skipped (module not ready)"


def send_completion_notification(**context):
    """Send notification on pipeline completion."""
    postgres_status = context['ti'].xcom_pull(key='postgres_status', task_ids='load_postgres')
    neo4j_status = context['ti'].xcom_pull(key='neo4j_status', task_ids='load_neo4j')

    message = f"""
    InfraSight Data Ingestion Complete
    ==================================
    Execution Date: {context['execution_date']}
    PostgreSQL Status: {postgres_status}
    Neo4j Status: {neo4j_status}
    """

    print(message)
    return message


# Task definitions
validate_task = PythonOperator(
    task_id='validate_csv_files',
    python_callable=validate_csv_files,
    dag=dag,
)

postgres_task = PythonOperator(
    task_id='load_postgres',
    python_callable=load_postgres,
    dag=dag,
)

neo4j_task = PythonOperator(
    task_id='load_neo4j',
    python_callable=load_neo4j,
    dag=dag,
)

metrics_task = PythonOperator(
    task_id='compute_graph_metrics',
    python_callable=compute_graph_metrics,
    dag=dag,
)

embedding_task = PythonOperator(
    task_id='generate_embeddings',
    python_callable=generate_embeddings,
    dag=dag,
)

notify_task = PythonOperator(
    task_id='send_notification',
    python_callable=send_completion_notification,
    dag=dag,
)

# Task dependencies
validate_task >> [postgres_task, neo4j_task]
neo4j_task >> metrics_task
[postgres_task, metrics_task] >> embedding_task
embedding_task >> notify_task
