"""
InfraSight-AI: Embedding Generator
Generates and stores vector embeddings for incidents, resolutions, and knowledge.
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None
    print("sentence-transformers not installed. Run: pip install sentence-transformers")

try:
    import psycopg2
    from psycopg2.extras import execute_batch, RealDictCursor
except ImportError:
    psycopg2 = None
    print("psycopg2 not installed. Run: pip install psycopg2-binary")

from config.settings import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Generates and manages embeddings for RAG retrieval.

    Uses sentence-transformers (all-MiniLM-L6-v2 by default) to generate
    384-dimensional embeddings stored in PostgreSQL with pgvector.
    """

    def __init__(self):
        self.model = None
        self.conn = None
        self.cursor = None
        self._initialize()

    def _initialize(self):
        """Initialize the embedding model and database connection."""
        # Load embedding model
        if SentenceTransformer is not None:
            try:
                self.model = SentenceTransformer(config.embedding.model_name)
                logger.info(f"Loaded embedding model: {config.embedding.model_name}")
                logger.info(f"Embedding dimension: {self.model.get_sentence_embedding_dimension()}")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
        else:
            logger.warning("SentenceTransformer not available")

        # Connect to database
        if psycopg2 is not None:
            try:
                self.conn = psycopg2.connect(**config.postgres.dsn)
                self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
                logger.info("Connected to PostgreSQL for embedding storage")
            except Exception as e:
                logger.error(f"Failed to connect to PostgreSQL: {e}")

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text."""
        if self.model is None:
            return None

        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    def generate_batch_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for a batch of texts."""
        if self.model is None:
            return [None] * len(texts)

        try:
            embeddings = self.model.encode(
                texts,
                batch_size=config.embedding.batch_size,
                convert_to_numpy=True,
                show_progress_bar=True
            )
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            return [None] * len(texts)

    def generate_incident_embeddings(self):
        """Generate embeddings for all incidents."""
        logger.info("Generating incident embeddings...")

        if self.conn is None or self.model is None:
            logger.error("Database or model not available")
            return

        # Fetch incidents without embeddings
        self.cursor.execute("""
            SELECT i.incident_id, i.incident_number, i.title, i.description,
                   i.category, i.subcategory
            FROM incidents i
            LEFT JOIN incident_embeddings ie ON i.incident_id = ie.incident_id
            WHERE ie.embedding_id IS NULL
        """)

        incidents = self.cursor.fetchall()
        logger.info(f"Found {len(incidents)} incidents without embeddings")

        if not incidents:
            return

        # Prepare text for embedding
        texts = []
        for inc in incidents:
            text = self._create_incident_text(inc)
            texts.append(text)

        # Generate embeddings in batches
        embeddings = self.generate_batch_embeddings(texts)

        # Store embeddings
        insert_sql = """
            INSERT INTO incident_embeddings (incident_id, text_content, embedding, model_name)
            VALUES (%s, %s, %s::vector, %s)
            ON CONFLICT (incident_id) DO UPDATE SET
                text_content = EXCLUDED.text_content,
                embedding = EXCLUDED.embedding,
                created_at = CURRENT_TIMESTAMP
        """

        records = []
        for inc, text, embedding in zip(incidents, texts, embeddings):
            if embedding is not None:
                embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                records.append((
                    inc['incident_id'],
                    text,
                    embedding_str,
                    config.embedding.model_name
                ))

        if records:
            try:
                execute_batch(self.cursor, insert_sql, records, page_size=50)
                self.conn.commit()
                logger.info(f"Stored {len(records)} incident embeddings")
            except Exception as e:
                self.conn.rollback()
                logger.error(f"Error storing incident embeddings: {e}")

    def generate_resolution_embeddings(self):
        """Generate embeddings for all resolutions."""
        logger.info("Generating resolution embeddings...")

        if self.conn is None or self.model is None:
            logger.error("Database or model not available")
            return

        # Fetch resolutions without embeddings
        self.cursor.execute("""
            SELECT r.resolution_id, r.incident_id, r.resolution_type,
                   r.title, r.description, r.root_cause, r.fix_applied,
                   r.workaround, r.preventive_action
            FROM resolutions r
            LEFT JOIN resolution_embeddings re ON r.resolution_id = re.resolution_id
            WHERE re.embedding_id IS NULL
        """)

        resolutions = self.cursor.fetchall()
        logger.info(f"Found {len(resolutions)} resolutions without embeddings")

        if not resolutions:
            return

        # Prepare text for embedding
        texts = []
        for res in resolutions:
            text = self._create_resolution_text(res)
            texts.append(text)

        # Generate embeddings
        embeddings = self.generate_batch_embeddings(texts)

        # Store embeddings
        insert_sql = """
            INSERT INTO resolution_embeddings (resolution_id, text_content, embedding, model_name)
            VALUES (%s, %s, %s::vector, %s)
            ON CONFLICT (resolution_id) DO UPDATE SET
                text_content = EXCLUDED.text_content,
                embedding = EXCLUDED.embedding,
                created_at = CURRENT_TIMESTAMP
        """

        records = []
        for res, text, embedding in zip(resolutions, texts, embeddings):
            if embedding is not None:
                embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                records.append((
                    res['resolution_id'],
                    text,
                    embedding_str,
                    config.embedding.model_name
                ))

        if records:
            try:
                execute_batch(self.cursor, insert_sql, records, page_size=50)
                self.conn.commit()
                logger.info(f"Stored {len(records)} resolution embeddings")
            except Exception as e:
                self.conn.rollback()
                logger.error(f"Error storing resolution embeddings: {e}")

    def generate_knowledge_embeddings(self, knowledge_items: List[Dict[str, Any]]):
        """Generate embeddings for knowledge base items."""
        logger.info(f"Generating embeddings for {len(knowledge_items)} knowledge items...")

        if self.conn is None or self.model is None:
            logger.error("Database or model not available")
            return

        # Prepare text for embedding
        texts = []
        for item in knowledge_items:
            text = f"{item['title']}\n{item['content']}"
            texts.append(text)

        # Generate embeddings
        embeddings = self.generate_batch_embeddings(texts)

        # Store embeddings
        insert_sql = """
            INSERT INTO knowledge_embeddings (knowledge_id, title, content, category, tags, embedding, model_name)
            VALUES (%s, %s, %s, %s, %s, %s::vector, %s)
            ON CONFLICT (knowledge_id) DO UPDATE SET
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                category = EXCLUDED.category,
                tags = EXCLUDED.tags,
                embedding = EXCLUDED.embedding,
                updated_at = CURRENT_TIMESTAMP
        """

        records = []
        for item, text, embedding in zip(knowledge_items, texts, embeddings):
            if embedding is not None:
                embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                tags = item.get('tags', [])
                if isinstance(tags, list):
                    tags = '{' + ','.join(f'"{t}"' for t in tags) + '}'

                records.append((
                    item['knowledge_id'],
                    item['title'],
                    item['content'],
                    item.get('category', ''),
                    tags,
                    embedding_str,
                    config.embedding.model_name
                ))

        if records:
            try:
                execute_batch(self.cursor, insert_sql, records, page_size=50)
                self.conn.commit()
                logger.info(f"Stored {len(records)} knowledge embeddings")
            except Exception as e:
                self.conn.rollback()
                logger.error(f"Error storing knowledge embeddings: {e}")

    def _create_incident_text(self, incident: Dict) -> str:
        """Create searchable text from incident data."""
        parts = [
            f"Incident: {incident.get('title', '')}",
            f"Category: {incident.get('category', '')} - {incident.get('subcategory', '')}",
            f"Description: {incident.get('description', '')}"
        ]
        return '\n'.join(parts)

    def _create_resolution_text(self, resolution: Dict) -> str:
        """Create searchable text from resolution data."""
        parts = [
            f"Resolution: {resolution.get('title', '')}",
            f"Type: {resolution.get('resolution_type', '')}",
            f"Description: {resolution.get('description', '')}",
            f"Root Cause: {resolution.get('root_cause', '')}",
            f"Fix Applied: {resolution.get('fix_applied', '')}",
            f"Workaround: {resolution.get('workaround', '')}",
            f"Preventive Action: {resolution.get('preventive_action', '')}"
        ]
        return '\n'.join(p for p in parts if p.split(': ', 1)[-1])

    def generate_all_embeddings(self):
        """Generate all embeddings."""
        logger.info("Starting full embedding generation...")

        self.generate_incident_embeddings()
        self.generate_resolution_embeddings()

        # Generate sample knowledge base embeddings
        sample_knowledge = self._get_sample_knowledge_items()
        self.generate_knowledge_embeddings(sample_knowledge)

        logger.info("Embedding generation complete!")

    def _get_sample_knowledge_items(self) -> List[Dict[str, Any]]:
        """Generate sample knowledge base items."""
        return [
            {
                "knowledge_id": "KB0001",
                "title": "Database Connection Pool Exhaustion",
                "content": """
                    Problem: Application fails to connect to database with 'connection pool exhausted' error.

                    Symptoms:
                    - Application timeouts
                    - Database shows max connections reached
                    - Slow response times before failure

                    Root Cause: Usually caused by connection leaks, long-running queries, or undersized pool.

                    Resolution:
                    1. Identify connection leaks in application code
                    2. Check for long-running queries: SELECT * FROM pg_stat_activity
                    3. Kill idle connections if needed
                    4. Increase pool size if legitimate need
                    5. Implement connection timeout settings

                    Prevention:
                    - Use connection pooling library (HikariCP, pgBouncer)
                    - Set appropriate timeouts
                    - Monitor connection usage
                    - Implement circuit breakers
                """,
                "category": "Database",
                "tags": ["database", "connection", "pool", "timeout"]
            },
            {
                "knowledge_id": "KB0002",
                "title": "High CPU Usage on Application Server",
                "content": """
                    Problem: Application server experiencing sustained high CPU usage.

                    Diagnosis:
                    1. Use `top` or `htop` to identify process
                    2. Check application threads: jstack (Java), py-spy (Python)
                    3. Review recent deployments
                    4. Check for infinite loops or inefficient algorithms

                    Resolution:
                    1. If specific process: Restart or debug
                    2. If GC: Tune JVM parameters
                    3. If algorithmic: Profile and optimize
                    4. If load: Scale horizontally

                    Prevention:
                    - Implement CPU usage alerts at 70%
                    - Regular performance testing
                    - Code review for efficiency
                """,
                "category": "Performance",
                "tags": ["cpu", "performance", "server", "optimization"]
            },
            {
                "knowledge_id": "KB0003",
                "title": "SSL/TLS Certificate Expiration",
                "content": """
                    Problem: Service unavailable due to expired SSL certificate.

                    Impact: All HTTPS traffic fails with certificate errors.

                    Immediate Fix:
                    1. Obtain new certificate
                    2. Install on load balancer/server
                    3. Verify certificate chain
                    4. Test connectivity

                    Prevention:
                    - Implement certificate monitoring
                    - Use Let's Encrypt with auto-renewal
                    - Set calendar reminders 30/14/7 days before expiry
                    - Use cert-manager in Kubernetes
                """,
                "category": "Security",
                "tags": ["ssl", "tls", "certificate", "security"]
            },
            {
                "knowledge_id": "KB0004",
                "title": "Memory Leak in Application",
                "content": """
                    Problem: Application memory usage grows continuously until OOM kill or crash.

                    Diagnosis:
                    1. Monitor memory over time
                    2. Use heap dump analysis (MAT for Java, memory_profiler for Python)
                    3. Check for unclosed resources
                    4. Review recent code changes

                    Resolution:
                    1. Identify leaking objects
                    2. Fix resource cleanup (use try-with-resources, context managers)
                    3. Check caching policies
                    4. Verify third-party library versions

                    Prevention:
                    - Regular memory profiling
                    - Set memory limits with alerts
                    - Code review for resource management
                """,
                "category": "Application",
                "tags": ["memory", "leak", "oom", "application"]
            },
            {
                "knowledge_id": "KB0005",
                "title": "Kubernetes Pod CrashLoopBackOff",
                "content": """
                    Problem: Pods repeatedly crash and restart.

                    Diagnosis:
                    1. kubectl describe pod <pod-name>
                    2. kubectl logs <pod-name> --previous
                    3. Check resource limits
                    4. Verify configuration

                    Common Causes:
                    - Missing config/secrets
                    - Resource constraints
                    - Readiness/liveness probe failures
                    - Application startup errors

                    Resolution:
                    1. Fix configuration issues
                    2. Adjust resource limits
                    3. Fix probe configurations
                    4. Debug application startup
                """,
                "category": "Container",
                "tags": ["kubernetes", "container", "pod", "crash"]
            }
        ]

    def search_similar(
        self,
        query: str,
        table: str = "incident_embeddings",
        limit: int = 5,
        threshold: float = 0.7
    ) -> List[Dict]:
        """Search for similar items using vector similarity."""
        if self.conn is None or self.model is None:
            return []

        # Generate query embedding
        query_embedding = self.generate_embedding(query)
        if query_embedding is None:
            return []

        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'

        # Build query based on table
        if table == "incident_embeddings":
            sql = """
                SELECT
                    ie.incident_id,
                    ie.text_content,
                    i.incident_number,
                    i.title,
                    i.severity,
                    1 - (ie.embedding <=> %s::vector) as similarity
                FROM incident_embeddings ie
                JOIN incidents i ON ie.incident_id = i.incident_id
                WHERE 1 - (ie.embedding <=> %s::vector) >= %s
                ORDER BY ie.embedding <=> %s::vector
                LIMIT %s
            """
        elif table == "resolution_embeddings":
            sql = """
                SELECT
                    re.resolution_id,
                    re.text_content,
                    r.resolution_type,
                    r.fix_applied,
                    r.root_cause,
                    1 - (re.embedding <=> %s::vector) as similarity
                FROM resolution_embeddings re
                JOIN resolutions r ON re.resolution_id = r.resolution_id
                WHERE 1 - (re.embedding <=> %s::vector) >= %s
                ORDER BY re.embedding <=> %s::vector
                LIMIT %s
            """
        elif table == "knowledge_embeddings":
            sql = """
                SELECT
                    knowledge_id,
                    title,
                    content,
                    category,
                    1 - (embedding <=> %s::vector) as similarity
                FROM knowledge_embeddings
                WHERE 1 - (embedding <=> %s::vector) >= %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """
        else:
            return []

        try:
            self.cursor.execute(sql, (embedding_str, embedding_str, threshold, embedding_str, limit))
            results = self.cursor.fetchall()
            return [dict(r) for r in results]
        except Exception as e:
            logger.error(f"Error searching similar items: {e}")
            return []

    def close(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Closed database connection")

    def __del__(self):
        self.close()


def main():
    """Main entry point for embedding generation."""
    generator = EmbeddingGenerator()
    try:
        generator.generate_all_embeddings()

        # Test search
        print("\nTesting similarity search...")
        results = generator.search_similar(
            "database connection timeout error",
            table="incident_embeddings",
            limit=3
        )
        for r in results:
            print(f"  - {r.get('title', r.get('knowledge_id'))}: {r['similarity']:.2%}")

    finally:
        generator.close()


if __name__ == "__main__":
    main()
