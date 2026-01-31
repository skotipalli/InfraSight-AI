// ============================================================================
// InfraSight-AI: Neo4j Graph Model Definition
// Database: neo4j (default)
// Version: 1.0.0
// ============================================================================

// ============================================================================
// CONSTRAINTS (Unique identifiers)
// ============================================================================

// Service constraints
CREATE CONSTRAINT service_id_unique IF NOT EXISTS
FOR (s:Service) REQUIRE s.service_id IS UNIQUE;

CREATE CONSTRAINT service_name_unique IF NOT EXISTS
FOR (s:Service) REQUIRE s.name IS UNIQUE;

// Configuration Item constraints
CREATE CONSTRAINT ci_id_unique IF NOT EXISTS
FOR (ci:ConfigurationItem) REQUIRE ci.ci_id IS UNIQUE;

// Incident constraints
CREATE CONSTRAINT incident_id_unique IF NOT EXISTS
FOR (i:Incident) REQUIRE i.incident_id IS UNIQUE;

CREATE CONSTRAINT incident_number_unique IF NOT EXISTS
FOR (i:Incident) REQUIRE i.incident_number IS UNIQUE;

// Problem constraints
CREATE CONSTRAINT problem_id_unique IF NOT EXISTS
FOR (p:Problem) REQUIRE p.problem_id IS UNIQUE;

CREATE CONSTRAINT problem_number_unique IF NOT EXISTS
FOR (p:Problem) REQUIRE p.problem_number IS UNIQUE;

// Change constraints
CREATE CONSTRAINT change_id_unique IF NOT EXISTS
FOR (c:Change) REQUIRE c.change_id IS UNIQUE;

CREATE CONSTRAINT change_number_unique IF NOT EXISTS
FOR (c:Change) REQUIRE c.change_number IS UNIQUE;

// Resolution constraints
CREATE CONSTRAINT resolution_id_unique IF NOT EXISTS
FOR (r:Resolution) REQUIRE r.resolution_id IS UNIQUE;

// ============================================================================
// INDEXES (Performance optimization)
// ============================================================================

// Service indexes
CREATE INDEX service_criticality_idx IF NOT EXISTS
FOR (s:Service) ON (s.criticality);

CREATE INDEX service_status_idx IF NOT EXISTS
FOR (s:Service) ON (s.status);

// CI indexes
CREATE INDEX ci_type_idx IF NOT EXISTS
FOR (ci:ConfigurationItem) ON (ci.type);

CREATE INDEX ci_environment_idx IF NOT EXISTS
FOR (ci:ConfigurationItem) ON (ci.environment);

CREATE INDEX ci_status_idx IF NOT EXISTS
FOR (ci:ConfigurationItem) ON (ci.status);

CREATE INDEX ci_health_idx IF NOT EXISTS
FOR (ci:ConfigurationItem) ON (ci.health_status);

// Incident indexes
CREATE INDEX incident_severity_idx IF NOT EXISTS
FOR (i:Incident) ON (i.severity);

CREATE INDEX incident_status_idx IF NOT EXISTS
FOR (i:Incident) ON (i.status);

CREATE INDEX incident_created_idx IF NOT EXISTS
FOR (i:Incident) ON (i.created_at);

// Change indexes
CREATE INDEX change_risk_idx IF NOT EXISTS
FOR (c:Change) ON (c.risk_level);

CREATE INDEX change_status_idx IF NOT EXISTS
FOR (c:Change) ON (c.status);

// ============================================================================
// NODE DEFINITIONS (with example creation)
// ============================================================================

// ---------------------------------------------------------------------------
// Service Node
// ---------------------------------------------------------------------------
// Represents a business service
/*
Properties:
  - service_id: STRING (UUID) - Primary key
  - name: STRING - Service name
  - type: STRING - Service type (e.g., 'web_application', 'api_gateway', 'data_pipeline')
  - description: STRING - Service description
  - criticality: STRING - 'platinum', 'gold', 'silver', 'bronze'
  - owner: STRING - Service owner
  - team: STRING - Owning team
  - sla_hours: FLOAT - SLA target in hours
  - status: STRING - 'active', 'inactive', 'deprecated'
  - created_at: DATETIME
  - updated_at: DATETIME
*/

// Example Service creation:
// CREATE (s:Service {
//     service_id: 'svc-001',
//     name: 'Customer Portal',
//     type: 'web_application',
//     criticality: 'platinum',
//     owner: 'John Smith',
//     team: 'Customer Experience',
//     sla_hours: 1.0,
//     status: 'active',
//     created_at: datetime(),
//     updated_at: datetime()
// })

// ---------------------------------------------------------------------------
// ConfigurationItem Node
// ---------------------------------------------------------------------------
// Represents an infrastructure component
/*
Properties:
  - ci_id: STRING (UUID) - Primary key
  - name: STRING - CI name
  - type: STRING - 'server', 'database', 'application', 'network', 'storage',
                   'cloud_service', 'container', 'load_balancer', 'cache', 'message_queue'
  - description: STRING - CI description
  - environment: STRING - 'production', 'staging', 'development', 'testing', 'dr'
  - status: STRING - 'active', 'inactive', 'maintenance', 'decommissioned'
  - version: STRING - Version/release
  - ip_address: STRING - IP address
  - hostname: STRING - Hostname
  - operating_system: STRING - OS details
  - cpu_cores: INTEGER - CPU cores
  - memory_gb: FLOAT - Memory in GB
  - storage_gb: FLOAT - Storage in GB
  - cloud_provider: STRING - AWS, Azure, GCP, etc.
  - cloud_region: STRING - Cloud region
  - cost_per_month: FLOAT - Monthly cost
  - health_status: STRING - 'healthy', 'degraded', 'unhealthy', 'unknown'
  - last_health_check: DATETIME
  - centrality_score: FLOAT - Computed graph centrality
  - pagerank_score: FLOAT - PageRank score
  - blast_radius: INTEGER - Number of dependent CIs
  - risk_score: FLOAT - Computed risk score
  - created_at: DATETIME
  - updated_at: DATETIME
*/

// Example CI creation:
// CREATE (ci:ConfigurationItem {
//     ci_id: 'ci-001',
//     name: 'web-server-prod-01',
//     type: 'server',
//     environment: 'production',
//     status: 'active',
//     hostname: 'web-prod-01.example.com',
//     cpu_cores: 8,
//     memory_gb: 32.0,
//     storage_gb: 500.0,
//     cloud_provider: 'AWS',
//     cloud_region: 'us-east-1',
//     cost_per_month: 250.00,
//     health_status: 'healthy',
//     centrality_score: 0.0,
//     blast_radius: 0,
//     risk_score: 0.0,
//     created_at: datetime(),
//     updated_at: datetime()
// })

// ---------------------------------------------------------------------------
// Incident Node
// ---------------------------------------------------------------------------
// Represents an IT incident
/*
Properties:
  - incident_id: STRING (UUID) - Primary key
  - incident_number: STRING - Human-readable number (INC0001234)
  - title: STRING - Incident title
  - description: STRING - Detailed description
  - severity: STRING - 'critical', 'high', 'medium', 'low'
  - priority: STRING - 'P1', 'P2', 'P3', 'P4'
  - status: STRING - 'open', 'in_progress', 'resolved', 'closed'
  - category: STRING - Incident category
  - subcategory: STRING - Subcategory
  - impact_scope: STRING - 'widespread', 'limited', 'localized'
  - reported_by: STRING
  - assigned_to: STRING
  - assignment_group: STRING
  - created_at: DATETIME
  - acknowledged_at: DATETIME
  - resolved_at: DATETIME
  - resolution_time_minutes: INTEGER
  - sla_breached: BOOLEAN
  - is_major_incident: BOOLEAN
*/

// ---------------------------------------------------------------------------
// Problem Node
// ---------------------------------------------------------------------------
// Represents a problem record (root cause of incidents)
/*
Properties:
  - problem_id: STRING (UUID) - Primary key
  - problem_number: STRING - Human-readable number (PRB0001234)
  - title: STRING - Problem title
  - description: STRING - Detailed description
  - status: STRING - 'open', 'in_progress', 'known_error', 'resolved', 'closed'
  - priority: STRING - 'P1', 'P2', 'P3', 'P4'
  - root_cause: STRING - Root cause description
  - known_error: BOOLEAN - Is this a known error?
  - workaround: STRING - Workaround description
  - owner: STRING
  - assigned_to: STRING
  - related_incident_count: INTEGER
  - created_at: DATETIME
  - resolved_at: DATETIME
*/

// ---------------------------------------------------------------------------
// Change Node
// ---------------------------------------------------------------------------
// Represents a change request
/*
Properties:
  - change_id: STRING (UUID) - Primary key
  - change_number: STRING - Human-readable number (CHG0001234)
  - title: STRING - Change title
  - description: STRING - Detailed description
  - change_type: STRING - 'standard', 'normal', 'emergency'
  - status: STRING - 'pending', 'approved', 'scheduled', 'implementing', 'completed', 'failed', 'cancelled'
  - risk_level: STRING - 'low', 'medium', 'high', 'critical'
  - computed_risk_score: FLOAT - AI-computed risk score
  - category: STRING
  - implementation_plan: STRING
  - rollback_plan: STRING
  - requested_by: STRING
  - approved_by: STRING
  - implemented_by: STRING
  - scheduled_start: DATETIME
  - scheduled_end: DATETIME
  - actual_start: DATETIME
  - actual_end: DATETIME
  - success: BOOLEAN
  - caused_incident: BOOLEAN
  - created_at: DATETIME
*/

// ---------------------------------------------------------------------------
// Resolution Node
// ---------------------------------------------------------------------------
// Represents how an incident was resolved
/*
Properties:
  - resolution_id: STRING (UUID) - Primary key
  - resolution_type: STRING - 'fix', 'workaround', 'rollback', 'restart', 'patch'
  - title: STRING - Resolution title
  - description: STRING - What was done
  - root_cause: STRING - Root cause description
  - fix_applied: STRING - Fix description
  - workaround: STRING - Workaround used
  - preventive_action: STRING - Recommended prevention
  - resolved_by: STRING
  - time_to_resolve_minutes: INTEGER
  - was_effective: BOOLEAN
  - reoccurrence_count: INTEGER
  - created_at: DATETIME
*/

// ============================================================================
// RELATIONSHIP DEFINITIONS
// ============================================================================

// ---------------------------------------------------------------------------
// Service Relationships
// ---------------------------------------------------------------------------

// Service PROVIDES ConfigurationItem
// A service is provided by one or more CIs
// (:Service)-[:PROVIDES]->(:ConfigurationItem)
/*
Properties:
  - role: STRING - Role of CI in service ('primary', 'secondary', 'support')
  - created_at: DATETIME
*/

// ---------------------------------------------------------------------------
// CI Dependency Relationships
// ---------------------------------------------------------------------------

// CI DEPENDS_ON CI
// Core dependency relationship
// (:ConfigurationItem)-[:DEPENDS_ON]->(:ConfigurationItem)
/*
Properties:
  - strength: FLOAT - Dependency strength (0.0 to 1.0)
  - is_critical: BOOLEAN - Is this a critical dependency?
  - description: STRING - Dependency description
  - created_at: DATETIME
*/

// CI HOSTS CI
// One CI hosts another (e.g., server hosts application)
// (:ConfigurationItem)-[:HOSTS]->(:ConfigurationItem)
/*
Properties:
  - created_at: DATETIME
*/

// CI CONNECTS_TO CI
// Network connectivity
// (:ConfigurationItem)-[:CONNECTS_TO]->(:ConfigurationItem)
/*
Properties:
  - protocol: STRING - 'TCP', 'UDP', 'HTTP', 'HTTPS', etc.
  - port: INTEGER - Port number
  - encrypted: BOOLEAN
  - created_at: DATETIME
*/

// CI RUNS_ON CI
// Application runs on infrastructure
// (:ConfigurationItem)-[:RUNS_ON]->(:ConfigurationItem)
/*
Properties:
  - created_at: DATETIME
*/

// CI BACKED_BY CI
// Data is backed by storage/database
// (:ConfigurationItem)-[:BACKED_BY]->(:ConfigurationItem)
/*
Properties:
  - replication: STRING - 'sync', 'async', 'none'
  - created_at: DATETIME
*/

// ---------------------------------------------------------------------------
// Incident Relationships
// ---------------------------------------------------------------------------

// Incident AFFECTS CI
// Incident affects a configuration item
// (:Incident)-[:AFFECTS]->(:ConfigurationItem)
/*
Properties:
  - impact_level: STRING - 'direct', 'indirect'
  - created_at: DATETIME
*/

// Incident CAUSED_BY CI
// Root cause CI for the incident
// (:Incident)-[:CAUSED_BY]->(:ConfigurationItem)
/*
Properties:
  - confidence: FLOAT - Confidence score
  - determined_at: DATETIME
*/

// Incident RESOLVED_BY Resolution
// How the incident was resolved
// (:Incident)-[:RESOLVED_BY]->(:Resolution)
/*
Properties:
  - created_at: DATETIME
*/

// Incident RELATED_TO Incident
// Related incidents
// (:Incident)-[:RELATED_TO]->(:Incident)
/*
Properties:
  - relationship_type: STRING - 'duplicate', 'parent_child', 'caused_by'
  - created_at: DATETIME
*/

// ---------------------------------------------------------------------------
// Problem Relationships
// ---------------------------------------------------------------------------

// Problem RELATES_TO Incident
// Problem is related to incidents
// (:Problem)-[:RELATES_TO]->(:Incident)
/*
Properties:
  - linked_at: DATETIME
  - linked_by: STRING
*/

// Problem ROOT_CAUSE CI
// Root cause CI for the problem
// (:Problem)-[:ROOT_CAUSE]->(:ConfigurationItem)
/*
Properties:
  - confidence: FLOAT
  - identified_at: DATETIME
*/

// ---------------------------------------------------------------------------
// Change Relationships
// ---------------------------------------------------------------------------

// Change MODIFIES CI
// Change affects a CI
// (:Change)-[:MODIFIES]->(:ConfigurationItem)
/*
Properties:
  - modification_type: STRING - 'config', 'upgrade', 'patch', 'replacement'
  - created_at: DATETIME
*/

// Change TRIGGERS Incident
// Change caused an incident
// (:Change)-[:TRIGGERS]->(:Incident)
/*
Properties:
  - identified_at: DATETIME
*/

// ============================================================================
// GRAPH ALGORITHMS SETUP (GDS Library)
// ============================================================================

// Create graph projection for dependency analysis
// CALL gds.graph.project(
//     'ci-dependencies',
//     'ConfigurationItem',
//     {
//         DEPENDS_ON: {
//             orientation: 'NATURAL',
//             properties: ['strength']
//         },
//         HOSTS: {orientation: 'NATURAL'},
//         CONNECTS_TO: {orientation: 'NATURAL'},
//         RUNS_ON: {orientation: 'NATURAL'}
//     }
// )

// ============================================================================
// UTILITY QUERIES
// ============================================================================

// ---------------------------------------------------------------------------
// Query 1: Find all downstream dependencies (Blast Radius)
// ---------------------------------------------------------------------------
// MATCH (ci:ConfigurationItem {ci_id: $ci_id})
// CALL apoc.path.subgraphNodes(ci, {
//     relationshipFilter: '<DEPENDS_ON|<HOSTS|<RUNS_ON',
//     minLevel: 1,
//     maxLevel: 10
// }) YIELD node
// RETURN node.ci_id AS ci_id, node.name AS name, node.type AS type

// ---------------------------------------------------------------------------
// Query 2: Find root cause candidates for an incident
// ---------------------------------------------------------------------------
// MATCH (i:Incident {incident_id: $incident_id})-[:AFFECTS]->(affected:ConfigurationItem)
// MATCH path = (affected)-[:DEPENDS_ON*1..5]->(upstream:ConfigurationItem)
// WHERE upstream.health_status = 'unhealthy'
// RETURN upstream.ci_id AS ci_id,
//        upstream.name AS name,
//        length(path) AS distance,
//        upstream.health_status AS health
// ORDER BY distance ASC

// ---------------------------------------------------------------------------
// Query 3: Calculate change risk based on graph metrics
// ---------------------------------------------------------------------------
// MATCH (c:Change {change_id: $change_id})-[:MODIFIES]->(ci:ConfigurationItem)
// OPTIONAL MATCH (ci)<-[:DEPENDS_ON*1..3]-(dependent:ConfigurationItem)
// WITH ci, count(DISTINCT dependent) AS downstream_count
// OPTIONAL MATCH (ci)-[:DEPENDS_ON*1..3]->(upstream:ConfigurationItem)
// WITH ci, downstream_count, count(DISTINCT upstream) AS upstream_count
// RETURN ci.ci_id AS ci_id,
//        ci.name AS ci_name,
//        ci.centrality_score AS centrality,
//        downstream_count,
//        upstream_count,
//        (ci.centrality_score * 0.3 +
//         downstream_count * 0.01 * 0.25 +
//         upstream_count * 0.01 * 0.2) AS risk_score

// ---------------------------------------------------------------------------
// Query 4: Find orphaned CIs (no dependencies)
// ---------------------------------------------------------------------------
// MATCH (ci:ConfigurationItem)
// WHERE NOT (ci)-[:DEPENDS_ON]-()
//   AND NOT ()-[:DEPENDS_ON]->(ci)
//   AND NOT (ci)-[:HOSTS]-()
//   AND NOT ()-[:HOSTS]->(ci)
// RETURN ci.ci_id AS ci_id,
//        ci.name AS name,
//        ci.type AS type,
//        ci.cost_per_month AS cost

// ---------------------------------------------------------------------------
// Query 5: Service impact analysis
// ---------------------------------------------------------------------------
// MATCH (s:Service {service_id: $service_id})-[:PROVIDES]->(ci:ConfigurationItem)
// MATCH path = (ci)-[:DEPENDS_ON*0..5]->(dependency:ConfigurationItem)
// RETURN DISTINCT dependency.ci_id AS ci_id,
//        dependency.name AS name,
//        dependency.type AS type,
//        dependency.health_status AS health,
//        length(path) AS depth

// ---------------------------------------------------------------------------
// Query 6: Find similar past incidents for a CI
// ---------------------------------------------------------------------------
// MATCH (ci:ConfigurationItem {ci_id: $ci_id})<-[:AFFECTS]-(i:Incident)
// WHERE i.status = 'resolved'
// OPTIONAL MATCH (i)-[:RESOLVED_BY]->(r:Resolution)
// RETURN i.incident_id AS incident_id,
//        i.title AS title,
//        i.severity AS severity,
//        i.resolution_time_minutes AS resolution_time,
//        r.fix_applied AS fix,
//        r.root_cause AS root_cause
// ORDER BY i.created_at DESC
// LIMIT 10

// ---------------------------------------------------------------------------
// Query 7: Compute PageRank for CI importance
// ---------------------------------------------------------------------------
// CALL gds.pageRank.stream('ci-dependencies')
// YIELD nodeId, score
// WITH gds.util.asNode(nodeId) AS ci, score
// SET ci.pagerank_score = score
// RETURN ci.ci_id AS ci_id, ci.name AS name, score
// ORDER BY score DESC
// LIMIT 20

// ---------------------------------------------------------------------------
// Query 8: Detect configuration drift (changed relationships)
// ---------------------------------------------------------------------------
// MATCH (ci:ConfigurationItem)
// WHERE ci.updated_at > datetime() - duration('P7D')
// OPTIONAL MATCH (ci)-[r:DEPENDS_ON]->(target:ConfigurationItem)
// WHERE r.created_at > datetime() - duration('P7D')
// RETURN ci.ci_id AS ci_id,
//        ci.name AS ci_name,
//        collect({target: target.name, created: r.created_at}) AS new_dependencies

// ============================================================================
// DATA LOADING PROCEDURES
// ============================================================================

// Load Services from CSV
// LOAD CSV WITH HEADERS FROM 'file:///services.csv' AS row
// CREATE (s:Service {
//     service_id: row.service_id,
//     name: row.service_name,
//     type: row.service_type,
//     criticality: row.criticality,
//     owner: row.owner,
//     team: row.team,
//     status: row.status,
//     created_at: datetime(row.created_at)
// })

// Load CIs from CSV
// LOAD CSV WITH HEADERS FROM 'file:///configuration_items.csv' AS row
// CREATE (ci:ConfigurationItem {
//     ci_id: row.ci_id,
//     name: row.ci_name,
//     type: row.ci_type,
//     environment: row.environment,
//     status: row.status,
//     version: row.version,
//     ip_address: row.ip_address,
//     hostname: row.hostname,
//     cost_per_month: toFloat(row.cost_per_month),
//     health_status: 'healthy',
//     centrality_score: 0.0,
//     blast_radius: 0,
//     risk_score: 0.0,
//     created_at: datetime(row.created_at)
// })

// Load CI Relationships from CSV
// LOAD CSV WITH HEADERS FROM 'file:///ci_relationships.csv' AS row
// MATCH (source:ConfigurationItem {ci_id: row.source_ci_id})
// MATCH (target:ConfigurationItem {ci_id: row.target_ci_id})
// CALL apoc.create.relationship(source, row.relationship_type,
//     {strength: toFloat(row.strength), is_critical: row.is_critical = 'true'},
//     target) YIELD rel
// RETURN count(rel)

// Link Services to CIs
// MATCH (s:Service), (ci:ConfigurationItem)
// WHERE ci.service_id = s.service_id
// CREATE (s)-[:PROVIDES]->(ci)
