-- ============================================================================
-- InfraSight-AI: PostgreSQL Schema Definition
-- Database: infrasight_db
-- Version: 1.0.0
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- ============================================================================
-- ENUM TYPES
-- ============================================================================

CREATE TYPE severity_level AS ENUM ('critical', 'high', 'medium', 'low');
CREATE TYPE status_type AS ENUM ('open', 'in_progress', 'resolved', 'closed', 'pending');
CREATE TYPE priority_level AS ENUM ('P1', 'P2', 'P3', 'P4');
CREATE TYPE change_type AS ENUM ('standard', 'normal', 'emergency');
CREATE TYPE risk_level AS ENUM ('low', 'medium', 'high', 'critical');
CREATE TYPE ci_type AS ENUM ('server', 'database', 'application', 'network', 'storage', 'cloud_service', 'container', 'load_balancer', 'cache', 'message_queue');
CREATE TYPE environment_type AS ENUM ('production', 'staging', 'development', 'testing', 'dr');
CREATE TYPE service_criticality AS ENUM ('platinum', 'gold', 'silver', 'bronze');
CREATE TYPE relationship_type AS ENUM ('depends_on', 'hosts', 'connects_to', 'runs_on', 'uses', 'backed_by');
CREATE TYPE resolution_type AS ENUM ('fix', 'workaround', 'rollback', 'restart', 'configuration_change', 'patch', 'escalation');
CREATE TYPE metric_type AS ENUM ('cpu_usage', 'memory_usage', 'disk_usage', 'network_in', 'network_out', 'request_count', 'error_rate', 'latency_p50', 'latency_p99', 'connection_count');

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Services Table: Business services that depend on infrastructure
CREATE TABLE services (
    service_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_name VARCHAR(255) NOT NULL UNIQUE,
    service_type VARCHAR(100) NOT NULL,
    description TEXT,
    criticality service_criticality NOT NULL DEFAULT 'silver',
    owner VARCHAR(255),
    team VARCHAR(255),
    sla_target_hours DECIMAL(5,2),
    status status_type NOT NULL DEFAULT 'open',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_services_criticality ON services(criticality);
CREATE INDEX idx_services_status ON services(status);
CREATE INDEX idx_services_owner ON services(owner);

-- Configuration Items Table: Infrastructure components
CREATE TABLE configuration_items (
    ci_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ci_name VARCHAR(255) NOT NULL,
    ci_type ci_type NOT NULL,
    service_id UUID REFERENCES services(service_id),
    description TEXT,
    environment environment_type NOT NULL DEFAULT 'production',
    status status_type NOT NULL DEFAULT 'open',
    version VARCHAR(50),
    ip_address INET,
    hostname VARCHAR(255),
    operating_system VARCHAR(100),
    cpu_cores INTEGER,
    memory_gb DECIMAL(10,2),
    storage_gb DECIMAL(10,2),
    cloud_provider VARCHAR(50),
    cloud_region VARCHAR(50),
    cost_per_month DECIMAL(10,2),
    last_health_check TIMESTAMP WITH TIME ZONE,
    health_status VARCHAR(50) DEFAULT 'healthy',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_ci_name_env UNIQUE (ci_name, environment)
);

CREATE INDEX idx_ci_type ON configuration_items(ci_type);
CREATE INDEX idx_ci_service ON configuration_items(service_id);
CREATE INDEX idx_ci_environment ON configuration_items(environment);
CREATE INDEX idx_ci_status ON configuration_items(status);
CREATE INDEX idx_ci_health ON configuration_items(health_status);

-- CI Relationships Table: Dependencies between CIs
CREATE TABLE ci_relationships (
    relationship_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_ci_id UUID NOT NULL REFERENCES configuration_items(ci_id) ON DELETE CASCADE,
    target_ci_id UUID NOT NULL REFERENCES configuration_items(ci_id) ON DELETE CASCADE,
    relationship_type relationship_type NOT NULL,
    strength DECIMAL(3,2) DEFAULT 1.0 CHECK (strength >= 0 AND strength <= 1),
    description TEXT,
    port INTEGER,
    protocol VARCHAR(20),
    is_critical BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT no_self_reference CHECK (source_ci_id != target_ci_id),
    CONSTRAINT unique_relationship UNIQUE (source_ci_id, target_ci_id, relationship_type)
);

CREATE INDEX idx_rel_source ON ci_relationships(source_ci_id);
CREATE INDEX idx_rel_target ON ci_relationships(target_ci_id);
CREATE INDEX idx_rel_type ON ci_relationships(relationship_type);
CREATE INDEX idx_rel_critical ON ci_relationships(is_critical);

-- Incidents Table: IT incidents
CREATE TABLE incidents (
    incident_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_number VARCHAR(20) NOT NULL UNIQUE,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    severity severity_level NOT NULL,
    priority priority_level NOT NULL,
    status status_type NOT NULL DEFAULT 'open',
    affected_ci_id UUID REFERENCES configuration_items(ci_id),
    affected_service_id UUID REFERENCES services(service_id),
    category VARCHAR(100),
    subcategory VARCHAR(100),
    impact_scope VARCHAR(50),
    reported_by VARCHAR(255),
    assigned_to VARCHAR(255),
    assignment_group VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE,
    resolution_time_minutes INTEGER,
    sla_breached BOOLEAN DEFAULT FALSE,
    is_major_incident BOOLEAN DEFAULT FALSE,
    parent_incident_id UUID REFERENCES incidents(incident_id)
);

CREATE INDEX idx_incident_severity ON incidents(severity);
CREATE INDEX idx_incident_priority ON incidents(priority);
CREATE INDEX idx_incident_status ON incidents(status);
CREATE INDEX idx_incident_ci ON incidents(affected_ci_id);
CREATE INDEX idx_incident_service ON incidents(affected_service_id);
CREATE INDEX idx_incident_created ON incidents(created_at);
CREATE INDEX idx_incident_category ON incidents(category);
CREATE INDEX idx_incident_assigned ON incidents(assigned_to);

-- Problems Table: Problem records (patterns from incidents)
CREATE TABLE problems (
    problem_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    problem_number VARCHAR(20) NOT NULL UNIQUE,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    status status_type NOT NULL DEFAULT 'open',
    priority priority_level NOT NULL,
    root_cause TEXT,
    root_cause_ci_id UUID REFERENCES configuration_items(ci_id),
    known_error BOOLEAN DEFAULT FALSE,
    known_error_description TEXT,
    workaround TEXT,
    category VARCHAR(100),
    owner VARCHAR(255),
    assigned_to VARCHAR(255),
    related_incident_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    identified_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_problem_status ON problems(status);
CREATE INDEX idx_problem_priority ON problems(priority);
CREATE INDEX idx_problem_root_cause_ci ON problems(root_cause_ci_id);
CREATE INDEX idx_problem_known_error ON problems(known_error);
CREATE INDEX idx_problem_created ON problems(created_at);

-- Problem-Incident Link Table
CREATE TABLE problem_incidents (
    problem_id UUID REFERENCES problems(problem_id) ON DELETE CASCADE,
    incident_id UUID REFERENCES incidents(incident_id) ON DELETE CASCADE,
    linked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    linked_by VARCHAR(255),
    PRIMARY KEY (problem_id, incident_id)
);

-- Changes Table: Change requests
CREATE TABLE changes (
    change_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    change_number VARCHAR(20) NOT NULL UNIQUE,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    change_type change_type NOT NULL,
    status status_type NOT NULL DEFAULT 'pending',
    risk_level risk_level NOT NULL DEFAULT 'medium',
    computed_risk_score DECIMAL(5,4),
    affected_ci_id UUID REFERENCES configuration_items(ci_id),
    affected_service_id UUID REFERENCES services(service_id),
    category VARCHAR(100),
    reason TEXT,
    implementation_plan TEXT,
    rollback_plan TEXT,
    test_plan TEXT,
    requested_by VARCHAR(255),
    assigned_to VARCHAR(255),
    approved_by VARCHAR(255),
    implemented_by VARCHAR(255),
    scheduled_start TIMESTAMP WITH TIME ZONE,
    scheduled_end TIMESTAMP WITH TIME ZONE,
    actual_start TIMESTAMP WITH TIME ZONE,
    actual_end TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE,
    success BOOLEAN,
    failure_reason TEXT,
    caused_incident BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_change_type ON changes(change_type);
CREATE INDEX idx_change_status ON changes(status);
CREATE INDEX idx_change_risk ON changes(risk_level);
CREATE INDEX idx_change_ci ON changes(affected_ci_id);
CREATE INDEX idx_change_service ON changes(affected_service_id);
CREATE INDEX idx_change_scheduled ON changes(scheduled_start);
CREATE INDEX idx_change_created ON changes(created_at);

-- Change-CI Impact Table (for multi-CI changes)
CREATE TABLE change_affected_cis (
    change_id UUID REFERENCES changes(change_id) ON DELETE CASCADE,
    ci_id UUID REFERENCES configuration_items(ci_id) ON DELETE CASCADE,
    impact_type VARCHAR(50),
    PRIMARY KEY (change_id, ci_id)
);

-- Resolutions Table: How incidents were resolved
CREATE TABLE resolutions (
    resolution_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id UUID NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
    resolution_type resolution_type NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    root_cause TEXT,
    fix_applied TEXT,
    workaround TEXT,
    preventive_action TEXT,
    resolved_by VARCHAR(255),
    time_to_resolve_minutes INTEGER,
    was_effective BOOLEAN DEFAULT TRUE,
    reoccurrence_count INTEGER DEFAULT 0,
    knowledge_article_id VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_resolution_incident ON resolutions(incident_id);
CREATE INDEX idx_resolution_type ON resolutions(resolution_type);
CREATE INDEX idx_resolution_effective ON resolutions(was_effective);
CREATE INDEX idx_resolution_created ON resolutions(created_at);

-- Metrics Usage Table: Infrastructure metrics over time
CREATE TABLE metrics_usage (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ci_id UUID NOT NULL REFERENCES configuration_items(ci_id) ON DELETE CASCADE,
    metric_type metric_type NOT NULL,
    metric_value DECIMAL(15,4) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    threshold_warning DECIMAL(15,4),
    threshold_critical DECIMAL(15,4),
    is_anomaly BOOLEAN DEFAULT FALSE,
    anomaly_score DECIMAL(5,4),
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_metrics_ci ON metrics_usage(ci_id);
CREATE INDEX idx_metrics_type ON metrics_usage(metric_type);
CREATE INDEX idx_metrics_collected ON metrics_usage(collected_at);
CREATE INDEX idx_metrics_anomaly ON metrics_usage(is_anomaly);

-- Create hypertable-like partitioning for metrics (for performance)
-- Note: In production, consider using TimescaleDB extension

-- ============================================================================
-- VECTOR EMBEDDING TABLES (pgvector)
-- ============================================================================

-- Incident Embeddings: Vector representations of incidents for similarity search
CREATE TABLE incident_embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id UUID NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
    text_content TEXT NOT NULL,
    embedding vector(384) NOT NULL,  -- all-MiniLM-L6-v2 produces 384-dim vectors
    model_name VARCHAR(100) DEFAULT 'all-MiniLM-L6-v2',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_incident_embedding UNIQUE (incident_id)
);

-- Create IVFFlat index for approximate nearest neighbor search
CREATE INDEX idx_incident_embedding_vector ON incident_embeddings
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Resolution Embeddings: Vector representations of resolutions
CREATE TABLE resolution_embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resolution_id UUID NOT NULL REFERENCES resolutions(resolution_id) ON DELETE CASCADE,
    text_content TEXT NOT NULL,
    embedding vector(384) NOT NULL,
    model_name VARCHAR(100) DEFAULT 'all-MiniLM-L6-v2',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_resolution_embedding UNIQUE (resolution_id)
);

CREATE INDEX idx_resolution_embedding_vector ON resolution_embeddings
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Knowledge Base Embeddings: General knowledge articles
CREATE TABLE knowledge_embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    knowledge_id VARCHAR(50) NOT NULL UNIQUE,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100),
    tags TEXT[],
    embedding vector(384) NOT NULL,
    model_name VARCHAR(100) DEFAULT 'all-MiniLM-L6-v2',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_knowledge_embedding_vector ON knowledge_embeddings
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================================================
-- ANALYTICS & CACHE TABLES
-- ============================================================================

-- Graph Metrics Cache: Cached results from Neo4j computations
CREATE TABLE graph_metrics_cache (
    cache_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ci_id UUID NOT NULL REFERENCES configuration_items(ci_id) ON DELETE CASCADE,
    centrality_score DECIMAL(10,8),
    pagerank_score DECIMAL(10,8),
    betweenness_score DECIMAL(10,8),
    blast_radius INTEGER,
    upstream_count INTEGER,
    downstream_count INTEGER,
    cluster_id INTEGER,
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_ci_metrics UNIQUE (ci_id)
);

CREATE INDEX idx_graph_metrics_ci ON graph_metrics_cache(ci_id);
CREATE INDEX idx_graph_metrics_centrality ON graph_metrics_cache(centrality_score DESC);

-- Anomaly Detection Results
CREATE TABLE anomaly_detections (
    detection_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ci_id UUID REFERENCES configuration_items(ci_id),
    detection_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    anomaly_score DECIMAL(5,4) NOT NULL,
    severity severity_level NOT NULL,
    baseline_value DECIMAL(15,4),
    current_value DECIMAL(15,4),
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(255),
    acknowledged_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_anomaly_ci ON anomaly_detections(ci_id);
CREATE INDEX idx_anomaly_severity ON anomaly_detections(severity);
CREATE INDEX idx_anomaly_detected ON anomaly_detections(detected_at);

-- ============================================================================
-- AUDIT & HISTORY TABLES
-- ============================================================================

-- Configuration Change History: Track changes to CIs over time
CREATE TABLE ci_history (
    history_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ci_id UUID NOT NULL REFERENCES configuration_items(ci_id) ON DELETE CASCADE,
    change_type VARCHAR(50) NOT NULL,
    field_changed VARCHAR(100),
    old_value TEXT,
    new_value TEXT,
    changed_by VARCHAR(255),
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ci_history_ci ON ci_history(ci_id);
CREATE INDEX idx_ci_history_changed ON ci_history(changed_at);

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Active Incidents View
CREATE VIEW v_active_incidents AS
SELECT
    i.incident_id,
    i.incident_number,
    i.title,
    i.severity,
    i.priority,
    i.status,
    ci.ci_name AS affected_ci,
    ci.ci_type,
    s.service_name AS affected_service,
    s.criticality AS service_criticality,
    i.created_at,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - i.created_at))/60 AS age_minutes
FROM incidents i
LEFT JOIN configuration_items ci ON i.affected_ci_id = ci.ci_id
LEFT JOIN services s ON i.affected_service_id = s.service_id
WHERE i.status IN ('open', 'in_progress');

-- CI Health Dashboard View
CREATE VIEW v_ci_health_dashboard AS
SELECT
    ci.ci_id,
    ci.ci_name,
    ci.ci_type,
    ci.environment,
    ci.health_status,
    s.service_name,
    s.criticality,
    gmc.centrality_score,
    gmc.blast_radius,
    COUNT(DISTINCT i.incident_id) FILTER (WHERE i.status IN ('open', 'in_progress')) AS open_incidents,
    COUNT(DISTINCT c.change_id) FILTER (WHERE c.status = 'pending') AS pending_changes
FROM configuration_items ci
LEFT JOIN services s ON ci.service_id = s.service_id
LEFT JOIN graph_metrics_cache gmc ON ci.ci_id = gmc.ci_id
LEFT JOIN incidents i ON ci.ci_id = i.affected_ci_id
LEFT JOIN changes c ON ci.ci_id = c.affected_ci_id
GROUP BY ci.ci_id, ci.ci_name, ci.ci_type, ci.environment, ci.health_status,
         s.service_name, s.criticality, gmc.centrality_score, gmc.blast_radius;

-- Change Risk Summary View
CREATE VIEW v_change_risk_summary AS
SELECT
    c.change_id,
    c.change_number,
    c.title,
    c.change_type,
    c.risk_level,
    c.computed_risk_score,
    c.status,
    ci.ci_name AS affected_ci,
    ci.ci_type,
    s.service_name,
    s.criticality AS service_criticality,
    gmc.blast_radius,
    gmc.centrality_score,
    c.scheduled_start,
    c.scheduled_end
FROM changes c
LEFT JOIN configuration_items ci ON c.affected_ci_id = ci.ci_id
LEFT JOIN services s ON c.affected_service_id = s.service_id
LEFT JOIN graph_metrics_cache gmc ON ci.ci_id = gmc.ci_id
WHERE c.status IN ('pending', 'open');

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function to search similar incidents using vector similarity
CREATE OR REPLACE FUNCTION search_similar_incidents(
    query_embedding vector(384),
    limit_count INTEGER DEFAULT 5,
    similarity_threshold DECIMAL DEFAULT 0.7
)
RETURNS TABLE (
    incident_id UUID,
    incident_number VARCHAR(20),
    title VARCHAR(500),
    severity severity_level,
    status status_type,
    similarity_score DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        i.incident_id,
        i.incident_number,
        i.title,
        i.severity,
        i.status,
        (1 - (ie.embedding <=> query_embedding))::DECIMAL AS similarity_score
    FROM incident_embeddings ie
    JOIN incidents i ON ie.incident_id = i.incident_id
    WHERE (1 - (ie.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY ie.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Function to search similar resolutions
CREATE OR REPLACE FUNCTION search_similar_resolutions(
    query_embedding vector(384),
    limit_count INTEGER DEFAULT 5,
    similarity_threshold DECIMAL DEFAULT 0.7
)
RETURNS TABLE (
    resolution_id UUID,
    incident_id UUID,
    resolution_type resolution_type,
    title VARCHAR(500),
    fix_applied TEXT,
    workaround TEXT,
    similarity_score DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        r.resolution_id,
        r.incident_id,
        r.resolution_type,
        r.title,
        r.fix_applied,
        r.workaround,
        (1 - (re.embedding <=> query_embedding))::DECIMAL AS similarity_score
    FROM resolution_embeddings re
    JOIN resolutions r ON re.resolution_id = r.resolution_id
    WHERE (1 - (re.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY re.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Function to update timestamps automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update timestamps
CREATE TRIGGER update_services_timestamp
    BEFORE UPDATE ON services
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ci_timestamp
    BEFORE UPDATE ON configuration_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_resolutions_timestamp
    BEFORE UPDATE ON resolutions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SAMPLE QUERIES FOR REFERENCE
-- ============================================================================

/*
-- Find similar incidents to a given incident
SELECT * FROM search_similar_incidents(
    (SELECT embedding FROM incident_embeddings WHERE incident_id = 'your-incident-uuid'),
    10,
    0.6
);

-- Get blast radius for a CI
SELECT
    ci.ci_name,
    gmc.blast_radius,
    gmc.downstream_count
FROM configuration_items ci
JOIN graph_metrics_cache gmc ON ci.ci_id = gmc.ci_id
WHERE ci.ci_id = 'your-ci-uuid';

-- Get high-risk pending changes
SELECT * FROM v_change_risk_summary
WHERE computed_risk_score > 0.7
ORDER BY computed_risk_score DESC;
*/

-- ============================================================================
-- GRANTS (adjust based on your security requirements)
-- ============================================================================

-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO infrasight_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO infrasight_app;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO infrasight_app;
