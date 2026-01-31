"""
InfraSight-AI: Remediation Recommendation Agent
Recommends fixes, workarounds, and preventive actions using RAG.
"""

import logging
from typing import Dict, List, Any, Optional
from langchain.tools import Tool

from .base_agent import BaseAgent, AgentResponse, Neo4jTool, PostgresTool

logger = logging.getLogger(__name__)


class RemediationAgent(BaseAgent):
    """
    Remediation Recommendation Agent

    Uses RAG (Retrieval-Augmented Generation) to:
    1. Find similar past incidents and their resolutions
    2. Retrieve relevant knowledge base articles
    3. Analyze graph context for the affected CI
    4. Generate tailored remediation recommendations
    5. Suggest preventive actions
    """

    def __init__(self):
        super().__init__(
            name="Remediation Agent",
            description="Recommends fixes, workarounds, and preventive actions using RAG"
        )
        self.neo4j = Neo4jTool()
        self.postgres = PostgresTool()
        self.embedding_model = None
        self._load_embedding_model()
        self.build_agent()

    def _load_embedding_model(self):
        """Load the embedding model for similarity search."""
        try:
            from sentence_transformers import SentenceTransformer
            from config.settings import config
            self.embedding_model = SentenceTransformer(config.embedding.model_name)
            logger.info(f"Loaded embedding model: {config.embedding.model_name}")
        except ImportError:
            logger.warning("sentence-transformers not installed. RAG will use keyword search.")

    def get_tools(self) -> List[Tool]:
        """Return tools for remediation recommendation."""
        return [
            Tool(
                name="get_incident_context",
                func=self._get_incident_context,
                description="Get full context of an incident including affected CI and service. Input: incident_id"
            ),
            Tool(
                name="search_similar_incidents",
                func=self._search_similar_incidents,
                description="Find similar past incidents using semantic search. Input: incident_description"
            ),
            Tool(
                name="get_past_resolutions",
                func=self._get_past_resolutions,
                description="Get resolutions from similar past incidents. Input: ci_id"
            ),
            Tool(
                name="search_knowledge_base",
                func=self._search_knowledge_base,
                description="Search knowledge base for relevant articles. Input: search_query"
            ),
            Tool(
                name="get_ci_runbook",
                func=self._get_ci_runbook,
                description="Get runbook/playbook for a CI type. Input: ci_type"
            ),
            Tool(
                name="generate_remediation_plan",
                func=self._generate_remediation_plan,
                description="Generate a remediation plan based on gathered context. Input: incident_id,context_summary"
            ),
        ]

    def get_prompt_template(self) -> str:
        """Return the remediation agent prompt template."""
        return """You are an expert IT operations engineer specializing in incident remediation.

Your task is to recommend fixes, workarounds, and preventive actions for incidents.

You have access to the following tools:
{tools}

When recommending remediation:
1. First understand the incident context
2. Search for similar past incidents and their resolutions
3. Look for relevant knowledge base articles
4. Consider the CI type and environment
5. Provide clear, actionable recommendations

Use the following format:
Question: the incident to remediate
Thought: consider what information is needed
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (repeat as needed)
Thought: I now have enough information to recommend remediation
Final Answer: A structured remediation recommendation including:
- Immediate Fix: Steps to resolve the incident now
- Workaround: Temporary solution if fix is not immediately possible
- Root Cause Fix: Long-term solution addressing the underlying issue
- Preventive Actions: Steps to prevent recurrence
- Estimated Time: Approximate time for each action

Chat History:
{chat_history}

Question: {input}
{agent_scratchpad}"""

    def _get_incident_context(self, incident_id: str) -> str:
        """Get full context of an incident."""
        query = """
        MATCH (i:Incident {incident_id: $id})
        OPTIONAL MATCH (i)-[:AFFECTS]->(ci:ConfigurationItem)
        OPTIONAL MATCH (s:Service)-[:PROVIDES]->(ci)
        OPTIONAL MATCH (ci)-[:DEPENDS_ON*1..2]->(upstream:ConfigurationItem)
        RETURN i {.*} as incident,
               ci {.*} as affected_ci,
               s {.name, .criticality, .sla_hours} as service,
               collect(DISTINCT upstream {.name, .type, .health_status})[0..5] as upstream_deps
        """

        results = self.neo4j.query(query, {"id": incident_id.strip()})

        if not results:
            return f"Incident not found: {incident_id}"

        r = results[0]
        inc = r.get('incident', {})
        ci = r.get('affected_ci', {})
        svc = r.get('service', {})
        upstream = r.get('upstream_deps', [])

        return f"""
INCIDENT CONTEXT
{'=' * 50}

Incident:
- Number: {inc.get('incident_number')}
- Title: {inc.get('title')}
- Description: {inc.get('description')}
- Severity: {inc.get('severity')}
- Priority: {inc.get('priority')}
- Category: {inc.get('category')}
- Subcategory: {inc.get('subcategory')}
- Status: {inc.get('status')}

Affected CI:
- Name: {ci.get('name', 'Unknown')}
- Type: {ci.get('type', 'Unknown')}
- Environment: {ci.get('environment', 'Unknown')}
- Health: {ci.get('health_status', 'Unknown')}
- Cloud: {ci.get('cloud_provider', 'Unknown')} / {ci.get('cloud_region', 'Unknown')}
- OS: {ci.get('operating_system', 'N/A')}
- Version: {ci.get('version', 'N/A')}

Service:
- Name: {svc.get('name', 'None')}
- Criticality: {svc.get('criticality', 'Unknown')}
- SLA Target: {svc.get('sla_hours', 'N/A')} hours

Upstream Dependencies:
{chr(10).join(f"  - {u['name']} ({u['type']}) - Health: {u['health_status']}" for u in upstream) if upstream else '  None identified'}
"""

    def _search_similar_incidents(self, description: str) -> str:
        """Search for similar incidents using semantic search."""

        if self.embedding_model and self.postgres.conn:
            try:
                # Generate embedding for the query
                query_embedding = self.embedding_model.encode(description)

                # Search using pgvector
                sql = """
                SELECT
                    i.incident_id,
                    i.incident_number,
                    i.title,
                    i.severity,
                    i.category,
                    i.status,
                    r.resolution_type,
                    r.fix_applied,
                    r.root_cause,
                    1 - (ie.embedding <=> %s::vector) as similarity
                FROM incident_embeddings ie
                JOIN incidents i ON ie.incident_id = i.incident_id
                LEFT JOIN resolutions r ON i.incident_id = r.incident_id
                WHERE i.status IN ('resolved', 'closed')
                ORDER BY ie.embedding <=> %s::vector
                LIMIT 5
                """

                # Convert embedding to format PostgreSQL expects
                embedding_str = '[' + ','.join(map(str, query_embedding.tolist())) + ']'
                results = self.postgres.query(sql, (embedding_str, embedding_str))

                if results:
                    output = "Similar Past Incidents (by semantic similarity):\n"
                    output += "=" * 50 + "\n"

                    for r in results:
                        output += f"""
{r['incident_number']}: {r['title']}
  Similarity: {r['similarity']*100:.1f}%
  Severity: {r['severity']}, Category: {r['category']}
  Resolution: {r['resolution_type'] or 'Not documented'}
  Fix Applied: {r['fix_applied'] or 'Not documented'}
  Root Cause: {r['root_cause'] or 'Not identified'}
---
"""
                    return output

            except Exception as e:
                logger.warning(f"Vector search failed: {e}. Falling back to keyword search.")

        # Fallback to keyword search
        return self._keyword_search_incidents(description)

    def _keyword_search_incidents(self, description: str) -> str:
        """Fallback keyword-based search for similar incidents."""
        # Extract keywords
        keywords = [w for w in description.lower().split() if len(w) > 3][:5]

        query = """
        MATCH (i:Incident)
        WHERE i.status IN ['resolved', 'closed']
        AND (
            any(kw IN $keywords WHERE toLower(i.title) CONTAINS kw)
            OR any(kw IN $keywords WHERE toLower(i.description) CONTAINS kw)
        )
        OPTIONAL MATCH (i)-[:RESOLVED_BY]->(r:Resolution)
        RETURN i.incident_number as number,
               i.title as title,
               i.severity as severity,
               i.category as category,
               r.resolution_type as resolution_type,
               r.fix_applied as fix,
               r.root_cause as root_cause
        LIMIT 5
        """

        results = self.neo4j.query(query, {"keywords": keywords})

        if not results:
            return "No similar incidents found based on keyword search."

        output = "Similar Past Incidents (keyword match):\n"
        output += "=" * 50 + "\n"

        for r in results:
            output += f"""
{r['number']}: {r['title']}
  Severity: {r['severity']}, Category: {r['category']}
  Resolution: {r['resolution_type'] or 'Not documented'}
  Fix: {r['fix'] or 'Not documented'}
---
"""
        return output

    def _get_past_resolutions(self, ci_id: str) -> str:
        """Get resolutions from past incidents for this CI."""
        query = """
        MATCH (ci:ConfigurationItem {ci_id: $ci_id})
        MATCH (ci)<-[:AFFECTS]-(i:Incident)-[:RESOLVED_BY]->(r:Resolution)
        WHERE r.was_effective = true
        RETURN r.resolution_type as type,
               r.title as title,
               r.fix_applied as fix,
               r.workaround as workaround,
               r.preventive_action as preventive,
               r.root_cause as root_cause,
               r.time_to_resolve_minutes as resolution_time,
               i.category as category
        ORDER BY r.created_at DESC
        LIMIT 10
        """

        results = self.neo4j.query(query, {"ci_id": ci_id.strip()})

        if not results:
            return f"No past resolutions found for CI: {ci_id}"

        output = "Effective Past Resolutions for this CI:\n"
        output += "=" * 50 + "\n"

        for r in results:
            output += f"""
Type: {r['type']} | Category: {r['category']}
Title: {r['title']}
Fix Applied: {r['fix'] or 'Not documented'}
Workaround: {r['workaround'] or 'None'}
Preventive Action: {r['preventive'] or 'None'}
Root Cause: {r['root_cause'] or 'Not identified'}
Resolution Time: {r['resolution_time'] or 'Unknown'} minutes
---
"""
        return output

    def _search_knowledge_base(self, search_query: str) -> str:
        """Search the knowledge base for relevant articles."""

        if self.embedding_model and self.postgres.conn:
            try:
                query_embedding = self.embedding_model.encode(search_query)

                sql = """
                SELECT
                    knowledge_id,
                    title,
                    content,
                    category,
                    1 - (embedding <=> %s::vector) as similarity
                FROM knowledge_embeddings
                ORDER BY embedding <=> %s::vector
                LIMIT 3
                """

                embedding_str = '[' + ','.join(map(str, query_embedding.tolist())) + ']'
                results = self.postgres.query(sql, (embedding_str, embedding_str))

                if results:
                    output = "Relevant Knowledge Base Articles:\n"
                    output += "=" * 50 + "\n"

                    for r in results:
                        output += f"""
Article: {r['knowledge_id']}
Title: {r['title']}
Category: {r['category']}
Relevance: {r['similarity']*100:.1f}%

Content Summary:
{r['content'][:500]}...
---
"""
                    return output

            except Exception as e:
                logger.warning(f"Knowledge base search failed: {e}")

        return "Knowledge base search not available. Using incident history instead."

    def _get_ci_runbook(self, ci_type: str) -> str:
        """Get runbook/playbook for a CI type."""
        # In production, would retrieve from a document store
        # Here we provide template runbooks

        runbooks = {
            "server": """
SERVER RUNBOOK
==============
Common Issues & Remediation:

1. High CPU Usage
   - Check top processes: `top -o %CPU`
   - Review application logs
   - Consider scaling or resource increase

2. Memory Issues
   - Check memory: `free -m`
   - Identify memory-hungry processes
   - Clear caches if safe: `sync; echo 3 > /proc/sys/vm/drop_caches`

3. Disk Space
   - Check disk: `df -h`
   - Find large files: `du -sh /* | sort -h`
   - Clean logs, temp files

4. Service Not Responding
   - Check service status: `systemctl status <service>`
   - Review logs: `journalctl -u <service> -n 100`
   - Restart if needed: `systemctl restart <service>`
""",
            "database": """
DATABASE RUNBOOK
================
Common Issues & Remediation:

1. Connection Pool Exhaustion
   - Check active connections
   - Identify long-running queries
   - Kill idle connections if needed
   - Increase pool size if appropriate

2. Slow Queries
   - Enable slow query log
   - Use EXPLAIN ANALYZE
   - Add missing indexes
   - Optimize query structure

3. Replication Lag
   - Check replica status
   - Review network latency
   - Consider parallel replication

4. Storage Issues
   - Check tablespace usage
   - Archive old data
   - Optimize/vacuum tables
""",
            "application": """
APPLICATION RUNBOOK
===================
Common Issues & Remediation:

1. Application Crash
   - Check application logs
   - Review stack traces
   - Check for memory leaks
   - Restart with debug logging

2. Performance Degradation
   - Enable APM tracing
   - Profile hot paths
   - Check external dependencies
   - Review recent deployments

3. Configuration Errors
   - Validate config files
   - Check environment variables
   - Review secret management
   - Compare with working config

4. Dependency Failures
   - Check downstream services
   - Verify circuit breakers
   - Test fallback mechanisms
""",
            "network": """
NETWORK RUNBOOK
===============
Common Issues & Remediation:

1. Connectivity Issues
   - Test connectivity: ping, traceroute
   - Check firewall rules
   - Verify DNS resolution
   - Review security groups

2. Latency/Packet Loss
   - Check network utilization
   - Review QoS settings
   - Test alternative paths
   - Contact network team

3. DNS Issues
   - Check DNS servers
   - Flush DNS cache
   - Verify records
   - Check TTLs
"""
        }

        ci_type_lower = ci_type.strip().lower()
        runbook = runbooks.get(ci_type_lower)

        if not runbook:
            return f"""
GENERAL RUNBOOK for {ci_type}
{'=' * 50}
1. Check service/component status
2. Review recent logs
3. Check resource utilization (CPU, Memory, Disk, Network)
4. Review recent changes
5. Check dependencies
6. Restart service if safe
7. Escalate if issue persists
"""

        return runbook

    def _generate_remediation_plan(self, input_str: str) -> str:
        """Generate a structured remediation plan."""
        # Parse input (incident_id,context_summary)
        parts = input_str.split(',', 1)
        incident_id = parts[0].strip()
        context = parts[1] if len(parts) > 1 else ""

        # In production with LLM, this would generate a custom plan
        # For now, provide a structured template

        return f"""
REMEDIATION PLAN FOR {incident_id}
{'=' * 60}

IMMEDIATE ACTIONS (0-30 minutes):
1. Verify incident scope and impact
2. Communicate with stakeholders
3. Gather diagnostic information
4. Apply immediate workaround if available

SHORT-TERM FIX (30 min - 2 hours):
1. Identify root cause from diagnostics
2. Apply targeted fix
3. Verify service restoration
4. Monitor for recurrence

LONG-TERM REMEDIATION (1-7 days):
1. Document root cause analysis
2. Implement permanent fix
3. Update monitoring and alerting
4. Create/update runbook
5. Conduct post-incident review

PREVENTIVE MEASURES:
1. Add automated monitoring for this scenario
2. Implement early warning alerts
3. Review similar systems for same vulnerability
4. Update change management process if applicable
5. Schedule follow-up review

ESCALATION PATH:
- L1: On-call engineer
- L2: Service owner
- L3: Platform team / Vendor support
"""

    def run(self, input_data: Dict[str, Any]) -> AgentResponse:
        """
        Run remediation recommendation.

        Args:
            input_data: Dict containing:
                - incident_id: The incident to remediate
                - description: Optional incident description for search
        """
        incident_id = input_data.get('incident_id')
        description = input_data.get('description', '')

        if not incident_id:
            return self._create_response(
                success=False,
                result=None,
                reasoning="No incident_id provided"
            )

        try:
            if self.agent_executor:
                result = self.agent_executor.invoke({
                    "input": f"Recommend remediation for incident {incident_id}. "
                             f"Get incident context, search for similar incidents, "
                             f"find past resolutions, and generate a remediation plan. "
                             f"Additional context: {description}"
                })

                return self._create_response(
                    success=True,
                    result=result.get('output'),
                    reasoning="Analysis completed using LangChain agent",
                    confidence=0.8,
                    incident_id=incident_id
                )
            else:
                return self._run_direct_recommendation(incident_id, description)

        except Exception as e:
            logger.error(f"Remediation Agent error: {e}")
            return self._create_response(
                success=False,
                result=str(e),
                reasoning=f"Error during recommendation: {e}"
            )

    def _run_direct_recommendation(self, incident_id: str, description: str = "") -> AgentResponse:
        """Run recommendation directly without LLM."""
        # Get incident context
        context = self._get_incident_context(incident_id)

        # Extract CI type for runbook
        ci_type = "application"  # Default
        for line in context.split('\n'):
            if 'Type:' in line and 'CI' not in line:
                ci_type = line.split(':')[1].strip()
                break

        # Search for similar incidents
        search_text = description if description else incident_id
        similar = self._search_similar_incidents(search_text)

        # Get CI runbook
        runbook = self._get_ci_runbook(ci_type)

        # Generate plan
        plan = self._generate_remediation_plan(incident_id + ",auto")

        result = f"""
REMEDIATION RECOMMENDATION REPORT
{'=' * 60}

{context}

SIMILAR PAST INCIDENTS:
{similar}

RELEVANT RUNBOOK:
{runbook}

{plan}
"""

        return self._create_response(
            success=True,
            result=result,
            reasoning="Direct recommendation completed",
            confidence=0.7,
            incident_id=incident_id
        )

    def __del__(self):
        """Cleanup."""
        if hasattr(self, 'neo4j'):
            self.neo4j.close()
        if hasattr(self, 'postgres'):
            self.postgres.close()


def recommend_remediation(incident_id: str, description: str = "") -> Dict[str, Any]:
    """Get remediation recommendations for an incident."""
    agent = RemediationAgent()
    response = agent.run({"incident_id": incident_id, "description": description})
    return {
        "success": response.success,
        "result": response.result,
        "confidence": response.confidence,
        "metadata": response.metadata
    }


if __name__ == "__main__":
    agent = RemediationAgent()
    result = agent.run({"incident_id": "INC0000001"})
    print(result.result)
