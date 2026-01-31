# InfraSight-AI

**AI-driven visibility, prediction, and intelligence for infrastructure**

InfraSight-AI is a production-style demo platform that combines graph analytics, RAG (Retrieval-Augmented Generation), and agentic AI to improve IT operations and incident management for hosting services.

## Features

### 1. Graph-Based Incident Root Cause Analysis & Blast Radius Prediction
- Uses Neo4j to model CI dependencies
- Traverses dependency paths to identify likely root causes
- Predicts downstream impact (blast radius)

### 2. Graph-Driven Service Dependency Mapping
- Build and visualize service → app → infra → cloud dependency graphs
- Understand complex relationships at a glance

### 3. Proactive Detection
- Identify orphaned, redundant, and zombie services
- Detect low-usage but high-cost components
- Configuration drift detection

### 4. Risk-Based Change Approval Automation
- Compute graph-based risk scores for changes
- Auto-classify changes into Low / Medium / High / Critical risk
- Provide approval workflow recommendations

### 5. Predictive Capacity & Saturation Analysis
- Use historical usage metrics to predict future bottlenecks
- 7/14/30 day forecasting

### 6. Anomaly Detection
- Compare historical vs current graph states
- Detect abnormal dependency changes
- Monitor configuration drift

### 7. AI-Powered Knowledge Discovery
- Combine Neo4j graph context + PostgreSQL RAG
- Recommend fixes based on similar past incidents
- Natural language interface

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.10+ |
| Relational DB | PostgreSQL 15 + pgvector |
| Graph DB | Neo4j |
| LLM | Llama 3.2 (via Ollama) |
| AI Framework | LangChain |
| Embeddings | sentence-transformers |
| Data Pipeline | Apache Airflow |
| Web UI | Gradio |

## Project Structure

```
InfraSight-AI/
├── README.md
├── requirements.txt
├── config/
│   └── settings.py              # Configuration management
├── data/
│   ├── raw/                     # CSV source files
│   └── processed/               # Transformed data
├── docs/
│   ├── ARCHITECTURE.md          # Architecture diagrams
│   └── SETUP.md                 # Setup instructions
├── scripts/
│   ├── generate_sample_data.py  # Data generator
│   ├── postgresql_schema.sql    # PostgreSQL DDL
│   └── neo4j_schema.cypher      # Neo4j schema
├── airflow/
│   └── dags/
│       ├── data_ingestion_dag.py
│       └── anomaly_detection_dag.py
└── src/
    ├── agents/
    │   ├── base_agent.py
    │   ├── rca_agent.py         # Root Cause Analysis
    │   ├── change_risk_agent.py # Change Risk Assessment
    │   └── remediation_agent.py # Remediation Recommendations
    ├── ingestion/
    │   ├── postgres_loader.py
    │   └── neo4j_loader.py
    ├── rag/
    │   └── embedding_generator.py
    └── ui/
        └── app.py               # Gradio interface
```

## Quick Start

### Prerequisites

- macOS 12.0+
- Python 3.10+
- Homebrew
- 16GB RAM recommended

### Installation

```bash
# Clone the repository
cd ~/InfraSight-AI

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install databases (macOS)
brew install postgresql@15 neo4j ollama

# Start services
brew services start postgresql@15
brew services start neo4j
ollama serve &
ollama pull llama3.2

# Generate sample data
python scripts/generate_sample_data.py

# Start the UI
python src/ui/app.py
```

Access the UI at: http://localhost:7860

For detailed setup instructions, see [SETUP.md](docs/SETUP.md).

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                       Gradio Web Interface                       │
├─────────────────────────────────────────────────────────────────┤
│                    LangChain Agent Orchestrator                  │
│    ┌─────────────┐   ┌─────────────┐   ┌─────────────────────┐  │
│    │ RCA Agent   │   │ Risk Agent  │   │ Remediation Agent   │  │
│    └─────────────┘   └─────────────┘   └─────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐        ┌─────────────────────────┐    │
│  │  RAG Pipeline       │        │  Graph Analytics        │    │
│  │  (pgvector)         │        │  (Neo4j)                │    │
│  └─────────────────────┘        └─────────────────────────┘    │
├─────────────────────────────────────────────────────────────────┤
│              Llama 3.2 via Ollama (Local LLM)                   │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐        ┌─────────────────────────┐    │
│  │  PostgreSQL 15      │        │  Neo4j                  │    │
│  │  + pgvector         │        │  Graph Database         │    │
│  └─────────────────────┘        └─────────────────────────┘    │
├─────────────────────────────────────────────────────────────────┤
│                      Apache Airflow                              │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────────┐   │
│  │ Ingestion   │   │ Embedding   │   │ Anomaly Detection   │   │
│  │ DAG         │   │ DAG         │   │ DAG                 │   │
│  └─────────────┘   └─────────────┘   └─────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Data Model

### PostgreSQL Tables
- `services` - Business services
- `configuration_items` - Infrastructure components
- `ci_relationships` - Dependencies between CIs
- `incidents` - IT incidents
- `problems` - Problem records
- `changes` - Change requests
- `resolutions` - How incidents were resolved
- `metrics_usage` - Infrastructure metrics
- `incident_embeddings` - Vector embeddings for RAG
- `resolution_embeddings` - Vector embeddings for RAG

### Neo4j Graph Model

**Nodes:**
- `:Service` - Business services
- `:ConfigurationItem` - Infrastructure components
- `:Incident` - IT incidents
- `:Problem` - Problem records
- `:Change` - Change requests
- `:Resolution` - Resolutions

**Relationships:**
- `(:Service)-[:PROVIDES]->(:ConfigurationItem)`
- `(:ConfigurationItem)-[:DEPENDS_ON]->(:ConfigurationItem)`
- `(:ConfigurationItem)-[:HOSTS]->(:ConfigurationItem)`
- `(:Incident)-[:AFFECTS]->(:ConfigurationItem)`
- `(:Incident)-[:RESOLVED_BY]->(:Resolution)`
- `(:Change)-[:MODIFIES]->(:ConfigurationItem)`

## Sample Data

The project includes realistic synthetic data:
- 30 Services
- 300 Configuration Items
- 387 CI Relationships
- 300 Incidents
- 50 Problems
- 250 Changes
- 222 Resolutions
- 3,000 Metrics records

## Agent Capabilities

### RCA Agent
- Incident context retrieval
- Upstream dependency traversal
- Blast radius calculation
- Root cause identification
- Confidence scoring

### Change Risk Agent
- CI criticality analysis
- Historical change success rates
- Graph-based risk scoring
- Conflict detection
- Approval recommendations

### Remediation Agent
- Similar incident retrieval (RAG)
- Knowledge base search
- Runbook lookup
- Fix recommendations
- Preventive actions

## Configuration

Environment variables (`.env`):

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=infrasight_db
POSTGRES_USER=infrasight
POSTGRES_PASSWORD=infrasight_pass

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=infrasight_pass

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

EMBEDDING_MODEL=all-MiniLM-L6-v2
```

## Development

```bash
# Run tests
pytest tests/

# Format code
black src/

# Type checking
mypy src/
```

## License

This project is for demonstration and portfolio purposes.

## Acknowledgments

- LangChain for the agent framework
- Neo4j for graph database capabilities
- Ollama for local LLM inference
- sentence-transformers for embeddings
