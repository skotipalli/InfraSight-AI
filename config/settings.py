"""
InfraSight-AI: Configuration Settings
Environment-based configuration for all components.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

@dataclass
class PostgresConfig:
    """PostgreSQL configuration."""
    host: str = os.getenv("POSTGRES_HOST", "localhost")
    port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    database: str = os.getenv("POSTGRES_DB", "infrasight_db")
    user: str = os.getenv("POSTGRES_USER", "infrasight")
    password: str = os.getenv("POSTGRES_PASSWORD", "infrasight_pass")

    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    @property
    def dsn(self) -> dict:
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.database,
            "user": self.user,
            "password": self.password
        }

@dataclass
class Neo4jConfig:
    """Neo4j configuration."""
    uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user: str = os.getenv("NEO4J_USER", "neo4j")
    password: str = os.getenv("NEO4J_PASSWORD", "infrasight_pass")
    database: str = os.getenv("NEO4J_DATABASE", "neo4j")

@dataclass
class OllamaConfig:
    """Ollama LLM configuration."""
    base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    embedding_model: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

@dataclass
class EmbeddingConfig:
    """Embedding model configuration."""
    model_name: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    dimension: int = 384  # all-MiniLM-L6-v2 produces 384-dim vectors
    batch_size: int = 32
    cache_dir: Optional[str] = os.getenv("TRANSFORMERS_CACHE", None)

@dataclass
class AirflowConfig:
    """Airflow configuration."""
    home: str = os.getenv("AIRFLOW_HOME", str(PROJECT_ROOT / "airflow"))
    dags_folder: str = os.getenv("AIRFLOW_DAGS_FOLDER", str(PROJECT_ROOT / "airflow" / "dags"))

@dataclass
class AppConfig:
    """Main application configuration."""
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Sub-configurations
    postgres: PostgresConfig = None
    neo4j: Neo4jConfig = None
    ollama: OllamaConfig = None
    embedding: EmbeddingConfig = None
    airflow: AirflowConfig = None

    def __post_init__(self):
        self.postgres = PostgresConfig()
        self.neo4j = Neo4jConfig()
        self.ollama = OllamaConfig()
        self.embedding = EmbeddingConfig()
        self.airflow = AirflowConfig()

# Global configuration instance
config = AppConfig()

# CSV file mappings
CSV_FILES = {
    "services": RAW_DATA_DIR / "services.csv",
    "configuration_items": RAW_DATA_DIR / "configuration_items.csv",
    "ci_relationships": RAW_DATA_DIR / "ci_relationships.csv",
    "incidents": RAW_DATA_DIR / "incidents.csv",
    "problems": RAW_DATA_DIR / "problems.csv",
    "changes": RAW_DATA_DIR / "changes.csv",
    "resolutions": RAW_DATA_DIR / "resolutions.csv",
    "metrics_usage": RAW_DATA_DIR / "metrics_usage.csv",
}
