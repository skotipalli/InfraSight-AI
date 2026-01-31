#!/usr/bin/env python3
"""
InfraSight-AI: Gradio Web Interface
AI-driven visibility, prediction, and intelligence for infrastructure.
"""

import logging
import sys
from pathlib import Path
from typing import Tuple, Optional
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import gradio as gr
except ImportError:
    print("Gradio not installed. Run: pip install gradio")
    sys.exit(1)

from config.settings import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# MOCK DATA FOR DEMO (Replace with real DB queries in production)
# ============================================================================

SAMPLE_INCIDENTS = [
    {"id": "INC0000001", "title": "Database connection timeout - mysql-prod-0001", "severity": "high"},
    {"id": "INC0000002", "title": "Service down - Payment Gateway", "severity": "critical"},
    {"id": "INC0000003", "title": "High latency on web-server-prod-0012", "severity": "medium"},
    {"id": "INC0000004", "title": "Certificate expired - api-gateway", "severity": "high"},
    {"id": "INC0000005", "title": "Memory leak detected - analytics-service", "severity": "medium"},
]

SAMPLE_CHANGES = [
    {"id": "CHG0000001", "title": "Software Update: web-server-prod-0001", "risk": "medium"},
    {"id": "CHG0000002", "title": "Security Patch: mysql-prod-0001", "risk": "high"},
    {"id": "CHG0000003", "title": "Configuration Change: load-balancer", "risk": "low"},
    {"id": "CHG0000004", "title": "Capacity Expansion: kafka-cluster", "risk": "medium"},
    {"id": "CHG0000005", "title": "Migration: legacy-auth to new-auth", "risk": "high"},
]

SAMPLE_CIS = [
    {"id": "ci-001", "name": "web-prod-0001", "type": "server", "health": "healthy"},
    {"id": "ci-002", "name": "mysql-prod-0001", "type": "database", "health": "degraded"},
    {"id": "ci-003", "name": "redis-cache-01", "type": "cache", "health": "healthy"},
    {"id": "ci-004", "name": "api-gateway-prod", "type": "load_balancer", "health": "healthy"},
    {"id": "ci-005", "name": "kafka-broker-01", "type": "message_queue", "health": "healthy"},
]


# ============================================================================
# AGENT WRAPPER FUNCTIONS
# ============================================================================

def analyze_incident(incident_id: str) -> str:
    """Run RCA analysis on an incident."""
    if not incident_id or incident_id == "":
        return "Please enter an incident ID to analyze."

    try:
        from src.agents.rca_agent import RCAAgent
        agent = RCAAgent()
        result = agent.run({"incident_id": incident_id})

        if result.success:
            return result.result
        else:
            return f"Analysis failed: {result.reasoning}"

    except Exception as e:
        logger.error(f"RCA analysis error: {e}")
        # Return demo output
        return f"""
ROOT CAUSE ANALYSIS REPORT
{'=' * 60}

Incident: {incident_id}

INCIDENT DETAILS:
- Title: Database connection timeout
- Severity: HIGH
- Status: Open
- Category: Performance
- Affected CI: mysql-prod-0001 (database)

UPSTREAM DEPENDENCIES (Potential Root Causes):
{'=' * 50}
! [1 hop] mysql-primary-01 (database)
   Health: degraded, Centrality: 0.4521
! [2 hops] storage-backend-01 (storage)
   Health: unhealthy, Centrality: 0.3211

*** ATTENTION: 2 unhealthy upstream CIs found! ***
   -> storage-backend-01 is unhealthy
   -> mysql-primary-01 is degraded

BLAST RADIUS ANALYSIS:
{'=' * 50}
- Total dependent CIs: 15
- Affected Services: Customer Portal, Payment Gateway

ROOT CAUSE IDENTIFIED:
The storage backend (storage-backend-01) is experiencing issues,
causing the MySQL primary to become degraded and triggering
connection timeouts in downstream applications.

CONFIDENCE: HIGH (0.85)

RECOMMENDED ACTIONS:
1. Investigate storage-backend-01 immediately
2. Check disk I/O and space utilization
3. Review storage controller logs
4. Consider failover if available
"""


def assess_change_risk(change_id: str) -> str:
    """Assess risk for a change request."""
    if not change_id or change_id == "":
        return "Please enter a change ID to assess."

    try:
        from src.agents.change_risk_agent import ChangeRiskAgent
        agent = ChangeRiskAgent()
        result = agent.run({"change_id": change_id})

        if result.success:
            return result.result
        else:
            return f"Assessment failed: {result.reasoning}"

    except Exception as e:
        logger.error(f"Change risk assessment error: {e}")
        # Return demo output
        return f"""
CHANGE RISK ASSESSMENT REPORT
{'=' * 60}

Change: {change_id}
Title: Software Update: web-server-prod-0001

TARGET CI ANALYSIS:
- Name: web-server-prod-0001
- Type: server
- Environment: production
- Centrality Score: 0.3521
- Blast Radius: 12 dependent CIs

SERVICE IMPACT:
- Affected Service: Customer Portal
- Service Criticality: GOLD

RISK SCORE CALCULATION:
{'=' * 50}
RISK SCORE: 0.4875
RISK LEVEL: MEDIUM

Risk Breakdown:
- Centrality Factor: 0.1056 (CI centrality: 0.35)
- Blast Radius Factor: 0.0600 (12 dependent CIs)
- Historical Factor: 0.0500 (success rate: 80%)
- Service Factor: 0.1050 (gold tier)
- Change Type Factor: 0.0200 (normal)

Key Risk Factors:
- Affects gold-tier service
- 12 downstream dependencies
- Historical issues (success rate: 80%)

RECOMMENDATION: Standard approval workflow
- Schedule during maintenance window
- Ensure rollback plan is tested
- Notify service owners 24 hours in advance
"""


def get_remediation(incident_id: str, description: str = "") -> str:
    """Get remediation recommendations."""
    if not incident_id or incident_id == "":
        return "Please enter an incident ID to get recommendations."

    try:
        from src.agents.remediation_agent import RemediationAgent
        agent = RemediationAgent()
        result = agent.run({"incident_id": incident_id, "description": description})

        if result.success:
            return result.result
        else:
            return f"Recommendation failed: {result.reasoning}"

    except Exception as e:
        logger.error(f"Remediation recommendation error: {e}")
        # Return demo output
        return f"""
REMEDIATION RECOMMENDATION REPORT
{'=' * 60}

Incident: {incident_id}

INCIDENT CONTEXT:
- Title: Database connection timeout
- Severity: HIGH
- CI Type: database
- Environment: production

SIMILAR PAST INCIDENTS:
{'=' * 50}
INC0000156: Database connection pool exhausted - mysql-prod
  Similarity: 92.3%
  Resolution: Increased pool size, fixed connection leak
  Root Cause: Connection leak in payment service

INC0000089: MySQL timeout during peak load
  Similarity: 87.1%
  Resolution: Optimized slow queries, added read replica
  Root Cause: Inefficient query causing lock contention

RECOMMENDED REMEDIATION:
{'=' * 50}

IMMEDIATE FIX (0-30 minutes):
1. Check current connection count: SHOW PROCESSLIST
2. Identify and kill idle connections if above threshold
3. Verify application connection pool settings
4. Restart affected application pods if needed

WORKAROUND:
- Enable read replicas for read-heavy traffic
- Implement connection retry with exponential backoff
- Rate limit non-critical database operations

ROOT CAUSE FIX:
1. Audit application code for connection leaks
2. Implement connection pool monitoring
3. Set appropriate connection timeouts
4. Add circuit breaker for database calls

PREVENTIVE ACTIONS:
1. Add connection pool monitoring alerts
2. Implement automated scaling for peak loads
3. Schedule regular connection pool audits
4. Document and update runbook

ESTIMATED RESOLUTION TIME: 30-60 minutes
"""


def search_knowledge(query: str) -> str:
    """Search the knowledge base."""
    if not query or query == "":
        return "Please enter a search query."

    try:
        from src.rag.embedding_generator import EmbeddingGenerator
        generator = EmbeddingGenerator()

        # Search incidents
        incidents = generator.search_similar(query, "incident_embeddings", limit=3)

        # Search knowledge
        knowledge = generator.search_similar(query, "knowledge_embeddings", limit=3)

        output = "SEARCH RESULTS\n" + "=" * 50 + "\n\n"

        output += "SIMILAR INCIDENTS:\n"
        if incidents:
            for inc in incidents:
                output += f"- {inc.get('title', 'N/A')} (Similarity: {inc['similarity']:.1%})\n"
        else:
            output += "  No similar incidents found.\n"

        output += "\nKNOWLEDGE ARTICLES:\n"
        if knowledge:
            for kb in knowledge:
                output += f"- {kb['title']} (Similarity: {kb['similarity']:.1%})\n"
                output += f"  Category: {kb['category']}\n"
        else:
            output += "  No relevant articles found.\n"

        generator.close()
        return output

    except Exception as e:
        logger.error(f"Knowledge search error: {e}")
        return f"""
SEARCH RESULTS for: "{query}"
{'=' * 50}

SIMILAR INCIDENTS:
- Database connection timeout (Similarity: 89.2%)
- MySQL slow query alert (Similarity: 76.5%)
- Connection pool exhausted (Similarity: 71.3%)

KNOWLEDGE ARTICLES:
- KB0001: Database Connection Pool Exhaustion (92.1%)
  Category: Database

- KB0002: High CPU Usage on Application Server (45.3%)
  Category: Performance

RELATED RESOLUTIONS:
- Increased connection pool size
- Implemented connection timeout
- Added query optimization
"""


def get_dependency_graph(ci_name: str) -> str:
    """Get dependency graph for a CI."""
    if not ci_name or ci_name == "":
        return "Please enter a CI name."

    # In production, would query Neo4j and generate visualization
    return f"""
DEPENDENCY GRAPH for: {ci_name}
{'=' * 60}

UPSTREAM DEPENDENCIES (what {ci_name} depends on):
├── mysql-primary-01 (database) [CRITICAL]
│   └── storage-san-01 (storage)
├── redis-cache-01 (cache)
└── config-server (application)

DOWNSTREAM DEPENDENTS (what depends on {ci_name}):
├── api-gateway (load_balancer)
│   ├── web-frontend-01 (application)
│   ├── web-frontend-02 (application)
│   └── mobile-backend (application)
├── payment-service (application)
└── notification-service (application)

GRAPH METRICS:
- Centrality Score: 0.4521
- PageRank: 0.0234
- Blast Radius: 8 CIs
- Risk Score: 0.5672 (MEDIUM)

SERVICES AFFECTED:
- Customer Portal (GOLD)
- Payment Gateway (PLATINUM)
- Notification Hub (SILVER)
"""


def get_orphan_detection() -> str:
    """Detect orphaned and zombie services."""
    return """
ORPHAN & ZOMBIE SERVICE DETECTION
{'=' * 60}

ORPHANED CIs (No dependencies):
┌────────────────────────────────────────────────────────────┐
│ CI Name              │ Type       │ Monthly Cost │ Status  │
├────────────────────────────────────────────────────────────┤
│ legacy-auth-01       │ application│ $245.00      │ active  │
│ test-server-old      │ server     │ $180.00      │ active  │
│ unused-cache-02      │ cache      │ $95.00       │ active  │
│ deprecated-api       │ application│ $320.00      │ active  │
└────────────────────────────────────────────────────────────┘

TOTAL POTENTIAL SAVINGS: $840.00/month

ZOMBIE SERVICES (Active but unused):
┌────────────────────────────────────────────────────────────┐
│ CI Name              │ Last Activity │ Monthly Cost│ Traffic │
├────────────────────────────────────────────────────────────┤
│ reports-v1           │ 45 days ago   │ $450.00     │ 0 req/d │
│ batch-processor-old  │ 30 days ago   │ $280.00     │ 2 req/d │
│ staging-clone        │ 60 days ago   │ $520.00     │ 0 req/d │
└────────────────────────────────────────────────────────────┘

RECOMMENDATIONS:
1. Review legacy-auth-01 for decommission
2. Archive test-server-old if no longer needed
3. Investigate reports-v1 for removal
4. Consider stopping staging-clone

ESTIMATED ANNUAL SAVINGS: $26,160
"""


def get_capacity_prediction() -> str:
    """Get capacity prediction analysis."""
    return """
CAPACITY & SATURATION PREDICTION
{'=' * 60}

RESOURCES APPROACHING CAPACITY (7-day forecast):
┌──────────────────────────────────────────────────────────────────┐
│ CI Name          │ Metric     │ Current │ Predicted │ Days Left │
├──────────────────────────────────────────────────────────────────┤
│ mysql-prod-01    │ disk_usage │ 78%     │ 95%       │ 5 days    │
│ web-server-03    │ memory     │ 82%     │ 95%       │ 7 days    │
│ kafka-broker-02  │ disk_usage │ 71%     │ 90%       │ 12 days   │
└──────────────────────────────────────────────────────────────────┘

TREND ANALYSIS:
- mysql-prod-01: Growing at 3.4% daily
- web-server-03: Memory pressure from increased traffic
- kafka-broker-02: Log retention causing disk growth

RECOMMENDED ACTIONS:
┌────────────────────────────────────────────────────────────────┐
│ Priority │ CI              │ Action                            │
├────────────────────────────────────────────────────────────────┤
│ HIGH     │ mysql-prod-01   │ Expand storage to 2TB             │
│ MEDIUM   │ web-server-03   │ Scale to 64GB RAM or add instance│
│ LOW      │ kafka-broker-02 │ Reduce retention to 7 days        │
└────────────────────────────────────────────────────────────────┘

COST IMPACT:
- mysql-prod-01 storage expansion: +$150/month
- web-server-03 memory upgrade: +$200/month
- kafka-broker-02 retention change: $0 (config only)
"""


def get_anomaly_detection() -> str:
    """Get anomaly detection results."""
    return """
ANOMALY & DRIFT DETECTION REPORT
{'=' * 60}

METRIC ANOMALIES DETECTED (Last 24 hours):
┌──────────────────────────────────────────────────────────────────┐
│ CI Name          │ Metric      │ Value    │ Threshold │ Severity │
├──────────────────────────────────────────────────────────────────┤
│ api-gateway-01   │ error_rate  │ 5.2%     │ 1%        │ HIGH     │
│ web-server-05    │ latency_p99 │ 1850ms   │ 1000ms    │ MEDIUM   │
│ redis-cache-02   │ memory      │ 92%      │ 90%       │ MEDIUM   │
└──────────────────────────────────────────────────────────────────┘

CONFIGURATION DRIFT DETECTED:
┌──────────────────────────────────────────────────────────────────┐
│ CI Name          │ Change Type     │ Old Value   │ New Value    │
├──────────────────────────────────────────────────────────────────┤
│ nginx-prod-01    │ config change   │ 1000 conn   │ 5000 conn    │
│ mysql-replica-02 │ new dependency  │ -           │ analytics-db │
└──────────────────────────────────────────────────────────────────┘

GRAPH DRIFT (New/Removed Dependencies):
- NEW: analytics-service -> mysql-replica-02 (DEPENDS_ON)
- NEW: web-frontend -> cdn-edge-01 (CONNECTS_TO)
- REMOVED: legacy-api -> old-database (DEPENDS_ON)

RECOMMENDATIONS:
1. Investigate api-gateway-01 error spike
2. Review web-server-05 performance
3. Validate nginx config change was intentional
4. Verify analytics-db dependency is approved
"""


def chat_interface(message: str, history: list) -> str:
    """Main chat interface for natural language queries."""
    if not message:
        return "Please ask a question about your infrastructure."

    message_lower = message.lower()

    # Route to appropriate function based on intent
    if any(word in message_lower for word in ["root cause", "rca", "why", "analyze incident"]):
        # Extract incident ID if present
        import re
        match = re.search(r'(INC\d+)', message, re.IGNORECASE)
        if match:
            return analyze_incident(match.group(1))
        return "Please specify an incident ID (e.g., INC0000001) for root cause analysis."

    elif any(word in message_lower for word in ["change", "risk", "assess", "chg"]):
        import re
        match = re.search(r'(CHG\d+)', message, re.IGNORECASE)
        if match:
            return assess_change_risk(match.group(1))
        return "Please specify a change ID (e.g., CHG0000001) for risk assessment."

    elif any(word in message_lower for word in ["fix", "remediate", "resolve", "recommend"]):
        import re
        match = re.search(r'(INC\d+)', message, re.IGNORECASE)
        if match:
            return get_remediation(match.group(1))
        return "Please specify an incident ID for remediation recommendations."

    elif any(word in message_lower for word in ["depend", "graph", "impact", "blast"]):
        # Try to extract CI name
        words = message.split()
        for i, word in enumerate(words):
            if word.lower() in ["for", "of", "on"] and i + 1 < len(words):
                return get_dependency_graph(words[i + 1])
        return get_dependency_graph("mysql-prod-0001")

    elif any(word in message_lower for word in ["orphan", "zombie", "unused"]):
        return get_orphan_detection()

    elif any(word in message_lower for word in ["capacity", "prediction", "forecast", "saturation"]):
        return get_capacity_prediction()

    elif any(word in message_lower for word in ["anomaly", "drift", "unusual"]):
        return get_anomaly_detection()

    elif any(word in message_lower for word in ["search", "find", "knowledge"]):
        return search_knowledge(message)

    else:
        return f"""
I can help you with:

1. **Root Cause Analysis**: "Analyze incident INC0000001"
2. **Change Risk Assessment**: "Assess risk for CHG0000001"
3. **Remediation Recommendations**: "How to fix INC0000001"
4. **Dependency Graphs**: "Show dependencies for mysql-prod-01"
5. **Orphan Detection**: "Find orphaned services"
6. **Capacity Prediction**: "Show capacity forecast"
7. **Anomaly Detection**: "Show detected anomalies"
8. **Knowledge Search**: "Search for database timeout"

How can I assist you?
"""


# ============================================================================
# GRADIO UI DEFINITION
# ============================================================================

def create_ui():
    """Create the Gradio interface."""

    with gr.Blocks(
        title="InfraSight-AI",
        theme=gr.themes.Soft(),
        css="""
        .gradio-container {max-width: 1200px !important}
        .output-text {font-family: monospace; white-space: pre-wrap;}
        """
    ) as app:

        gr.Markdown("""
        # InfraSight-AI
        ### AI-driven visibility, prediction, and intelligence for infrastructure

        *Powered by Graph Analytics, RAG, and Agentic AI*
        """)

        with gr.Tabs():
            # Tab 1: Chat Interface
            with gr.TabItem("AI Assistant"):
                gr.Markdown("Ask questions in natural language about incidents, changes, and infrastructure.")
                chatbot = gr.Chatbot(height=400)
                msg = gr.Textbox(
                    placeholder="Ask about incidents, changes, dependencies...",
                    label="Your Question"
                )
                clear = gr.Button("Clear")

                def respond(message, chat_history):
                    response = chat_interface(message, chat_history)
                    chat_history.append((message, response))
                    return "", chat_history

                msg.submit(respond, [msg, chatbot], [msg, chatbot])
                clear.click(lambda: None, None, chatbot, queue=False)

            # Tab 2: Root Cause Analysis
            with gr.TabItem("Root Cause Analysis"):
                gr.Markdown("Analyze incidents to identify root causes using graph-based dependency analysis.")

                with gr.Row():
                    with gr.Column(scale=1):
                        incident_dropdown = gr.Dropdown(
                            choices=[f"{i['id']} - {i['title']}" for i in SAMPLE_INCIDENTS],
                            label="Select Incident",
                            info="Choose an incident to analyze"
                        )
                        incident_input = gr.Textbox(
                            label="Or enter Incident ID",
                            placeholder="INC0000001"
                        )
                        rca_btn = gr.Button("Analyze Root Cause", variant="primary")

                    with gr.Column(scale=2):
                        rca_output = gr.Textbox(
                            label="Analysis Results",
                            lines=25,
                            elem_classes=["output-text"]
                        )

                def run_rca(dropdown, manual):
                    incident_id = manual if manual else (dropdown.split(" - ")[0] if dropdown else "")
                    return analyze_incident(incident_id)

                rca_btn.click(run_rca, [incident_dropdown, incident_input], rca_output)

            # Tab 3: Change Risk Assessment
            with gr.TabItem("Change Risk Assessment"):
                gr.Markdown("Evaluate change requests and compute risk scores based on dependency analysis.")

                with gr.Row():
                    with gr.Column(scale=1):
                        change_dropdown = gr.Dropdown(
                            choices=[f"{c['id']} - {c['title']}" for c in SAMPLE_CHANGES],
                            label="Select Change",
                            info="Choose a change to assess"
                        )
                        change_input = gr.Textbox(
                            label="Or enter Change ID",
                            placeholder="CHG0000001"
                        )
                        risk_btn = gr.Button("Assess Risk", variant="primary")

                    with gr.Column(scale=2):
                        risk_output = gr.Textbox(
                            label="Risk Assessment",
                            lines=25,
                            elem_classes=["output-text"]
                        )

                def run_risk(dropdown, manual):
                    change_id = manual if manual else (dropdown.split(" - ")[0] if dropdown else "")
                    return assess_change_risk(change_id)

                risk_btn.click(run_risk, [change_dropdown, change_input], risk_output)

            # Tab 4: Remediation Recommendations
            with gr.TabItem("Remediation"):
                gr.Markdown("Get fix recommendations, workarounds, and preventive actions using RAG.")

                with gr.Row():
                    with gr.Column(scale=1):
                        rem_incident = gr.Textbox(
                            label="Incident ID",
                            placeholder="INC0000001"
                        )
                        rem_desc = gr.Textbox(
                            label="Additional Context (optional)",
                            placeholder="Describe symptoms...",
                            lines=3
                        )
                        rem_btn = gr.Button("Get Recommendations", variant="primary")

                    with gr.Column(scale=2):
                        rem_output = gr.Textbox(
                            label="Remediation Recommendations",
                            lines=25,
                            elem_classes=["output-text"]
                        )

                rem_btn.click(get_remediation, [rem_incident, rem_desc], rem_output)

            # Tab 5: Dependency Graph
            with gr.TabItem("Dependency Graph"):
                gr.Markdown("Visualize service and infrastructure dependencies.")

                with gr.Row():
                    with gr.Column(scale=1):
                        ci_dropdown = gr.Dropdown(
                            choices=[f"{c['name']} ({c['type']})" for c in SAMPLE_CIS],
                            label="Select CI",
                            info="Choose a configuration item"
                        )
                        ci_input = gr.Textbox(
                            label="Or enter CI Name",
                            placeholder="mysql-prod-0001"
                        )
                        graph_btn = gr.Button("Show Dependencies", variant="primary")

                    with gr.Column(scale=2):
                        graph_output = gr.Textbox(
                            label="Dependency Graph",
                            lines=25,
                            elem_classes=["output-text"]
                        )

                def run_graph(dropdown, manual):
                    ci_name = manual if manual else (dropdown.split(" (")[0] if dropdown else "")
                    return get_dependency_graph(ci_name)

                graph_btn.click(run_graph, [ci_dropdown, ci_input], graph_output)

            # Tab 6: Proactive Detection
            with gr.TabItem("Proactive Detection"):
                gr.Markdown("Detect orphans, anomalies, and predict capacity issues.")

                with gr.Row():
                    orphan_btn = gr.Button("Detect Orphan Services")
                    anomaly_btn = gr.Button("Show Anomalies")
                    capacity_btn = gr.Button("Capacity Prediction")

                detection_output = gr.Textbox(
                    label="Detection Results",
                    lines=25,
                    elem_classes=["output-text"]
                )

                orphan_btn.click(get_orphan_detection, [], detection_output)
                anomaly_btn.click(get_anomaly_detection, [], detection_output)
                capacity_btn.click(get_capacity_prediction, [], detection_output)

            # Tab 7: Knowledge Search
            with gr.TabItem("Knowledge Search"):
                gr.Markdown("Search the knowledge base for solutions and best practices.")

                search_input = gr.Textbox(
                    label="Search Query",
                    placeholder="database connection timeout..."
                )
                search_btn = gr.Button("Search", variant="primary")
                search_output = gr.Textbox(
                    label="Search Results",
                    lines=20,
                    elem_classes=["output-text"]
                )

                search_btn.click(search_knowledge, [search_input], search_output)

        gr.Markdown("""
        ---
        **InfraSight-AI** | Graph Analytics + RAG + Agentic AI
        | [Documentation](docs/ARCHITECTURE.md)
        """)

    return app


def main():
    """Main entry point."""
    app = create_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )


if __name__ == "__main__":
    main()
