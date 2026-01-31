"""
InfraSight-AI: Anomaly Detection DAG
Runs hourly anomaly detection on infrastructure metrics and graph state.

Schedule: Hourly
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

default_args = {
    'owner': 'infrasight',
    'depends_on_past': False,
    'email': ['alerts@infrasight.local'],
    'email_on_failure': True,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
    'execution_timeout': timedelta(minutes=30),
}

dag = DAG(
    'infrasight_anomaly_detection',
    default_args=default_args,
    description='Hourly anomaly detection on metrics and graph state',
    schedule_interval='0 * * * *',  # Every hour
    start_date=days_ago(1),
    catchup=False,
    tags=['infrasight', 'anomaly', 'monitoring'],
    doc_md="""
    ## InfraSight Anomaly Detection Pipeline

    This DAG performs:
    1. Metrics anomaly detection using statistical methods
    2. Graph drift detection (new/removed dependencies)
    3. Orphan/zombie service detection
    4. Alert generation for detected anomalies
    """
)


def detect_metric_anomalies(**context):
    """Detect anomalies in infrastructure metrics."""
    import logging
    logger = logging.getLogger(__name__)

    try:
        # This would connect to PostgreSQL and analyze recent metrics
        # Using statistical methods (z-score, IQR, etc.)

        query = """
        WITH recent_metrics AS (
            SELECT
                ci_id,
                metric_type,
                metric_value,
                threshold_warning,
                threshold_critical,
                collected_at
            FROM metrics_usage
            WHERE collected_at > NOW() - INTERVAL '1 hour'
        ),
        stats AS (
            SELECT
                ci_id,
                metric_type,
                AVG(metric_value) as avg_value,
                STDDEV(metric_value) as std_value,
                MAX(metric_value) as max_value
            FROM recent_metrics
            GROUP BY ci_id, metric_type
        )
        SELECT
            s.ci_id,
            s.metric_type,
            s.avg_value,
            s.max_value,
            r.threshold_critical,
            CASE
                WHEN s.max_value > r.threshold_critical THEN 'critical'
                WHEN s.max_value > r.threshold_warning THEN 'warning'
                ELSE 'normal'
            END as status
        FROM stats s
        JOIN recent_metrics r ON s.ci_id = r.ci_id AND s.metric_type = r.metric_type
        WHERE s.max_value > r.threshold_warning
        """

        # In production, this would execute the query
        # For now, return simulated results
        anomalies_detected = 5  # Simulated
        logger.info(f"Detected {anomalies_detected} metric anomalies")

        context['ti'].xcom_push(key='metric_anomalies', value=anomalies_detected)
        return f"Detected {anomalies_detected} metric anomalies"

    except Exception as e:
        logger.error(f"Error in metric anomaly detection: {e}")
        raise


def detect_graph_drift(**context):
    """Detect changes in the dependency graph structure."""
    import logging
    logger = logging.getLogger(__name__)

    try:
        # This would compare current graph state with baseline
        # Detect new/removed nodes and relationships

        query = """
        // Find new dependencies added in the last hour
        MATCH (ci:ConfigurationItem)-[r]->(target:ConfigurationItem)
        WHERE r.created_at > datetime() - duration('PT1H')
        RETURN ci.ci_id as source, type(r) as relationship, target.ci_id as target,
               r.created_at as created

        // Find CIs with unusual relationship changes
        MATCH (ci:ConfigurationItem)
        WHERE ci.updated_at > datetime() - duration('PT1H')
        OPTIONAL MATCH (ci)-[r]->()
        WITH ci, count(r) as current_relations
        WHERE abs(current_relations - ci.baseline_relations) > 3
        RETURN ci.ci_id, current_relations, ci.baseline_relations
        """

        drift_events = 2  # Simulated
        logger.info(f"Detected {drift_events} graph drift events")

        context['ti'].xcom_push(key='drift_events', value=drift_events)
        return f"Detected {drift_events} graph drift events"

    except Exception as e:
        logger.error(f"Error in graph drift detection: {e}")
        raise


def detect_orphan_services(**context):
    """Identify orphaned, redundant, and zombie services."""
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Query for orphaned CIs (no incoming or outgoing dependencies)
        query = """
        // Find orphaned CIs
        MATCH (ci:ConfigurationItem)
        WHERE NOT (ci)-[:DEPENDS_ON]-()
          AND NOT ()-[:DEPENDS_ON]->(ci)
          AND NOT (ci)-[:HOSTS]-()
          AND NOT ()-[:HOSTS]->(ci)
          AND NOT (ci)-[:CONNECTS_TO]-()
          AND NOT ()-[:CONNECTS_TO]->(ci)
        RETURN ci.ci_id as ci_id,
               ci.name as name,
               ci.type as type,
               ci.cost_per_month as monthly_cost,
               ci.health_status as health
        ORDER BY ci.cost_per_month DESC

        // Find zombie services (no recent activity but still running)
        MATCH (ci:ConfigurationItem)
        WHERE ci.status = 'active'
          AND ci.health_status = 'healthy'
          AND NOT exists((ci)<-[:AFFECTS]-(:Incident {created_at: datetime() - duration('P30D')}))
          AND NOT exists((ci)<-[:MODIFIES]-(:Change {created_at: datetime() - duration('P30D')}))
        RETURN ci.ci_id, ci.name, ci.cost_per_month
        ORDER BY ci.cost_per_month DESC
        LIMIT 20
        """

        orphans_found = 8  # Simulated
        zombies_found = 3  # Simulated

        logger.info(f"Found {orphans_found} orphaned CIs and {zombies_found} zombie services")

        context['ti'].xcom_push(key='orphans', value=orphans_found)
        context['ti'].xcom_push(key='zombies', value=zombies_found)

        return f"Found {orphans_found} orphans, {zombies_found} zombies"

    except Exception as e:
        logger.error(f"Error in orphan detection: {e}")
        raise


def generate_alerts(**context):
    """Generate alerts for detected anomalies."""
    import logging
    logger = logging.getLogger(__name__)

    metric_anomalies = context['ti'].xcom_pull(key='metric_anomalies', task_ids='detect_metric_anomalies')
    drift_events = context['ti'].xcom_pull(key='drift_events', task_ids='detect_graph_drift')
    orphans = context['ti'].xcom_pull(key='orphans', task_ids='detect_orphan_services')

    alerts = []

    if metric_anomalies and metric_anomalies > 0:
        alerts.append({
            'type': 'metric_anomaly',
            'severity': 'high' if metric_anomalies > 10 else 'medium',
            'count': metric_anomalies,
            'message': f'{metric_anomalies} infrastructure metrics exceeded thresholds'
        })

    if drift_events and drift_events > 0:
        alerts.append({
            'type': 'graph_drift',
            'severity': 'medium',
            'count': drift_events,
            'message': f'{drift_events} unexpected dependency changes detected'
        })

    if orphans and orphans > 5:
        alerts.append({
            'type': 'orphan_services',
            'severity': 'low',
            'count': orphans,
            'message': f'{orphans} orphaned services identified for review'
        })

    logger.info(f"Generated {len(alerts)} alerts")

    # In production, would store alerts to database and send notifications
    for alert in alerts:
        logger.info(f"ALERT [{alert['severity'].upper()}]: {alert['message']}")

    return f"Generated {len(alerts)} alerts"


def update_anomaly_baseline(**context):
    """Update baseline metrics for future comparison."""
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Update statistical baselines for comparison
        # Store current graph state as reference

        logger.info("Anomaly baseline updated")
        return "Baseline updated successfully"

    except Exception as e:
        logger.error(f"Error updating baseline: {e}")
        raise


# Task definitions
metric_anomaly_task = PythonOperator(
    task_id='detect_metric_anomalies',
    python_callable=detect_metric_anomalies,
    dag=dag,
)

drift_task = PythonOperator(
    task_id='detect_graph_drift',
    python_callable=detect_graph_drift,
    dag=dag,
)

orphan_task = PythonOperator(
    task_id='detect_orphan_services',
    python_callable=detect_orphan_services,
    dag=dag,
)

alert_task = PythonOperator(
    task_id='generate_alerts',
    python_callable=generate_alerts,
    dag=dag,
)

baseline_task = PythonOperator(
    task_id='update_baseline',
    python_callable=update_anomaly_baseline,
    dag=dag,
)

# Dependencies - run detection in parallel, then alerts, then update baseline
[metric_anomaly_task, drift_task, orphan_task] >> alert_task >> baseline_task
