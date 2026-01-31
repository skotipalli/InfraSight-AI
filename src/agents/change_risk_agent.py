"""
InfraSight-AI: Change Risk Assessment Agent
Evaluates change requests and computes risk scores based on graph analysis.
"""

import logging
from typing import Dict, List, Any
from langchain.tools import Tool

from .base_agent import BaseAgent, AgentResponse, Neo4jTool, PostgresTool

logger = logging.getLogger(__name__)


class ChangeRiskAgent(BaseAgent):
    """
    Change Risk Assessment Agent

    Evaluates change requests by:
    1. Analyzing the target CI's position in the dependency graph
    2. Computing impact metrics (centrality, blast radius)
    3. Reviewing historical change success/failure rates
    4. Correlating with past incidents caused by changes
    5. Providing risk classification and recommendations
    """

    def __init__(self):
        super().__init__(
            name="Change Risk Agent",
            description="Evaluates change requests and computes risk scores"
        )
        self.neo4j = Neo4jTool()
        self.postgres = PostgresTool()
        self.build_agent()

    def get_tools(self) -> List[Tool]:
        """Return tools for change risk assessment."""
        return [
            Tool(
                name="get_change_details",
                func=self._get_change_details,
                description="Get details of a change request. Input: change_id or change_number"
            ),
            Tool(
                name="analyze_ci_criticality",
                func=self._analyze_ci_criticality,
                description="Analyze the criticality of a CI in the infrastructure. Input: ci_id"
            ),
            Tool(
                name="get_historical_changes",
                func=self._get_historical_changes,
                description="Get historical change success rates for a CI. Input: ci_id"
            ),
            Tool(
                name="compute_change_risk_score",
                func=self._compute_change_risk_score,
                description="Compute the overall risk score for a change. Input: change_id"
            ),
            Tool(
                name="get_maintenance_windows",
                func=self._get_maintenance_windows,
                description="Check if there are safe maintenance windows. Input: ci_id"
            ),
            Tool(
                name="check_conflicting_changes",
                func=self._check_conflicting_changes,
                description="Check for conflicting changes. Input: change_id"
            ),
        ]

    def get_prompt_template(self) -> str:
        """Return the change risk agent prompt template."""
        return """You are an expert change management advisor specializing in risk assessment.

Your task is to evaluate a change request and determine its risk level.

You have access to the following tools:
{tools}

Risk Classification Criteria:
- LOW: Routine changes with minimal impact, good historical success rate
- MEDIUM: Changes affecting moderately critical systems or with some historical issues
- HIGH: Changes affecting critical systems with significant blast radius
- CRITICAL: Emergency changes or changes to highly connected critical systems

Use the following format:
Question: the change request to evaluate
Thought: consider what factors affect the risk
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (repeat as needed)
Thought: I now have enough information to assess the risk
Final Answer: A structured risk assessment including:
- Risk Level: LOW / MEDIUM / HIGH / CRITICAL
- Risk Score: 0.0 to 1.0
- Key Risk Factors: Bullet list of main concerns
- Recommendations: Suggested mitigations or approval workflow
- Approval Recommendation: Auto-approve / Standard approval / CAB review required

Chat History:
{chat_history}

Question: {input}
{agent_scratchpad}"""

    def _get_change_details(self, change_identifier: str) -> str:
        """Get change request details."""
        query = """
        MATCH (c:Change)
        WHERE c.change_id = $id OR c.change_number = $id
        OPTIONAL MATCH (c)-[:MODIFIES]->(ci:ConfigurationItem)
        OPTIONAL MATCH (s:Service)-[:PROVIDES]->(ci)
        RETURN c {.*} as change,
               ci {.ci_id, .name, .type, .environment, .health_status, .centrality_score, .blast_radius} as target_ci,
               s {.name, .criticality} as affected_service
        """

        results = self.neo4j.query(query, {"id": change_identifier.strip()})

        if not results:
            return f"No change found: {change_identifier}"

        r = results[0]
        change = r.get('change', {})
        ci = r.get('target_ci', {})
        service = r.get('affected_service', {})

        return f"""
Change Request Details:
{'=' * 50}
- Change ID: {change.get('change_id')}
- Change Number: {change.get('change_number')}
- Title: {change.get('title')}
- Type: {change.get('change_type')}
- Category: {change.get('category')}
- Status: {change.get('status')}
- Requested Risk Level: {change.get('risk_level')}
- Computed Risk Score: {change.get('computed_risk_score', 'Not computed')}

Target Configuration Item:
- CI ID: {ci.get('ci_id', 'Unknown')}
- Name: {ci.get('name', 'Unknown')}
- Type: {ci.get('type', 'Unknown')}
- Environment: {ci.get('environment', 'Unknown')}
- Health Status: {ci.get('health_status', 'Unknown')}
- Centrality Score: {ci.get('centrality_score', 0):.4f}
- Blast Radius: {ci.get('blast_radius', 0)} CIs

Affected Service:
- Service: {service.get('name', 'None')}
- Criticality: {service.get('criticality', 'Unknown')}

Scheduled:
- Start: {change.get('scheduled_start')}
- End: {change.get('scheduled_end')}
"""

    def _analyze_ci_criticality(self, ci_id: str) -> str:
        """Analyze how critical a CI is in the infrastructure."""
        query = """
        MATCH (ci:ConfigurationItem {ci_id: $ci_id})

        // Count upstream dependencies
        OPTIONAL MATCH (ci)-[:DEPENDS_ON|RUNS_ON|BACKED_BY*1..3]->(upstream:ConfigurationItem)
        WITH ci, count(DISTINCT upstream) as upstream_count

        // Count downstream dependents
        OPTIONAL MATCH (ci)<-[:DEPENDS_ON|RUNS_ON|BACKED_BY*1..3]-(downstream:ConfigurationItem)
        WITH ci, upstream_count, count(DISTINCT downstream) as downstream_count

        // Get services this CI supports
        OPTIONAL MATCH (s:Service)-[:PROVIDES*1..2]->(ci)

        // Get recent incidents
        OPTIONAL MATCH (ci)<-[:AFFECTS]-(i:Incident)
        WHERE i.created_at > datetime() - duration('P90D')

        RETURN ci.name as name,
               ci.type as type,
               ci.centrality_score as centrality,
               ci.blast_radius as blast_radius,
               upstream_count,
               downstream_count,
               collect(DISTINCT s.name) as services,
               collect(DISTINCT s.criticality) as service_criticalities,
               count(DISTINCT i) as recent_incidents
        """

        results = self.neo4j.query(query, {"ci_id": ci_id.strip()})

        if not results:
            return f"CI not found: {ci_id}"

        r = results[0]

        # Determine criticality tier
        criticality_score = 0
        criticality_reasons = []

        # Centrality factor
        if r['centrality'] > 0.5:
            criticality_score += 0.3
            criticality_reasons.append("High graph centrality")
        elif r['centrality'] > 0.2:
            criticality_score += 0.15

        # Blast radius factor
        if r['downstream_count'] > 20:
            criticality_score += 0.3
            criticality_reasons.append(f"Large blast radius ({r['downstream_count']} dependents)")
        elif r['downstream_count'] > 5:
            criticality_score += 0.15

        # Service criticality factor
        if 'platinum' in r['service_criticalities']:
            criticality_score += 0.3
            criticality_reasons.append("Supports platinum-tier service")
        elif 'gold' in r['service_criticalities']:
            criticality_score += 0.2
            criticality_reasons.append("Supports gold-tier service")

        # Incident history factor
        if r['recent_incidents'] > 5:
            criticality_score += 0.1
            criticality_reasons.append(f"High incident frequency ({r['recent_incidents']} in 90 days)")

        tier = (
            "CRITICAL" if criticality_score >= 0.7 else
            "HIGH" if criticality_score >= 0.5 else
            "MEDIUM" if criticality_score >= 0.3 else
            "LOW"
        )

        return f"""
CI Criticality Analysis: {r['name']}
{'=' * 50}

Criticality Tier: {tier}
Criticality Score: {criticality_score:.2f}

Graph Position:
- Upstream Dependencies: {r['upstream_count']}
- Downstream Dependents: {r['downstream_count']}
- Centrality Score: {r['centrality']:.4f}
- Blast Radius: {r['blast_radius']}

Service Impact:
- Services Supported: {', '.join(r['services']) if r['services'] else 'None'}
- Highest Service Tier: {r['service_criticalities'][0] if r['service_criticalities'] else 'N/A'}

History:
- Incidents (90 days): {r['recent_incidents']}

Criticality Factors:
{chr(10).join('- ' + reason for reason in criticality_reasons) if criticality_reasons else '- No major criticality factors'}
"""

    def _get_historical_changes(self, ci_id: str) -> str:
        """Get historical change success rates for a CI."""
        query = """
        MATCH (ci:ConfigurationItem {ci_id: $ci_id})
        MATCH (c:Change)-[:MODIFIES]->(ci)
        WHERE c.status = 'closed'
        WITH ci,
             count(c) as total_changes,
             sum(CASE WHEN c.success = true THEN 1 ELSE 0 END) as successful,
             sum(CASE WHEN c.caused_incident = true THEN 1 ELSE 0 END) as caused_incidents,
             collect(c {.change_number, .title, .success, .caused_incident, .change_type})[0..10] as recent_changes
        RETURN total_changes,
               successful,
               caused_incidents,
               CASE WHEN total_changes > 0 THEN toFloat(successful) / total_changes ELSE 0 END as success_rate,
               recent_changes
        """

        results = self.neo4j.query(query, {"ci_id": ci_id.strip()})

        if not results or results[0]['total_changes'] == 0:
            return f"No historical changes found for CI: {ci_id}"

        r = results[0]

        output = f"""
Historical Change Analysis
{'=' * 50}

Statistics:
- Total Changes: {r['total_changes']}
- Successful: {r['successful']} ({r['success_rate']*100:.1f}%)
- Failed: {r['total_changes'] - r['successful']}
- Caused Incidents: {r['caused_incidents']}

Risk Assessment:
"""
        if r['success_rate'] < 0.8:
            output += "*** WARNING: Below average success rate! ***\n"
        if r['caused_incidents'] > 0:
            output += f"*** CAUTION: {r['caused_incidents']} past changes caused incidents ***\n"

        output += "\nRecent Changes:\n"
        for change in r['recent_changes']:
            status = "SUCCESS" if change['success'] else "FAILED"
            incident = " (CAUSED INCIDENT)" if change['caused_incident'] else ""
            output += f"  - {change['change_number']}: {change['title'][:40]}... [{status}]{incident}\n"

        return output

    def _compute_change_risk_score(self, change_identifier: str) -> str:
        """Compute comprehensive risk score for a change."""

        # First get the change and CI details
        query = """
        MATCH (c:Change)
        WHERE c.change_id = $id OR c.change_number = $id
        OPTIONAL MATCH (c)-[:MODIFIES]->(ci:ConfigurationItem)
        OPTIONAL MATCH (s:Service)-[:PROVIDES]->(ci)

        // Get historical data
        OPTIONAL MATCH (ci)<-[:MODIFIES]-(past_change:Change)
        WHERE past_change.status = 'closed'
        WITH c, ci, s,
             count(past_change) as total_past_changes,
             sum(CASE WHEN past_change.success = true THEN 1 ELSE 0 END) as past_successes,
             sum(CASE WHEN past_change.caused_incident = true THEN 1 ELSE 0 END) as past_incidents

        RETURN c.change_id as change_id,
               c.change_type as change_type,
               ci.ci_id as ci_id,
               ci.name as ci_name,
               ci.centrality_score as centrality,
               ci.blast_radius as blast_radius,
               s.criticality as service_criticality,
               total_past_changes,
               past_successes,
               past_incidents,
               CASE WHEN total_past_changes > 0
                    THEN toFloat(past_successes) / total_past_changes
                    ELSE 0.5 END as historical_success_rate
        """

        results = self.neo4j.query(query, {"id": change_identifier.strip()})

        if not results:
            return f"Change not found: {change_identifier}"

        r = results[0]

        # Risk calculation algorithm
        risk_score = 0.0
        risk_factors = []

        # Factor 1: Centrality (30% weight)
        centrality = r['centrality'] or 0
        centrality_risk = min(centrality * 2, 1.0) * 0.30
        risk_score += centrality_risk
        if centrality > 0.3:
            risk_factors.append(f"High centrality ({centrality:.2f})")

        # Factor 2: Blast radius (25% weight)
        blast = r['blast_radius'] or 0
        blast_risk = min(blast / 50, 1.0) * 0.25
        risk_score += blast_risk
        if blast > 10:
            risk_factors.append(f"Significant blast radius ({blast} CIs)")

        # Factor 3: Historical failures (25% weight)
        success_rate = r['historical_success_rate']
        failure_risk = (1 - success_rate) * 0.25
        risk_score += failure_risk
        if success_rate < 0.9:
            risk_factors.append(f"Historical issues (success rate: {success_rate*100:.0f}%)")

        # Factor 4: Service criticality (15% weight)
        criticality_map = {'platinum': 1.0, 'gold': 0.7, 'silver': 0.4, 'bronze': 0.2}
        svc_crit = criticality_map.get(r['service_criticality'], 0.3)
        risk_score += svc_crit * 0.15
        if svc_crit >= 0.7:
            risk_factors.append(f"Affects {r['service_criticality']} service")

        # Factor 5: Change type (5% weight)
        type_risk = {'emergency': 0.05, 'normal': 0.02, 'standard': 0.01}
        risk_score += type_risk.get(r['change_type'], 0.02)
        if r['change_type'] == 'emergency':
            risk_factors.append("Emergency change (expedited)")

        # Past incidents factor (bonus penalty)
        if r['past_incidents'] > 0:
            risk_score = min(risk_score + 0.1, 1.0)
            risk_factors.append(f"Past changes caused {r['past_incidents']} incidents")

        risk_score = min(max(risk_score, 0), 1.0)

        # Classify risk
        risk_level = (
            "CRITICAL" if risk_score >= 0.8 else
            "HIGH" if risk_score >= 0.6 else
            "MEDIUM" if risk_score >= 0.3 else
            "LOW"
        )

        # Approval recommendation
        if risk_level == "LOW":
            approval = "Auto-approve eligible"
        elif risk_level == "MEDIUM":
            approval = "Standard approval workflow"
        elif risk_level == "HIGH":
            approval = "Manager approval required"
        else:
            approval = "CAB review required"

        return f"""
CHANGE RISK SCORE CALCULATION
{'=' * 60}

Change: {change_identifier}
Target CI: {r['ci_name']} ({r['ci_id']})

RISK SCORE: {risk_score:.4f}
RISK LEVEL: {risk_level}

Risk Breakdown:
- Centrality Factor: {centrality_risk:.4f} (CI centrality: {centrality:.2f})
- Blast Radius Factor: {blast_risk:.4f} ({blast} dependent CIs)
- Historical Factor: {failure_risk:.4f} (success rate: {success_rate*100:.0f}%)
- Service Factor: {svc_crit * 0.15:.4f} ({r['service_criticality'] or 'unknown'} tier)
- Change Type Factor: {type_risk.get(r['change_type'], 0.02):.4f} ({r['change_type']})

Key Risk Factors:
{chr(10).join('- ' + f for f in risk_factors) if risk_factors else '- No significant risk factors'}

RECOMMENDATION: {approval}
"""

    def _get_maintenance_windows(self, ci_id: str) -> str:
        """Check for safe maintenance windows."""
        # In production, would check calendar systems, traffic patterns, etc.

        return f"""
Maintenance Window Analysis for CI: {ci_id}
{'=' * 50}

Recommended Windows (lowest traffic):
- Weekdays: 2:00 AM - 5:00 AM (local time)
- Weekends: 1:00 AM - 6:00 AM (local time)

Blackout Periods:
- Month-end processing: Last 3 days of month
- Peak hours: 9:00 AM - 12:00 PM, 2:00 PM - 5:00 PM

Note: Check service-specific maintenance calendars for additional constraints.
"""

    def _check_conflicting_changes(self, change_identifier: str) -> str:
        """Check for conflicting or overlapping changes."""
        query = """
        MATCH (c:Change)
        WHERE c.change_id = $id OR c.change_number = $id
        MATCH (c)-[:MODIFIES]->(ci:ConfigurationItem)

        // Find changes to the same CI or related CIs
        OPTIONAL MATCH (other_change:Change)-[:MODIFIES]->(ci)
        WHERE other_change.change_id <> c.change_id
          AND other_change.status IN ['pending', 'approved', 'scheduled']

        // Find changes to upstream/downstream CIs
        OPTIONAL MATCH (ci)-[:DEPENDS_ON*1..2]-(related_ci:ConfigurationItem)<-[:MODIFIES]-(related_change:Change)
        WHERE related_change.change_id <> c.change_id
          AND related_change.status IN ['pending', 'approved', 'scheduled']

        RETURN c.change_number as this_change,
               collect(DISTINCT other_change {.change_number, .title, .scheduled_start, .status}) as same_ci_changes,
               collect(DISTINCT related_change {.change_number, .title, .scheduled_start}) as related_changes
        """

        results = self.neo4j.query(query, {"id": change_identifier.strip()})

        if not results:
            return f"Change not found: {change_identifier}"

        r = results[0]

        output = f"""
Conflict Analysis for: {r['this_change']}
{'=' * 50}

Changes to Same CI:
"""
        if r['same_ci_changes']:
            for c in r['same_ci_changes']:
                if c:
                    output += f"  - {c['change_number']}: {c['title'][:40]}... (Status: {c['status']})\n"
        else:
            output += "  None\n"

        output += "\nChanges to Related CIs:\n"
        if r['related_changes']:
            for c in r['related_changes']:
                if c:
                    output += f"  - {c['change_number']}: {c['title'][:40]}...\n"
        else:
            output += "  None\n"

        if r['same_ci_changes'] or r['related_changes']:
            output += "\n*** ATTENTION: Potential scheduling conflicts detected! ***\n"
            output += "Consider coordinating with other change owners.\n"

        return output

    def run(self, input_data: Dict[str, Any]) -> AgentResponse:
        """
        Run change risk assessment.

        Args:
            input_data: Dict containing:
                - change_id: The change to assess
                - context: Optional additional context
        """
        change_id = input_data.get('change_id')

        if not change_id:
            return self._create_response(
                success=False,
                result=None,
                reasoning="No change_id provided"
            )

        try:
            if self.agent_executor:
                result = self.agent_executor.invoke({
                    "input": f"Assess the risk of change {change_id}. "
                             f"Get the change details, analyze CI criticality, "
                             f"review historical changes, compute risk score, "
                             f"and check for conflicts."
                })

                return self._create_response(
                    success=True,
                    result=result.get('output'),
                    reasoning="Analysis completed using LangChain agent",
                    confidence=0.85,
                    change_id=change_id
                )
            else:
                return self._run_direct_assessment(change_id)

        except Exception as e:
            logger.error(f"Change Risk Agent error: {e}")
            return self._create_response(
                success=False,
                result=str(e),
                reasoning=f"Error during assessment: {e}"
            )

    def _run_direct_assessment(self, change_id: str) -> AgentResponse:
        """Run assessment directly without LLM."""
        # Get change details
        change_info = self._get_change_details(change_id)

        # Compute risk score (includes all analysis)
        risk_score = self._compute_change_risk_score(change_id)

        # Check conflicts
        conflicts = self._check_conflicting_changes(change_id)

        result = f"""
CHANGE RISK ASSESSMENT REPORT
{'=' * 60}

{change_info}

{risk_score}

{conflicts}
"""

        return self._create_response(
            success=True,
            result=result,
            reasoning="Direct assessment completed",
            confidence=0.75,
            change_id=change_id
        )

    def __del__(self):
        """Cleanup."""
        if hasattr(self, 'neo4j'):
            self.neo4j.close()
        if hasattr(self, 'postgres'):
            self.postgres.close()


def assess_change_risk(change_id: str) -> Dict[str, Any]:
    """Assess risk for a change request."""
    agent = ChangeRiskAgent()
    response = agent.run({"change_id": change_id})
    return {
        "success": response.success,
        "result": response.result,
        "confidence": response.confidence,
        "metadata": response.metadata
    }


if __name__ == "__main__":
    agent = ChangeRiskAgent()
    result = agent.run({"change_id": "CHG0000001"})
    print(result.result)
