"""
InfraSight-AI: Root Cause Analysis Agent
Analyzes incidents to identify root causes using graph traversal.
"""

import logging
from typing import Dict, List, Any
from langchain.tools import Tool

from .base_agent import BaseAgent, AgentResponse, Neo4jTool

logger = logging.getLogger(__name__)


class RCAAgent(BaseAgent):
    """
    Root Cause Analysis Agent

    Uses graph-based analysis to:
    1. Identify the affected CI from an incident
    2. Traverse upstream dependencies to find potential root causes
    3. Calculate blast radius (downstream impact)
    4. Correlate with similar past incidents
    5. Provide ranked root cause candidates
    """

    def __init__(self):
        super().__init__(
            name="RCA Agent",
            description="Analyzes incidents to identify root causes using graph traversal"
        )
        self.neo4j = Neo4jTool()
        self.build_agent()

    def get_tools(self) -> List[Tool]:
        """Return tools for root cause analysis."""
        return [
            Tool(
                name="get_incident_details",
                func=self._get_incident_details,
                description="Get details of an incident by ID or number. Input: incident_id or incident_number"
            ),
            Tool(
                name="find_upstream_dependencies",
                func=self._find_upstream_dependencies,
                description="Find all upstream dependencies of a CI. Input: ci_id"
            ),
            Tool(
                name="calculate_blast_radius",
                func=self._calculate_blast_radius,
                description="Calculate downstream impact (blast radius) for a CI. Input: ci_id"
            ),
            Tool(
                name="get_ci_health_status",
                func=self._get_ci_health_status,
                description="Get current health status of a CI. Input: ci_id"
            ),
            Tool(
                name="find_related_incidents",
                func=self._find_related_incidents,
                description="Find similar past incidents for a CI. Input: ci_id"
            ),
            Tool(
                name="analyze_dependency_path",
                func=self._analyze_dependency_path,
                description="Analyze the dependency path between two CIs. Input: source_ci_id,target_ci_id"
            ),
        ]

    def get_prompt_template(self) -> str:
        """Return the RCA agent prompt template."""
        return """You are an expert IT operations analyst specializing in root cause analysis.

Your task is to analyze an incident and identify the most likely root cause.

You have access to the following tools:
{tools}

Use the following format:
Question: the incident to analyze
Thought: think about what information you need
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (repeat Thought/Action/Action Input/Observation as needed)
Thought: I now have enough information to identify the root cause
Final Answer: A structured analysis including:
- Root Cause: The identified root cause CI and explanation
- Confidence: Your confidence level (high/medium/low)
- Evidence: Supporting evidence from the graph analysis
- Blast Radius: Impact scope
- Recommendations: Suggested actions

Chat History:
{chat_history}

Question: {input}
{agent_scratchpad}"""

    def _get_incident_details(self, incident_identifier: str) -> str:
        """Get incident details from Neo4j."""
        query = """
        MATCH (i:Incident)
        WHERE i.incident_id = $id OR i.incident_number = $id
        OPTIONAL MATCH (i)-[:AFFECTS]->(ci:ConfigurationItem)
        OPTIONAL MATCH (i)-[:RESOLVED_BY]->(r:Resolution)
        RETURN i {.*} as incident,
               ci {.ci_id, .name, .type, .health_status} as affected_ci,
               r {.resolution_type, .root_cause, .fix_applied} as resolution
        """

        results = self.neo4j.query(query, {"id": incident_identifier.strip()})

        if not results:
            return f"No incident found with identifier: {incident_identifier}"

        result = results[0]
        incident = result.get('incident', {})
        ci = result.get('affected_ci', {})
        resolution = result.get('resolution', {})

        return f"""
Incident Details:
- ID: {incident.get('incident_id')}
- Number: {incident.get('incident_number')}
- Title: {incident.get('title')}
- Severity: {incident.get('severity')}
- Status: {incident.get('status')}
- Category: {incident.get('category')}

Affected CI:
- CI ID: {ci.get('ci_id', 'Unknown')}
- Name: {ci.get('name', 'Unknown')}
- Type: {ci.get('type', 'Unknown')}
- Health: {ci.get('health_status', 'Unknown')}

Resolution (if resolved):
- Type: {resolution.get('resolution_type', 'Not resolved')}
- Root Cause: {resolution.get('root_cause', 'Not identified')}
- Fix: {resolution.get('fix_applied', 'Not applied')}
"""

    def _find_upstream_dependencies(self, ci_id: str) -> str:
        """Find upstream dependencies that could be root causes."""
        query = """
        MATCH (ci:ConfigurationItem {ci_id: $ci_id})
        CALL {
            WITH ci
            MATCH path = (ci)-[:DEPENDS_ON|RUNS_ON|BACKED_BY*1..5]->(upstream:ConfigurationItem)
            RETURN upstream, length(path) as depth, nodes(path) as path_nodes
            ORDER BY depth
            LIMIT 20
        }
        RETURN upstream.ci_id as ci_id,
               upstream.name as name,
               upstream.type as type,
               upstream.health_status as health,
               upstream.centrality_score as centrality,
               depth
        ORDER BY
            CASE upstream.health_status
                WHEN 'unhealthy' THEN 0
                WHEN 'degraded' THEN 1
                ELSE 2
            END,
            depth ASC
        """

        results = self.neo4j.query(query, {"ci_id": ci_id.strip()})

        if not results:
            return f"No upstream dependencies found for CI: {ci_id}"

        output = "Upstream Dependencies (potential root causes):\n"
        output += "=" * 50 + "\n"

        for r in results:
            health_indicator = "!" if r['health'] in ['unhealthy', 'degraded'] else " "
            output += f"{health_indicator} [{r['depth']} hops] {r['name']} ({r['type']})\n"
            output += f"   Health: {r['health']}, Centrality: {r.get('centrality', 0):.4f}\n"

        # Highlight unhealthy upstreams
        unhealthy = [r for r in results if r['health'] in ['unhealthy', 'degraded']]
        if unhealthy:
            output += f"\n*** ATTENTION: {len(unhealthy)} unhealthy upstream CIs found! ***\n"
            for u in unhealthy:
                output += f"   -> {u['name']} is {u['health']}\n"

        return output

    def _calculate_blast_radius(self, ci_id: str) -> str:
        """Calculate the blast radius (downstream impact) of a CI."""
        query = """
        MATCH (ci:ConfigurationItem {ci_id: $ci_id})
        CALL {
            WITH ci
            MATCH (ci)<-[:DEPENDS_ON|RUNS_ON|BACKED_BY*1..5]-(downstream:ConfigurationItem)
            RETURN downstream
        }
        WITH ci, collect(DISTINCT downstream) as dependents

        // Get services affected
        OPTIONAL MATCH (s:Service)-[:PROVIDES]->(affected:ConfigurationItem)
        WHERE affected IN dependents OR affected = ci

        RETURN ci.name as ci_name,
               ci.type as ci_type,
               size(dependents) as downstream_count,
               collect(DISTINCT s.name) as affected_services,
               [d IN dependents | {name: d.name, type: d.type}][0..10] as sample_dependents
        """

        results = self.neo4j.query(query, {"ci_id": ci_id.strip()})

        if not results:
            return f"CI not found: {ci_id}"

        r = results[0]

        output = f"""
Blast Radius Analysis for: {r['ci_name']} ({r['ci_type']})
{'=' * 50}

Downstream Impact:
- Total dependent CIs: {r['downstream_count']}
- Affected Services: {', '.join(r['affected_services']) if r['affected_services'] else 'None directly'}

Sample Dependent CIs:
"""
        for dep in r.get('sample_dependents', []):
            output += f"  - {dep['name']} ({dep['type']})\n"

        # Risk assessment
        if r['downstream_count'] > 20:
            output += "\n*** HIGH IMPACT: This CI has significant downstream dependencies! ***\n"
        elif r['downstream_count'] > 5:
            output += "\n** MEDIUM IMPACT: Multiple systems depend on this CI **\n"

        return output

    def _get_ci_health_status(self, ci_id: str) -> str:
        """Get detailed health status of a CI."""
        query = """
        MATCH (ci:ConfigurationItem {ci_id: $ci_id})
        OPTIONAL MATCH (ci)<-[:AFFECTS]-(i:Incident)
        WHERE i.status IN ['open', 'in_progress']
        OPTIONAL MATCH (ci)<-[:MODIFIES]-(c:Change)
        WHERE c.status IN ['pending', 'in_progress']
        RETURN ci {.*} as ci,
               count(DISTINCT i) as open_incidents,
               count(DISTINCT c) as pending_changes,
               collect(DISTINCT i.incident_number)[0..5] as recent_incidents
        """

        results = self.neo4j.query(query, {"ci_id": ci_id.strip()})

        if not results:
            return f"CI not found: {ci_id}"

        r = results[0]
        ci = r['ci']

        return f"""
CI Health Status: {ci.get('name')}
{'=' * 50}
- Type: {ci.get('type')}
- Environment: {ci.get('environment')}
- Current Health: {ci.get('health_status')}
- Status: {ci.get('status')}
- Centrality Score: {ci.get('centrality_score', 0):.4f}
- Risk Score: {ci.get('risk_score', 0):.4f}
- Blast Radius: {ci.get('blast_radius', 0)}

Current Activity:
- Open Incidents: {r['open_incidents']}
- Pending Changes: {r['pending_changes']}
- Recent Incidents: {', '.join(r['recent_incidents']) if r['recent_incidents'] else 'None'}

Resources:
- CPU Cores: {ci.get('cpu_cores')}
- Memory: {ci.get('memory_gb')} GB
- Storage: {ci.get('storage_gb')} GB
- Monthly Cost: ${ci.get('cost_per_month', 0):.2f}
"""

    def _find_related_incidents(self, ci_id: str) -> str:
        """Find similar past incidents for correlation."""
        query = """
        MATCH (ci:ConfigurationItem {ci_id: $ci_id})
        MATCH (ci)<-[:AFFECTS]-(i:Incident)
        WHERE i.status IN ['resolved', 'closed']
        OPTIONAL MATCH (i)-[:RESOLVED_BY]->(r:Resolution)
        RETURN i.incident_number as number,
               i.title as title,
               i.severity as severity,
               i.category as category,
               i.resolution_time_minutes as resolution_time,
               r.root_cause as root_cause,
               r.fix_applied as fix
        ORDER BY i.created_at DESC
        LIMIT 10
        """

        results = self.neo4j.query(query, {"ci_id": ci_id.strip()})

        if not results:
            return f"No past incidents found for CI: {ci_id}"

        output = "Related Past Incidents:\n"
        output += "=" * 50 + "\n"

        for r in results:
            output += f"""
{r['number']}: {r['title']}
  Severity: {r['severity']}, Category: {r['category']}
  Resolution Time: {r['resolution_time']} minutes
  Root Cause: {r['root_cause'] or 'Not documented'}
  Fix: {r['fix'] or 'Not documented'}
---
"""

        return output

    def _analyze_dependency_path(self, input_str: str) -> str:
        """Analyze the path between two CIs."""
        try:
            source_id, target_id = [x.strip() for x in input_str.split(',')]
        except ValueError:
            return "Invalid input. Please provide: source_ci_id,target_ci_id"

        query = """
        MATCH (source:ConfigurationItem {ci_id: $source_id})
        MATCH (target:ConfigurationItem {ci_id: $target_id})
        MATCH path = shortestPath((source)-[*..10]-(target))
        RETURN [n IN nodes(path) | {name: n.name, type: labels(n)[0], health: n.health_status}] as path_nodes,
               length(path) as path_length,
               [r IN relationships(path) | type(r)] as relationship_types
        """

        results = self.neo4j.query(query, {"source_id": source_id, "target_id": target_id})

        if not results:
            return f"No path found between {source_id} and {target_id}"

        r = results[0]

        output = f"Dependency Path Analysis\n"
        output += "=" * 50 + "\n"
        output += f"Path Length: {r['path_length']} hops\n\n"
        output += "Path:\n"

        for i, (node, rel) in enumerate(zip(r['path_nodes'], r['relationship_types'] + [''])):
            health_marker = "!" if node.get('health') == 'unhealthy' else ""
            output += f"  {health_marker}{node['name']} ({node['type']})\n"
            if rel:
                output += f"    --[{rel}]-->\n"

        return output

    def run(self, input_data: Dict[str, Any]) -> AgentResponse:
        """
        Run root cause analysis.

        Args:
            input_data: Dict containing:
                - incident_id: The incident to analyze
                - context: Optional additional context
        """
        incident_id = input_data.get('incident_id')

        if not incident_id:
            return self._create_response(
                success=False,
                result=None,
                reasoning="No incident_id provided"
            )

        try:
            if self.agent_executor:
                # Use LangChain agent
                result = self.agent_executor.invoke({
                    "input": f"Analyze incident {incident_id} and identify the root cause. "
                             f"First get the incident details, then find upstream dependencies, "
                             f"check health status of related CIs, and calculate blast radius."
                })

                return self._create_response(
                    success=True,
                    result=result.get('output'),
                    reasoning="Analysis completed using LangChain agent",
                    confidence=0.8,
                    incident_id=incident_id
                )
            else:
                # Fallback to direct analysis
                return self._run_direct_analysis(incident_id)

        except Exception as e:
            logger.error(f"RCA Agent error: {e}")
            return self._create_response(
                success=False,
                result=str(e),
                reasoning=f"Error during analysis: {e}"
            )

    def _run_direct_analysis(self, incident_id: str) -> AgentResponse:
        """Run analysis directly without LLM."""
        # Get incident details
        incident_info = self._get_incident_details(incident_id)

        # Extract CI ID from incident (simplified parsing)
        # In production, would use proper parsing
        ci_id = None
        for line in incident_info.split('\n'):
            if 'CI ID:' in line:
                ci_id = line.split(':')[1].strip()
                break

        if not ci_id or ci_id == 'Unknown':
            return self._create_response(
                success=False,
                result=incident_info,
                reasoning="Could not identify affected CI"
            )

        # Get upstream dependencies
        upstream = self._find_upstream_dependencies(ci_id)

        # Calculate blast radius
        blast = self._calculate_blast_radius(ci_id)

        # Find related incidents
        related = self._find_related_incidents(ci_id)

        result = f"""
ROOT CAUSE ANALYSIS REPORT
{'=' * 60}

{incident_info}

{upstream}

{blast}

{related}
"""

        return self._create_response(
            success=True,
            result=result,
            reasoning="Direct analysis completed",
            confidence=0.7,
            incident_id=incident_id,
            ci_id=ci_id
        )

    def __del__(self):
        """Cleanup."""
        if hasattr(self, 'neo4j'):
            self.neo4j.close()


# Convenience function for direct use
def analyze_incident(incident_id: str) -> Dict[str, Any]:
    """Analyze an incident for root cause."""
    agent = RCAAgent()
    response = agent.run({"incident_id": incident_id})
    return {
        "success": response.success,
        "result": response.result,
        "reasoning": response.reasoning,
        "confidence": response.confidence,
        "metadata": response.metadata
    }


if __name__ == "__main__":
    # Example usage
    agent = RCAAgent()
    result = agent.run({"incident_id": "INC0000001"})
    print(result.result)
