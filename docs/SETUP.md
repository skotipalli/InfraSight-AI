# InfraSight-AI: Local Setup Guide

This guide provides step-by-step instructions for setting up InfraSight-AI on macOS.

## Prerequisites

- macOS 12.0+ (Monterey or later)
- Python 3.10+
- Homebrew
- 16GB RAM recommended
- 20GB free disk space

## Step 1: Install System Dependencies

```bash
# Update Homebrew
brew update

# Install Python 3.10+ (if not already installed)
brew install python@3.11

# Install PostgreSQL 15
brew install postgresql@15

# Install Neo4j
brew install neo4j

# Install Ollama (for local LLM)
brew install ollama
```

## Step 2: Start Database Services

### PostgreSQL

```bash
# Start PostgreSQL
brew services start postgresql@15

# Create database and user
psql postgres <<EOF
CREATE USER infrasight WITH PASSWORD 'infrasight_pass';
CREATE DATABASE infrasight_db OWNER infrasight;
GRANT ALL PRIVILEGES ON DATABASE infrasight_db TO infrasight;
EOF

# Enable pgvector extension
psql -d infrasight_db <<EOF
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
EOF
```

### Neo4j

```bash
# Start Neo4j
brew services start neo4j

# Access Neo4j Browser at http://localhost:7474
# Default credentials: neo4j/neo4j
# Change password to: infrasight_pass
```

### Ollama (Local LLM)

```bash
# Start Ollama service
ollama serve &

# Pull Llama 3.2 model (this may take a while)
ollama pull llama3.2

# Verify model is available
ollama list
```

## Step 3: Set Up Python Environment

```bash
# Navigate to project directory
cd ~/InfraSight-AI

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

## Step 4: Configure Environment Variables

Create a `.env` file in the project root:

```bash
cat > .env <<EOF
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=infrasight_db
POSTGRES_USER=infrasight
POSTGRES_PASSWORD=infrasight_pass

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=infrasight_pass
NEO4J_DATABASE=neo4j

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Embedding Model
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Application
DEBUG=true
LOG_LEVEL=INFO
EOF
```

## Step 5: Initialize Database Schema

```bash
# Apply PostgreSQL schema
psql -d infrasight_db -f scripts/postgresql_schema.sql

# Apply Neo4j constraints (via Neo4j Browser or cypher-shell)
# Open http://localhost:7474 and run the contents of scripts/neo4j_schema.cypher
```

## Step 6: Generate and Load Sample Data

```bash
# Activate virtual environment if not already active
source venv/bin/activate

# Generate sample CSV data
python scripts/generate_sample_data.py

# Load data into PostgreSQL
python src/ingestion/postgres_loader.py

# Load data into Neo4j
python src/ingestion/neo4j_loader.py
```

## Step 7: Generate Embeddings

```bash
# Generate embeddings for RAG
python src/rag/embedding_generator.py
```

## Step 8: Start the Application

```bash
# Start the Gradio UI
python src/ui/app.py

# Access the UI at http://localhost:7860
```

## Step 9: (Optional) Set Up Apache Airflow

```bash
# Set Airflow home
export AIRFLOW_HOME=~/InfraSight-AI/airflow

# Initialize Airflow database
airflow db init

# Create admin user
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@infrasight.local \
    --password admin

# Start Airflow webserver (in one terminal)
airflow webserver --port 8080

# Start Airflow scheduler (in another terminal)
airflow scheduler

# Access Airflow at http://localhost:8080
```

## Verification Steps

### 1. Verify PostgreSQL Connection

```bash
psql -h localhost -U infrasight -d infrasight_db -c "SELECT count(*) FROM incidents;"
```

Expected output: Count of incidents (should be ~300)

### 2. Verify Neo4j Connection

```bash
# Using cypher-shell
cypher-shell -u neo4j -p infrasight_pass "MATCH (n) RETURN count(n);"
```

Or via Neo4j Browser at http://localhost:7474

### 3. Verify Ollama

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Hello, how are you?",
  "stream": false
}'
```

### 4. Verify Embeddings

```bash
psql -h localhost -U infrasight -d infrasight_db -c \
  "SELECT count(*) FROM incident_embeddings;"
```

## Troubleshooting

### PostgreSQL Connection Issues

```bash
# Check if PostgreSQL is running
brew services list | grep postgresql

# Restart PostgreSQL
brew services restart postgresql@15

# Check logs
tail -f /usr/local/var/log/postgresql@15.log
```

### Neo4j Connection Issues

```bash
# Check if Neo4j is running
brew services list | grep neo4j

# Check Neo4j logs
tail -f /usr/local/var/log/neo4j.log

# Reset Neo4j password if needed
neo4j-admin set-initial-password newpassword
```

### Ollama Issues

```bash
# Check if Ollama is running
curl http://localhost:11434

# Restart Ollama
pkill ollama
ollama serve &
```

### Python Import Errors

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall requirements
pip install -r requirements.txt --force-reinstall
```

## Configuration Options

### Changing the LLM Model

Edit `.env`:
```
OLLAMA_MODEL=llama3.2:70b  # For larger model
```

### Changing Embedding Model

Edit `.env`:
```
EMBEDDING_MODEL=all-mpnet-base-v2  # Higher quality, slower
```

### Production Settings

For production deployment:

```bash
# .env for production
DEBUG=false
LOG_LEVEL=WARNING

# Use stronger passwords
POSTGRES_PASSWORD=<strong-password>
NEO4J_PASSWORD=<strong-password>
```

## Next Steps

1. Explore the UI at http://localhost:7860
2. Try Root Cause Analysis with sample incidents
3. Assess change risks with sample changes
4. Browse the dependency graph
5. Set up Airflow for automated pipelines

## Support

For issues and questions, please refer to:
- [Architecture Documentation](ARCHITECTURE.md)
- [GitHub Issues](https://github.com/your-repo/infrasight-ai/issues)
