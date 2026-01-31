"""
InfraSight-AI: Neo4j Graph Data Loader
Loads CSV data into Neo4j graph database.
"""

import csv
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from neo4j import GraphDatabase
except ImportError:
    print("neo4j driver not installed. Run: pip install neo4j")
    GraphDatabase = None

from config.settings import config, CSV_FILES

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Neo4jLoader:
    """Loads CSV data into Neo4j graph database."""

    def __init__(self):
        self.driver = None

    def connect(self):
        """Establish database connection."""
        if GraphDatabase is None:
            raise ImportError("neo4j is required. Install with: pip install neo4j")

        try:
            self.driver = GraphDatabase.driver(
                config.neo4j.uri,
                auth=(config.neo4j.user, config.neo4j.password)
            )
            # Verify connection
            self.driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {config.neo4j.uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def disconnect(self):
        """Close database connection."""
        if self.driver:
            self.driver.close()
            logger.info("Disconnected from Neo4j")

    def _run_query(self, query: str, parameters: Dict = None):
        """Execute a Cypher query."""
        with self.driver.session(database=config.neo4j.database) as session:
            result = session.run(query, parameters or {})
            return result.data()

    def _batch_query(self, query: str, records: List[Dict], batch_size: int = 100):
        """Execute batch insert."""
        with self.driver.session(database=config.neo4j.database) as session:
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                session.run(query, {"batch": batch})
        logger.info(f"Inserted {len(records)} records")

    def create_constraints_and_indexes(self):
        """Create constraints and indexes for optimal performance."""
        logger.info("Creating constraints and indexes...")

        constraints = [
            "CREATE CONSTRAINT service_id_unique IF NOT EXISTS FOR (s:Service) REQUIRE s.service_id IS UNIQUE",
            "CREATE CONSTRAINT ci_id_unique IF NOT EXISTS FOR (ci:ConfigurationItem) REQUIRE ci.ci_id IS UNIQUE",
            "CREATE CONSTRAINT incident_id_unique IF NOT EXISTS FOR (i:Incident) REQUIRE i.incident_id IS UNIQUE",
            "CREATE CONSTRAINT problem_id_unique IF NOT EXISTS FOR (p:Problem) REQUIRE p.problem_id IS UNIQUE",
            "CREATE CONSTRAINT change_id_unique IF NOT EXISTS FOR (c:Change) REQUIRE c.change_id IS UNIQUE",
            "CREATE CONSTRAINT resolution_id_unique IF NOT EXISTS FOR (r:Resolution) REQUIRE r.resolution_id IS UNIQUE",
        ]

        indexes = [
            "CREATE INDEX service_criticality_idx IF NOT EXISTS FOR (s:Service) ON (s.criticality)",
            "CREATE INDEX ci_type_idx IF NOT EXISTS FOR (ci:ConfigurationItem) ON (ci.type)",
            "CREATE INDEX ci_environment_idx IF NOT EXISTS FOR (ci:ConfigurationItem) ON (ci.environment)",
            "CREATE INDEX ci_health_idx IF NOT EXISTS FOR (ci:ConfigurationItem) ON (ci.health_status)",
            "CREATE INDEX incident_severity_idx IF NOT EXISTS FOR (i:Incident) ON (i.severity)",
            "CREATE INDEX incident_status_idx IF NOT EXISTS FOR (i:Incident) ON (i.status)",
            "CREATE INDEX change_risk_idx IF NOT EXISTS FOR (c:Change) ON (c.risk_level)",
        ]

        for constraint in constraints:
            try:
                self._run_query(constraint)
            except Exception as e:
                logger.warning(f"Constraint may already exist: {e}")

        for index in indexes:
            try:
                self._run_query(index)
            except Exception as e:
                logger.warning(f"Index may already exist: {e}")

        logger.info("Constraints and indexes created")

    def clear_database(self):
        """Clear all nodes and relationships (use with caution)."""
        logger.warning("Clearing all data from Neo4j...")
        self._run_query("MATCH (n) DETACH DELETE n")
        logger.info("Database cleared")

    def load_services(self, filepath: Path):
        """Load services as nodes."""
        logger.info(f"Loading services from {filepath}")

        records = self._read_csv(filepath)

        query = """
        UNWIND $batch AS row
        MERGE (s:Service {service_id: row.service_id})
        SET s.name = row.service_name,
            s.type = row.service_type,
            s.description = row.description,
            s.criticality = row.criticality,
            s.owner = row.owner,
            s.team = row.team,
            s.sla_hours = toFloat(row.sla_target_hours),
            s.status = row.status,
            s.created_at = datetime(row.created_at),
            s.updated_at = datetime(row.updated_at)
        """

        self._batch_query(query, records)

    def load_configuration_items(self, filepath: Path):
        """Load configuration items as nodes."""
        logger.info(f"Loading configuration items from {filepath}")

        records = self._read_csv(filepath)

        query = """
        UNWIND $batch AS row
        MERGE (ci:ConfigurationItem {ci_id: row.ci_id})
        SET ci.name = row.ci_name,
            ci.type = row.ci_type,
            ci.service_id = row.service_id,
            ci.description = row.description,
            ci.environment = row.environment,
            ci.status = row.status,
            ci.version = row.version,
            ci.ip_address = row.ip_address,
            ci.hostname = row.hostname,
            ci.operating_system = row.operating_system,
            ci.cpu_cores = toInteger(row.cpu_cores),
            ci.memory_gb = toFloat(row.memory_gb),
            ci.storage_gb = toFloat(row.storage_gb),
            ci.cloud_provider = row.cloud_provider,
            ci.cloud_region = row.cloud_region,
            ci.cost_per_month = toFloat(row.cost_per_month),
            ci.health_status = row.health_status,
            ci.centrality_score = 0.0,
            ci.pagerank_score = 0.0,
            ci.blast_radius = 0,
            ci.risk_score = 0.0,
            ci.created_at = datetime(row.created_at),
            ci.updated_at = datetime(row.updated_at)
        """

        self._batch_query(query, records)

    def link_services_to_cis(self):
        """Create PROVIDES relationships between Services and CIs."""
        logger.info("Linking services to configuration items...")

        query = """
        MATCH (ci:ConfigurationItem)
        WHERE ci.service_id IS NOT NULL AND ci.service_id <> ''
        MATCH (s:Service {service_id: ci.service_id})
        MERGE (s)-[r:PROVIDES]->(ci)
        SET r.created_at = datetime()
        RETURN count(r) AS links_created
        """

        result = self._run_query(query)
        logger.info(f"Created {result[0]['links_created']} Service-CI links")

    def load_ci_relationships(self, filepath: Path):
        """Load CI relationships."""
        logger.info(f"Loading CI relationships from {filepath}")

        records = self._read_csv(filepath)

        # Group by relationship type
        rel_types = {}
        for record in records:
            rel_type = record['relationship_type'].upper()
            if rel_type not in rel_types:
                rel_types[rel_type] = []
            rel_types[rel_type].append(record)

        for rel_type, type_records in rel_types.items():
            query = f"""
            UNWIND $batch AS row
            MATCH (source:ConfigurationItem {{ci_id: row.source_ci_id}})
            MATCH (target:ConfigurationItem {{ci_id: row.target_ci_id}})
            MERGE (source)-[r:{rel_type}]->(target)
            SET r.strength = toFloat(row.strength),
                r.description = row.description,
                r.port = CASE WHEN row.port IS NOT NULL AND row.port <> '' THEN toInteger(row.port) ELSE null END,
                r.protocol = row.protocol,
                r.is_critical = row.is_critical = 'true',
                r.created_at = datetime(row.created_at)
            """
            self._batch_query(query, type_records)
            logger.info(f"Loaded {len(type_records)} {rel_type} relationships")

    def load_incidents(self, filepath: Path):
        """Load incidents as nodes and create relationships."""
        logger.info(f"Loading incidents from {filepath}")

        records = self._read_csv(filepath)

        # Create incident nodes
        query = """
        UNWIND $batch AS row
        MERGE (i:Incident {incident_id: row.incident_id})
        SET i.incident_number = row.incident_number,
            i.title = row.title,
            i.description = row.description,
            i.severity = row.severity,
            i.priority = row.priority,
            i.status = row.status,
            i.category = row.category,
            i.subcategory = row.subcategory,
            i.impact_scope = row.impact_scope,
            i.reported_by = row.reported_by,
            i.assigned_to = row.assigned_to,
            i.assignment_group = row.assignment_group,
            i.created_at = datetime(row.created_at),
            i.resolution_time_minutes = CASE WHEN row.resolution_time_minutes <> '' THEN toInteger(row.resolution_time_minutes) ELSE null END,
            i.sla_breached = row.sla_breached = 'true',
            i.is_major_incident = row.is_major_incident = 'true'
        """
        self._batch_query(query, records)

        # Create AFFECTS relationships
        query = """
        UNWIND $batch AS row
        MATCH (i:Incident {incident_id: row.incident_id})
        MATCH (ci:ConfigurationItem {ci_id: row.affected_ci_id})
        WHERE row.affected_ci_id IS NOT NULL AND row.affected_ci_id <> ''
        MERGE (i)-[r:AFFECTS]->(ci)
        SET r.created_at = datetime()
        """
        self._batch_query(query, [r for r in records if r.get('affected_ci_id')])

    def load_problems(self, filepath: Path):
        """Load problems as nodes."""
        logger.info(f"Loading problems from {filepath}")

        records = self._read_csv(filepath)

        query = """
        UNWIND $batch AS row
        MERGE (p:Problem {problem_id: row.problem_id})
        SET p.problem_number = row.problem_number,
            p.title = row.title,
            p.description = row.description,
            p.status = row.status,
            p.priority = row.priority,
            p.root_cause = row.root_cause,
            p.known_error = row.known_error = 'true',
            p.workaround = row.workaround,
            p.category = row.category,
            p.owner = row.owner,
            p.assigned_to = row.assigned_to,
            p.related_incident_count = toInteger(row.related_incident_count),
            p.created_at = datetime(row.created_at)
        """
        self._batch_query(query, records)

        # Create ROOT_CAUSE relationships
        query = """
        UNWIND $batch AS row
        MATCH (p:Problem {problem_id: row.problem_id})
        MATCH (ci:ConfigurationItem {ci_id: row.root_cause_ci_id})
        WHERE row.root_cause_ci_id IS NOT NULL AND row.root_cause_ci_id <> ''
        MERGE (p)-[r:ROOT_CAUSE]->(ci)
        SET r.identified_at = datetime()
        """
        self._batch_query(query, [r for r in records if r.get('root_cause_ci_id')])

    def load_changes(self, filepath: Path):
        """Load changes as nodes."""
        logger.info(f"Loading changes from {filepath}")

        records = self._read_csv(filepath)

        query = """
        UNWIND $batch AS row
        MERGE (c:Change {change_id: row.change_id})
        SET c.change_number = row.change_number,
            c.title = row.title,
            c.description = row.description,
            c.change_type = row.change_type,
            c.status = row.status,
            c.risk_level = row.risk_level,
            c.computed_risk_score = toFloat(row.computed_risk_score),
            c.category = row.category,
            c.requested_by = row.requested_by,
            c.approved_by = row.approved_by,
            c.implemented_by = row.implemented_by,
            c.scheduled_start = datetime(row.scheduled_start),
            c.scheduled_end = datetime(row.scheduled_end),
            c.success = row.success = 'true',
            c.caused_incident = row.caused_incident = 'true',
            c.created_at = datetime(row.created_at)
        """
        self._batch_query(query, records)

        # Create MODIFIES relationships
        query = """
        UNWIND $batch AS row
        MATCH (c:Change {change_id: row.change_id})
        MATCH (ci:ConfigurationItem {ci_id: row.affected_ci_id})
        WHERE row.affected_ci_id IS NOT NULL AND row.affected_ci_id <> ''
        MERGE (c)-[r:MODIFIES]->(ci)
        SET r.created_at = datetime()
        """
        self._batch_query(query, [r for r in records if r.get('affected_ci_id')])

    def load_resolutions(self, filepath: Path):
        """Load resolutions as nodes and link to incidents."""
        logger.info(f"Loading resolutions from {filepath}")

        records = self._read_csv(filepath)

        query = """
        UNWIND $batch AS row
        MERGE (r:Resolution {resolution_id: row.resolution_id})
        SET r.resolution_type = row.resolution_type,
            r.title = row.title,
            r.description = row.description,
            r.root_cause = row.root_cause,
            r.fix_applied = row.fix_applied,
            r.workaround = row.workaround,
            r.preventive_action = row.preventive_action,
            r.resolved_by = row.resolved_by,
            r.time_to_resolve_minutes = CASE WHEN row.time_to_resolve_minutes <> '' THEN toInteger(row.time_to_resolve_minutes) ELSE null END,
            r.was_effective = row.was_effective = 'true',
            r.reoccurrence_count = toInteger(row.reoccurrence_count),
            r.knowledge_article_id = row.knowledge_article_id,
            r.created_at = datetime(row.created_at)
        """
        self._batch_query(query, records)

        # Link to incidents
        query = """
        UNWIND $batch AS row
        MATCH (i:Incident {incident_id: row.incident_id})
        MATCH (r:Resolution {resolution_id: row.resolution_id})
        MERGE (i)-[rel:RESOLVED_BY]->(r)
        SET rel.created_at = datetime()
        """
        self._batch_query(query, records)

    def compute_graph_metrics(self):
        """Compute and store graph metrics on CI nodes."""
        logger.info("Computing graph metrics...")

        # Compute blast radius (downstream dependent count)
        query = """
        MATCH (ci:ConfigurationItem)
        OPTIONAL MATCH path = (ci)<-[:DEPENDS_ON|HOSTS|RUNS_ON*1..5]-(dependent:ConfigurationItem)
        WITH ci, count(DISTINCT dependent) AS blast_radius
        SET ci.blast_radius = blast_radius
        RETURN count(ci) AS updated
        """
        result = self._run_query(query)
        logger.info(f"Updated blast radius for {result[0]['updated']} CIs")

        # Compute simple centrality (in-degree + out-degree)
        query = """
        MATCH (ci:ConfigurationItem)
        OPTIONAL MATCH (ci)-[out]->()
        OPTIONAL MATCH (ci)<-[in]-()
        WITH ci, count(DISTINCT out) AS out_degree, count(DISTINCT in) AS in_degree
        SET ci.centrality_score = toFloat(in_degree + out_degree) / 100.0
        RETURN count(ci) AS updated
        """
        result = self._run_query(query)
        logger.info(f"Updated centrality for {result[0]['updated']} CIs")

        # Compute risk score based on centrality and blast radius
        query = """
        MATCH (ci:ConfigurationItem)
        SET ci.risk_score = (ci.centrality_score * 0.4) + (toFloat(ci.blast_radius) / 50.0 * 0.6)
        RETURN count(ci) AS updated
        """
        result = self._run_query(query)
        logger.info(f"Updated risk scores for {result[0]['updated']} CIs")

    def _read_csv(self, filepath: Path) -> List[Dict]:
        """Read CSV file and return list of dictionaries."""
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)

    def load_all(self, clear_first: bool = False):
        """Load all data into Neo4j."""
        logger.info("Starting full data load to Neo4j...")

        if clear_first:
            self.clear_database()

        self.create_constraints_and_indexes()

        # Load nodes first
        self.load_services(CSV_FILES["services"])
        self.load_configuration_items(CSV_FILES["configuration_items"])
        self.load_incidents(CSV_FILES["incidents"])
        self.load_problems(CSV_FILES["problems"])
        self.load_changes(CSV_FILES["changes"])
        self.load_resolutions(CSV_FILES["resolutions"])

        # Create relationships
        self.link_services_to_cis()
        self.load_ci_relationships(CSV_FILES["ci_relationships"])

        # Compute metrics
        self.compute_graph_metrics()

        logger.info("Full Neo4j data load complete!")


def main():
    """Main entry point."""
    loader = Neo4jLoader()
    try:
        loader.connect()
        loader.load_all(clear_first=True)
    finally:
        loader.disconnect()


if __name__ == "__main__":
    main()
