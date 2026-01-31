"""
InfraSight-AI: PostgreSQL Data Loader
Loads CSV data into PostgreSQL tables with proper type handling.
"""

import csv
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import psycopg2
    from psycopg2.extras import execute_batch, RealDictCursor
except ImportError:
    print("psycopg2 not installed. Run: pip install psycopg2-binary")
    psycopg2 = None

from config.settings import config, CSV_FILES

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PostgresLoader:
    """Loads CSV data into PostgreSQL database."""

    def __init__(self):
        self.conn = None
        self.cursor = None

    def connect(self):
        """Establish database connection."""
        if psycopg2 is None:
            raise ImportError("psycopg2 is required. Install with: pip install psycopg2-binary")

        try:
            self.conn = psycopg2.connect(**config.postgres.dsn)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            logger.info(f"Connected to PostgreSQL at {config.postgres.host}:{config.postgres.port}")
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    def disconnect(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            logger.info("Disconnected from PostgreSQL")

    def _parse_value(self, value: str, field_type: str) -> Any:
        """Parse string value to appropriate type."""
        if value == "" or value is None:
            return None

        if field_type == "uuid":
            return value
        elif field_type == "int":
            return int(value) if value else None
        elif field_type == "float":
            return float(value) if value else None
        elif field_type == "bool":
            return value.lower() == "true"
        elif field_type == "datetime":
            try:
                return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None
        elif field_type == "inet":
            return value if value else None
        else:
            return value

    def load_services(self, filepath: Path):
        """Load services from CSV."""
        logger.info(f"Loading services from {filepath}")

        insert_sql = """
            INSERT INTO services (
                service_id, service_name, service_type, description, criticality,
                owner, team, sla_target_hours, status, created_at, updated_at
            ) VALUES (
                %(service_id)s, %(service_name)s, %(service_type)s, %(description)s,
                %(criticality)s::service_criticality, %(owner)s, %(team)s,
                %(sla_target_hours)s, %(status)s::status_type,
                %(created_at)s, %(updated_at)s
            )
            ON CONFLICT (service_id) DO UPDATE SET
                service_name = EXCLUDED.service_name,
                service_type = EXCLUDED.service_type,
                description = EXCLUDED.description,
                criticality = EXCLUDED.criticality,
                owner = EXCLUDED.owner,
                team = EXCLUDED.team,
                sla_target_hours = EXCLUDED.sla_target_hours,
                status = EXCLUDED.status,
                updated_at = EXCLUDED.updated_at
        """

        field_types = {
            "service_id": "uuid",
            "sla_target_hours": "float",
            "created_at": "datetime",
            "updated_at": "datetime"
        }

        self._load_csv(filepath, insert_sql, field_types)

    def load_configuration_items(self, filepath: Path):
        """Load configuration items from CSV."""
        logger.info(f"Loading configuration items from {filepath}")

        insert_sql = """
            INSERT INTO configuration_items (
                ci_id, ci_name, ci_type, service_id, description, environment,
                status, version, ip_address, hostname, operating_system,
                cpu_cores, memory_gb, storage_gb, cloud_provider, cloud_region,
                cost_per_month, health_status, last_health_check, created_at, updated_at
            ) VALUES (
                %(ci_id)s, %(ci_name)s, %(ci_type)s::ci_type,
                NULLIF(%(service_id)s, '')::uuid, %(description)s,
                %(environment)s::environment_type, %(status)s::status_type,
                %(version)s, %(ip_address)s::inet, %(hostname)s, %(operating_system)s,
                %(cpu_cores)s, %(memory_gb)s, %(storage_gb)s,
                %(cloud_provider)s, %(cloud_region)s, %(cost_per_month)s,
                %(health_status)s, %(last_health_check)s, %(created_at)s, %(updated_at)s
            )
            ON CONFLICT (ci_id) DO UPDATE SET
                ci_name = EXCLUDED.ci_name,
                ci_type = EXCLUDED.ci_type,
                service_id = EXCLUDED.service_id,
                description = EXCLUDED.description,
                environment = EXCLUDED.environment,
                status = EXCLUDED.status,
                version = EXCLUDED.version,
                ip_address = EXCLUDED.ip_address,
                hostname = EXCLUDED.hostname,
                operating_system = EXCLUDED.operating_system,
                cpu_cores = EXCLUDED.cpu_cores,
                memory_gb = EXCLUDED.memory_gb,
                storage_gb = EXCLUDED.storage_gb,
                cloud_provider = EXCLUDED.cloud_provider,
                cloud_region = EXCLUDED.cloud_region,
                cost_per_month = EXCLUDED.cost_per_month,
                health_status = EXCLUDED.health_status,
                last_health_check = EXCLUDED.last_health_check,
                updated_at = EXCLUDED.updated_at
        """

        field_types = {
            "ci_id": "uuid",
            "service_id": "uuid",
            "cpu_cores": "int",
            "memory_gb": "float",
            "storage_gb": "float",
            "cost_per_month": "float",
            "last_health_check": "datetime",
            "created_at": "datetime",
            "updated_at": "datetime"
        }

        self._load_csv(filepath, insert_sql, field_types)

    def load_ci_relationships(self, filepath: Path):
        """Load CI relationships from CSV."""
        logger.info(f"Loading CI relationships from {filepath}")

        insert_sql = """
            INSERT INTO ci_relationships (
                relationship_id, source_ci_id, target_ci_id, relationship_type,
                strength, description, port, protocol, is_critical, created_at, updated_at
            ) VALUES (
                %(relationship_id)s, %(source_ci_id)s, %(target_ci_id)s,
                %(relationship_type)s::relationship_type, %(strength)s,
                %(description)s, %(port)s, %(protocol)s, %(is_critical)s,
                %(created_at)s, %(updated_at)s
            )
            ON CONFLICT (relationship_id) DO UPDATE SET
                source_ci_id = EXCLUDED.source_ci_id,
                target_ci_id = EXCLUDED.target_ci_id,
                relationship_type = EXCLUDED.relationship_type,
                strength = EXCLUDED.strength,
                description = EXCLUDED.description,
                port = EXCLUDED.port,
                protocol = EXCLUDED.protocol,
                is_critical = EXCLUDED.is_critical,
                updated_at = EXCLUDED.updated_at
        """

        field_types = {
            "relationship_id": "uuid",
            "source_ci_id": "uuid",
            "target_ci_id": "uuid",
            "strength": "float",
            "port": "int",
            "is_critical": "bool",
            "created_at": "datetime",
            "updated_at": "datetime"
        }

        self._load_csv(filepath, insert_sql, field_types)

    def load_incidents(self, filepath: Path):
        """Load incidents from CSV."""
        logger.info(f"Loading incidents from {filepath}")

        insert_sql = """
            INSERT INTO incidents (
                incident_id, incident_number, title, description, severity, priority,
                status, affected_ci_id, affected_service_id, category, subcategory,
                impact_scope, reported_by, assigned_to, assignment_group,
                created_at, acknowledged_at, resolved_at, closed_at,
                resolution_time_minutes, sla_breached, is_major_incident
            ) VALUES (
                %(incident_id)s, %(incident_number)s, %(title)s, %(description)s,
                %(severity)s::severity_level, %(priority)s::priority_level,
                %(status)s::status_type, NULLIF(%(affected_ci_id)s, '')::uuid,
                NULLIF(%(affected_service_id)s, '')::uuid, %(category)s,
                %(subcategory)s, %(impact_scope)s, %(reported_by)s,
                %(assigned_to)s, %(assignment_group)s, %(created_at)s,
                %(acknowledged_at)s, %(resolved_at)s, %(closed_at)s,
                %(resolution_time_minutes)s, %(sla_breached)s, %(is_major_incident)s
            )
            ON CONFLICT (incident_id) DO UPDATE SET
                incident_number = EXCLUDED.incident_number,
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                severity = EXCLUDED.severity,
                priority = EXCLUDED.priority,
                status = EXCLUDED.status,
                affected_ci_id = EXCLUDED.affected_ci_id,
                affected_service_id = EXCLUDED.affected_service_id,
                category = EXCLUDED.category,
                subcategory = EXCLUDED.subcategory,
                impact_scope = EXCLUDED.impact_scope,
                reported_by = EXCLUDED.reported_by,
                assigned_to = EXCLUDED.assigned_to,
                assignment_group = EXCLUDED.assignment_group,
                acknowledged_at = EXCLUDED.acknowledged_at,
                resolved_at = EXCLUDED.resolved_at,
                closed_at = EXCLUDED.closed_at,
                resolution_time_minutes = EXCLUDED.resolution_time_minutes,
                sla_breached = EXCLUDED.sla_breached,
                is_major_incident = EXCLUDED.is_major_incident
        """

        field_types = {
            "incident_id": "uuid",
            "affected_ci_id": "uuid",
            "affected_service_id": "uuid",
            "created_at": "datetime",
            "acknowledged_at": "datetime",
            "resolved_at": "datetime",
            "closed_at": "datetime",
            "resolution_time_minutes": "int",
            "sla_breached": "bool",
            "is_major_incident": "bool"
        }

        self._load_csv(filepath, insert_sql, field_types)

    def load_problems(self, filepath: Path):
        """Load problems from CSV."""
        logger.info(f"Loading problems from {filepath}")

        insert_sql = """
            INSERT INTO problems (
                problem_id, problem_number, title, description, status, priority,
                root_cause, root_cause_ci_id, known_error, known_error_description,
                workaround, category, owner, assigned_to, related_incident_count,
                created_at, identified_at, resolved_at, closed_at
            ) VALUES (
                %(problem_id)s, %(problem_number)s, %(title)s, %(description)s,
                %(status)s::status_type, %(priority)s::priority_level,
                %(root_cause)s, NULLIF(%(root_cause_ci_id)s, '')::uuid,
                %(known_error)s, %(known_error_description)s, %(workaround)s,
                %(category)s, %(owner)s, %(assigned_to)s, %(related_incident_count)s,
                %(created_at)s, %(identified_at)s, %(resolved_at)s, %(closed_at)s
            )
            ON CONFLICT (problem_id) DO UPDATE SET
                problem_number = EXCLUDED.problem_number,
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                status = EXCLUDED.status,
                priority = EXCLUDED.priority,
                root_cause = EXCLUDED.root_cause,
                root_cause_ci_id = EXCLUDED.root_cause_ci_id,
                known_error = EXCLUDED.known_error,
                known_error_description = EXCLUDED.known_error_description,
                workaround = EXCLUDED.workaround,
                category = EXCLUDED.category,
                owner = EXCLUDED.owner,
                assigned_to = EXCLUDED.assigned_to,
                related_incident_count = EXCLUDED.related_incident_count,
                identified_at = EXCLUDED.identified_at,
                resolved_at = EXCLUDED.resolved_at,
                closed_at = EXCLUDED.closed_at
        """

        field_types = {
            "problem_id": "uuid",
            "root_cause_ci_id": "uuid",
            "known_error": "bool",
            "related_incident_count": "int",
            "created_at": "datetime",
            "identified_at": "datetime",
            "resolved_at": "datetime",
            "closed_at": "datetime"
        }

        self._load_csv(filepath, insert_sql, field_types)

    def load_changes(self, filepath: Path):
        """Load changes from CSV."""
        logger.info(f"Loading changes from {filepath}")

        insert_sql = """
            INSERT INTO changes (
                change_id, change_number, title, description, change_type, status,
                risk_level, computed_risk_score, affected_ci_id, affected_service_id,
                category, reason, implementation_plan, rollback_plan, test_plan,
                requested_by, assigned_to, approved_by, implemented_by,
                scheduled_start, scheduled_end, actual_start, actual_end,
                created_at, approved_at, closed_at, success, failure_reason, caused_incident
            ) VALUES (
                %(change_id)s, %(change_number)s, %(title)s, %(description)s,
                %(change_type)s::change_type, %(status)s::status_type,
                %(risk_level)s::risk_level, %(computed_risk_score)s,
                NULLIF(%(affected_ci_id)s, '')::uuid,
                NULLIF(%(affected_service_id)s, '')::uuid,
                %(category)s, %(reason)s, %(implementation_plan)s,
                %(rollback_plan)s, %(test_plan)s, %(requested_by)s,
                %(assigned_to)s, %(approved_by)s, %(implemented_by)s,
                %(scheduled_start)s, %(scheduled_end)s, %(actual_start)s,
                %(actual_end)s, %(created_at)s, %(approved_at)s, %(closed_at)s,
                NULLIF(%(success)s, '')::boolean, %(failure_reason)s, %(caused_incident)s
            )
            ON CONFLICT (change_id) DO UPDATE SET
                change_number = EXCLUDED.change_number,
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                change_type = EXCLUDED.change_type,
                status = EXCLUDED.status,
                risk_level = EXCLUDED.risk_level,
                computed_risk_score = EXCLUDED.computed_risk_score,
                affected_ci_id = EXCLUDED.affected_ci_id,
                affected_service_id = EXCLUDED.affected_service_id,
                category = EXCLUDED.category,
                reason = EXCLUDED.reason,
                implementation_plan = EXCLUDED.implementation_plan,
                rollback_plan = EXCLUDED.rollback_plan,
                test_plan = EXCLUDED.test_plan,
                requested_by = EXCLUDED.requested_by,
                assigned_to = EXCLUDED.assigned_to,
                approved_by = EXCLUDED.approved_by,
                implemented_by = EXCLUDED.implemented_by,
                scheduled_start = EXCLUDED.scheduled_start,
                scheduled_end = EXCLUDED.scheduled_end,
                actual_start = EXCLUDED.actual_start,
                actual_end = EXCLUDED.actual_end,
                approved_at = EXCLUDED.approved_at,
                closed_at = EXCLUDED.closed_at,
                success = EXCLUDED.success,
                failure_reason = EXCLUDED.failure_reason,
                caused_incident = EXCLUDED.caused_incident
        """

        field_types = {
            "change_id": "uuid",
            "affected_ci_id": "uuid",
            "affected_service_id": "uuid",
            "computed_risk_score": "float",
            "scheduled_start": "datetime",
            "scheduled_end": "datetime",
            "actual_start": "datetime",
            "actual_end": "datetime",
            "created_at": "datetime",
            "approved_at": "datetime",
            "closed_at": "datetime",
            "caused_incident": "bool"
        }

        self._load_csv(filepath, insert_sql, field_types)

    def load_resolutions(self, filepath: Path):
        """Load resolutions from CSV."""
        logger.info(f"Loading resolutions from {filepath}")

        insert_sql = """
            INSERT INTO resolutions (
                resolution_id, incident_id, resolution_type, title, description,
                root_cause, fix_applied, workaround, preventive_action,
                resolved_by, time_to_resolve_minutes, was_effective,
                reoccurrence_count, knowledge_article_id, created_at, updated_at
            ) VALUES (
                %(resolution_id)s, %(incident_id)s, %(resolution_type)s::resolution_type,
                %(title)s, %(description)s, %(root_cause)s, %(fix_applied)s,
                %(workaround)s, %(preventive_action)s, %(resolved_by)s,
                %(time_to_resolve_minutes)s, %(was_effective)s,
                %(reoccurrence_count)s, %(knowledge_article_id)s,
                %(created_at)s, %(updated_at)s
            )
            ON CONFLICT (resolution_id) DO UPDATE SET
                incident_id = EXCLUDED.incident_id,
                resolution_type = EXCLUDED.resolution_type,
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                root_cause = EXCLUDED.root_cause,
                fix_applied = EXCLUDED.fix_applied,
                workaround = EXCLUDED.workaround,
                preventive_action = EXCLUDED.preventive_action,
                resolved_by = EXCLUDED.resolved_by,
                time_to_resolve_minutes = EXCLUDED.time_to_resolve_minutes,
                was_effective = EXCLUDED.was_effective,
                reoccurrence_count = EXCLUDED.reoccurrence_count,
                knowledge_article_id = EXCLUDED.knowledge_article_id,
                updated_at = EXCLUDED.updated_at
        """

        field_types = {
            "resolution_id": "uuid",
            "incident_id": "uuid",
            "time_to_resolve_minutes": "int",
            "was_effective": "bool",
            "reoccurrence_count": "int",
            "created_at": "datetime",
            "updated_at": "datetime"
        }

        self._load_csv(filepath, insert_sql, field_types)

    def load_metrics_usage(self, filepath: Path):
        """Load metrics usage from CSV."""
        logger.info(f"Loading metrics usage from {filepath}")

        insert_sql = """
            INSERT INTO metrics_usage (
                metric_id, ci_id, metric_type, metric_value, unit,
                threshold_warning, threshold_critical, is_anomaly,
                anomaly_score, collected_at
            ) VALUES (
                %(metric_id)s, %(ci_id)s, %(metric_type)s::metric_type,
                %(metric_value)s, %(unit)s, %(threshold_warning)s,
                %(threshold_critical)s, %(is_anomaly)s, %(anomaly_score)s,
                %(collected_at)s
            )
            ON CONFLICT (metric_id) DO UPDATE SET
                ci_id = EXCLUDED.ci_id,
                metric_type = EXCLUDED.metric_type,
                metric_value = EXCLUDED.metric_value,
                unit = EXCLUDED.unit,
                threshold_warning = EXCLUDED.threshold_warning,
                threshold_critical = EXCLUDED.threshold_critical,
                is_anomaly = EXCLUDED.is_anomaly,
                anomaly_score = EXCLUDED.anomaly_score,
                collected_at = EXCLUDED.collected_at
        """

        field_types = {
            "metric_id": "uuid",
            "ci_id": "uuid",
            "metric_value": "float",
            "threshold_warning": "float",
            "threshold_critical": "float",
            "is_anomaly": "bool",
            "anomaly_score": "float",
            "collected_at": "datetime"
        }

        self._load_csv(filepath, insert_sql, field_types)

    def _load_csv(self, filepath: Path, insert_sql: str, field_types: Dict[str, str]):
        """Generic CSV loader with type conversion."""
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            records = []

            for row in reader:
                # Convert types
                for field, ftype in field_types.items():
                    if field in row:
                        row[field] = self._parse_value(row[field], ftype)
                records.append(row)

            # Batch insert
            if records:
                try:
                    execute_batch(self.cursor, insert_sql, records, page_size=100)
                    self.conn.commit()
                    logger.info(f"Loaded {len(records)} records")
                except psycopg2.Error as e:
                    self.conn.rollback()
                    logger.error(f"Error loading data: {e}")
                    raise

    def load_all(self):
        """Load all CSV files into PostgreSQL."""
        logger.info("Starting full data load to PostgreSQL...")

        # Load in order of dependencies
        self.load_services(CSV_FILES["services"])
        self.load_configuration_items(CSV_FILES["configuration_items"])
        self.load_ci_relationships(CSV_FILES["ci_relationships"])
        self.load_incidents(CSV_FILES["incidents"])
        self.load_problems(CSV_FILES["problems"])
        self.load_changes(CSV_FILES["changes"])
        self.load_resolutions(CSV_FILES["resolutions"])
        self.load_metrics_usage(CSV_FILES["metrics_usage"])

        logger.info("Full data load complete!")


def main():
    """Main entry point."""
    loader = PostgresLoader()
    try:
        loader.connect()
        loader.load_all()
    finally:
        loader.disconnect()


if __name__ == "__main__":
    main()
