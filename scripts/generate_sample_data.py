#!/usr/bin/env python3
"""
InfraSight-AI: Synthetic Data Generator
Generates realistic ITSM and infrastructure data for demo purposes.

This script creates 8 CSV files with 250+ rows each:
- services.csv
- configuration_items.csv
- ci_relationships.csv
- incidents.csv
- problems.csv
- changes.csv
- resolutions.csv
- metrics_usage.csv
"""

import csv
import uuid
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import json

# Seed for reproducibility
random.seed(42)

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

TEAMS = [
    "Platform Engineering", "Cloud Infrastructure", "Database Operations",
    "Network Operations", "Security Operations", "Application Support",
    "DevOps", "SRE", "Data Engineering", "Customer Experience"
]

OWNERS = [
    "John Smith", "Sarah Johnson", "Michael Chen", "Emily Davis",
    "David Wilson", "Lisa Anderson", "James Brown", "Jennifer Martinez",
    "Robert Taylor", "Amanda White", "Christopher Lee", "Jessica Garcia",
    "Daniel Harris", "Michelle Robinson", "Kevin Thompson", "Laura Clark"
]

CLOUD_PROVIDERS = ["AWS", "Azure", "GCP", "On-Premise"]
CLOUD_REGIONS = {
    "AWS": ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"],
    "Azure": ["eastus", "westus2", "westeurope", "southeastasia"],
    "GCP": ["us-central1", "us-east1", "europe-west1", "asia-east1"],
    "On-Premise": ["dc-east", "dc-west", "dc-eu", "dc-asia"]
}

CI_TYPES = {
    "server": {
        "prefixes": ["web", "app", "api", "worker", "batch", "proxy"],
        "os": ["Ubuntu 22.04", "RHEL 8", "Amazon Linux 2", "Windows Server 2022"],
        "cpu_range": (4, 32),
        "memory_range": (8, 128),
        "storage_range": (100, 2000)
    },
    "database": {
        "prefixes": ["mysql", "postgres", "mongodb", "redis", "elasticsearch"],
        "versions": ["8.0", "15.0", "6.0", "7.0", "8.10"],
        "cpu_range": (8, 64),
        "memory_range": (32, 512),
        "storage_range": (500, 10000)
    },
    "application": {
        "prefixes": ["auth", "payment", "inventory", "notification", "analytics", "reporting"],
        "versions": ["1.0", "2.0", "2.5", "3.0", "3.1", "4.0"],
        "cpu_range": (2, 16),
        "memory_range": (4, 64),
        "storage_range": (50, 500)
    },
    "network": {
        "prefixes": ["firewall", "router", "switch", "vpn", "dns"],
        "versions": ["1.0", "2.0", "3.0"],
        "cpu_range": (2, 8),
        "memory_range": (4, 32),
        "storage_range": (50, 200)
    },
    "load_balancer": {
        "prefixes": ["alb", "nlb", "haproxy", "nginx", "f5"],
        "versions": ["1.0", "2.0"],
        "cpu_range": (4, 16),
        "memory_range": (8, 64),
        "storage_range": (50, 200)
    },
    "cache": {
        "prefixes": ["redis", "memcached", "varnish"],
        "versions": ["6.0", "7.0", "1.6"],
        "cpu_range": (4, 16),
        "memory_range": (16, 128),
        "storage_range": (50, 500)
    },
    "message_queue": {
        "prefixes": ["rabbitmq", "kafka", "sqs", "activemq"],
        "versions": ["3.11", "3.5", "1.0", "5.17"],
        "cpu_range": (4, 16),
        "memory_range": (8, 64),
        "storage_range": (100, 1000)
    },
    "storage": {
        "prefixes": ["s3", "nfs", "efs", "blob", "ceph"],
        "versions": ["1.0", "2.0"],
        "cpu_range": (2, 8),
        "memory_range": (8, 32),
        "storage_range": (1000, 50000)
    },
    "container": {
        "prefixes": ["k8s-node", "docker-host", "ecs-instance"],
        "versions": ["1.28", "24.0", "1.0"],
        "cpu_range": (8, 64),
        "memory_range": (32, 256),
        "storage_range": (200, 2000)
    },
    "cloud_service": {
        "prefixes": ["lambda", "cloudfunction", "appservice"],
        "versions": ["1.0", "2.0"],
        "cpu_range": (1, 4),
        "memory_range": (1, 16),
        "storage_range": (10, 100)
    }
}

INCIDENT_CATEGORIES = {
    "Performance": ["Slow response", "High latency", "Timeout errors", "Resource exhaustion"],
    "Availability": ["Service down", "Partial outage", "Connectivity issues", "Failover triggered"],
    "Security": ["Unauthorized access", "Certificate expired", "Vulnerability detected", "Brute force attempt"],
    "Data": ["Data corruption", "Replication lag", "Backup failure", "Storage full"],
    "Network": ["DNS resolution failure", "Packet loss", "Bandwidth saturation", "Routing issues"],
    "Application": ["Application crash", "Memory leak", "Thread deadlock", "Configuration error"]
}

PROBLEM_ROOT_CAUSES = [
    "Memory leak in application code",
    "Database connection pool exhaustion",
    "Inadequate resource provisioning",
    "Network misconfiguration",
    "Certificate expiration oversight",
    "Race condition in concurrent processing",
    "Disk I/O bottleneck",
    "Cache invalidation issue",
    "Load balancer misconfiguration",
    "DNS propagation delay",
    "Third-party service degradation",
    "Insufficient logging/monitoring",
    "Lack of circuit breaker implementation",
    "Improper error handling",
    "Database query optimization needed"
]

CHANGE_CATEGORIES = [
    "Software Update", "Security Patch", "Configuration Change",
    "Hardware Upgrade", "Capacity Expansion", "Maintenance Window",
    "Migration", "Optimization", "New Deployment", "Rollback"
]

RESOLUTION_FIXES = [
    "Restarted the affected service",
    "Increased resource allocation (CPU/Memory)",
    "Applied configuration hotfix",
    "Cleared and rebuilt cache",
    "Rolled back to previous version",
    "Updated SSL/TLS certificates",
    "Optimized database queries",
    "Scaled out additional instances",
    "Fixed network routing rules",
    "Patched security vulnerability",
    "Cleaned up disk space",
    "Reset connection pools",
    "Updated DNS records",
    "Applied vendor patch",
    "Implemented circuit breaker"
]

WORKAROUNDS = [
    "Temporary redirect to backup system",
    "Manual failover to DR site",
    "Rate limiting enabled",
    "Caching bypass implemented",
    "Direct database access provided",
    "VPN tunnel established",
    "Load balancer health checks adjusted",
    "Async processing enabled",
    "Read replicas promoted temporarily",
    "Feature flag disabled"
]

PREVENTIVE_ACTIONS = [
    "Implement automated scaling policies",
    "Add monitoring alerts for early detection",
    "Schedule regular maintenance windows",
    "Implement certificate auto-renewal",
    "Add redundancy to critical components",
    "Improve deployment pipeline testing",
    "Implement chaos engineering practices",
    "Add circuit breakers for external dependencies",
    "Enhance logging and observability",
    "Document runbooks for common issues"
]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())

def random_date(start_days_ago: int = 365, end_days_ago: int = 0) -> datetime:
    """Generate a random date between start_days_ago and end_days_ago."""
    start = datetime.now() - timedelta(days=start_days_ago)
    end = datetime.now() - timedelta(days=end_days_ago)
    delta = end - start
    random_days = random.randint(0, delta.days)
    random_seconds = random.randint(0, 86400)
    return start + timedelta(days=random_days, seconds=random_seconds)

def random_ip() -> str:
    """Generate a random private IP address."""
    return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

def format_datetime(dt: datetime) -> str:
    """Format datetime for CSV."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")

# ============================================================================
# DATA GENERATORS
# ============================================================================

def generate_services(count: int = 30) -> List[Dict[str, Any]]:
    """Generate service records."""
    services = []
    service_types = [
        "web_application", "api_gateway", "data_pipeline", "analytics_platform",
        "customer_portal", "payment_system", "inventory_management",
        "notification_service", "authentication_service", "reporting_platform",
        "search_engine", "recommendation_engine", "content_delivery",
        "order_management", "crm_integration"
    ]

    criticalities = ["platinum", "gold", "silver", "bronze"]
    criticality_weights = [0.1, 0.2, 0.4, 0.3]

    for i in range(count):
        service_type = service_types[i % len(service_types)]
        criticality = random.choices(criticalities, criticality_weights)[0]

        sla_hours = {
            "platinum": random.uniform(0.25, 1),
            "gold": random.uniform(1, 4),
            "silver": random.uniform(4, 8),
            "bronze": random.uniform(8, 24)
        }[criticality]

        created_at = random_date(730, 90)

        services.append({
            "service_id": generate_uuid(),
            "service_name": f"{service_type.replace('_', '-')}-{i+1:03d}",
            "service_type": service_type,
            "description": f"Production {service_type.replace('_', ' ')} service",
            "criticality": criticality,
            "owner": random.choice(OWNERS),
            "team": random.choice(TEAMS),
            "sla_target_hours": round(sla_hours, 2),
            "status": random.choices(["open", "closed"], [0.95, 0.05])[0],
            "created_at": format_datetime(created_at),
            "updated_at": format_datetime(created_at + timedelta(days=random.randint(0, 30)))
        })

    return services

def generate_configuration_items(services: List[Dict], count: int = 300) -> List[Dict[str, Any]]:
    """Generate configuration item records."""
    cis = []
    environments = ["production", "staging", "development", "testing", "dr"]
    env_weights = [0.4, 0.2, 0.2, 0.15, 0.05]
    statuses = ["open", "in_progress", "closed"]
    status_weights = [0.85, 0.1, 0.05]

    ci_type_list = list(CI_TYPES.keys())

    for i in range(count):
        ci_type = random.choice(ci_type_list)
        config = CI_TYPES[ci_type]
        prefix = random.choice(config["prefixes"])
        environment = random.choices(environments, env_weights)[0]
        cloud_provider = random.choice(CLOUD_PROVIDERS)
        cloud_region = random.choice(CLOUD_REGIONS[cloud_provider])

        # Assign to a service (80% chance)
        service = random.choice(services) if random.random() < 0.8 else None

        cpu_cores = random.randint(*config["cpu_range"])
        memory_gb = random.randint(*config["memory_range"])
        storage_gb = random.randint(*config["storage_range"])

        # Cost calculation based on resources and cloud
        base_cost = (cpu_cores * 10) + (memory_gb * 2) + (storage_gb * 0.1)
        cloud_multiplier = {"AWS": 1.0, "Azure": 0.95, "GCP": 0.9, "On-Premise": 0.7}
        cost = round(base_cost * cloud_multiplier[cloud_provider], 2)

        version = config.get("versions", config.get("os", ["1.0"]))[0] if "versions" in config else random.choice(config.get("os", ["1.0"]))

        created_at = random_date(365, 30)

        cis.append({
            "ci_id": generate_uuid(),
            "ci_name": f"{prefix}-{environment[:4]}-{i+1:04d}",
            "ci_type": ci_type,
            "service_id": service["service_id"] if service else "",
            "description": f"{ci_type.replace('_', ' ').title()} for {prefix} workload",
            "environment": environment,
            "status": random.choices(statuses, status_weights)[0],
            "version": version,
            "ip_address": random_ip(),
            "hostname": f"{prefix}-{environment[:4]}-{i+1:04d}.internal.example.com",
            "operating_system": random.choice(config.get("os", ["Linux"])) if "os" in config else "",
            "cpu_cores": cpu_cores,
            "memory_gb": memory_gb,
            "storage_gb": storage_gb,
            "cloud_provider": cloud_provider,
            "cloud_region": cloud_region,
            "cost_per_month": cost,
            "health_status": random.choices(["healthy", "degraded", "unhealthy"], [0.85, 0.1, 0.05])[0],
            "last_health_check": format_datetime(datetime.now() - timedelta(minutes=random.randint(1, 60))),
            "created_at": format_datetime(created_at),
            "updated_at": format_datetime(created_at + timedelta(days=random.randint(0, 60)))
        })

    return cis

def generate_ci_relationships(cis: List[Dict], count: int = 400) -> List[Dict[str, Any]]:
    """Generate CI relationship records."""
    relationships = []
    relationship_types = ["depends_on", "hosts", "connects_to", "runs_on", "uses", "backed_by"]

    # Group CIs by type for logical relationships
    ci_by_type = {}
    for ci in cis:
        ci_type = ci["ci_type"]
        if ci_type not in ci_by_type:
            ci_by_type[ci_type] = []
        ci_by_type[ci_type].append(ci)

    existing_pairs = set()

    # Generate logical relationships
    for _ in range(count):
        # Application -> Database (depends_on)
        if random.random() < 0.3 and "application" in ci_by_type and "database" in ci_by_type:
            source = random.choice(ci_by_type["application"])
            target = random.choice(ci_by_type["database"])
            rel_type = "depends_on"
        # Application -> Cache (depends_on)
        elif random.random() < 0.3 and "application" in ci_by_type and "cache" in ci_by_type:
            source = random.choice(ci_by_type["application"])
            target = random.choice(ci_by_type["cache"])
            rel_type = "depends_on"
        # Server -> Application (hosts)
        elif random.random() < 0.3 and "server" in ci_by_type and "application" in ci_by_type:
            source = random.choice(ci_by_type["server"])
            target = random.choice(ci_by_type["application"])
            rel_type = "hosts"
        # Application -> Message Queue (uses)
        elif random.random() < 0.2 and "application" in ci_by_type and "message_queue" in ci_by_type:
            source = random.choice(ci_by_type["application"])
            target = random.choice(ci_by_type["message_queue"])
            rel_type = "uses"
        # Load Balancer -> Server (connects_to)
        elif random.random() < 0.3 and "load_balancer" in ci_by_type and "server" in ci_by_type:
            source = random.choice(ci_by_type["load_balancer"])
            target = random.choice(ci_by_type["server"])
            rel_type = "connects_to"
        # Container -> Server (runs_on)
        elif random.random() < 0.2 and "container" in ci_by_type and "server" in ci_by_type:
            source = random.choice(ci_by_type["container"])
            target = random.choice(ci_by_type["server"])
            rel_type = "runs_on"
        # Database -> Storage (backed_by)
        elif random.random() < 0.2 and "database" in ci_by_type and "storage" in ci_by_type:
            source = random.choice(ci_by_type["database"])
            target = random.choice(ci_by_type["storage"])
            rel_type = "backed_by"
        else:
            # Random relationship
            source = random.choice(cis)
            target = random.choice(cis)
            rel_type = random.choice(relationship_types)

        # Avoid self-references and duplicates
        pair_key = (source["ci_id"], target["ci_id"], rel_type)
        if source["ci_id"] != target["ci_id"] and pair_key not in existing_pairs:
            existing_pairs.add(pair_key)

            created_at = random_date(365, 30)

            relationships.append({
                "relationship_id": generate_uuid(),
                "source_ci_id": source["ci_id"],
                "target_ci_id": target["ci_id"],
                "relationship_type": rel_type,
                "strength": round(random.uniform(0.5, 1.0), 2),
                "description": f"{source['ci_name']} {rel_type.replace('_', ' ')} {target['ci_name']}",
                "port": random.choice([80, 443, 3306, 5432, 6379, 27017, 9092, None]),
                "protocol": random.choice(["TCP", "HTTP", "HTTPS", "gRPC", None]),
                "is_critical": str(random.random() < 0.3).lower(),
                "created_at": format_datetime(created_at),
                "updated_at": format_datetime(created_at + timedelta(days=random.randint(0, 30)))
            })

    return relationships

def generate_incidents(cis: List[Dict], services: List[Dict], count: int = 300) -> List[Dict[str, Any]]:
    """Generate incident records."""
    incidents = []
    severities = ["critical", "high", "medium", "low"]
    severity_weights = [0.05, 0.15, 0.40, 0.40]
    priorities = ["P1", "P2", "P3", "P4"]
    statuses = ["open", "in_progress", "resolved", "closed"]
    status_weights = [0.1, 0.15, 0.25, 0.5]

    for i in range(count):
        severity = random.choices(severities, severity_weights)[0]
        priority = priorities[severities.index(severity)]
        status = random.choices(statuses, status_weights)[0]

        category = random.choice(list(INCIDENT_CATEGORIES.keys()))
        subcategory = random.choice(INCIDENT_CATEGORIES[category])

        affected_ci = random.choice(cis) if random.random() < 0.9 else None
        affected_service = None
        if affected_ci and affected_ci["service_id"]:
            affected_service = next((s for s in services if s["service_id"] == affected_ci["service_id"]), None)

        created_at = random_date(180, 0)
        acknowledged_at = created_at + timedelta(minutes=random.randint(5, 120)) if status != "open" else None
        resolved_at = None
        closed_at = None
        resolution_time = None

        if status in ["resolved", "closed"]:
            resolution_time = random.randint(15, 480)  # 15 min to 8 hours
            resolved_at = created_at + timedelta(minutes=resolution_time)
            if status == "closed":
                closed_at = resolved_at + timedelta(hours=random.randint(1, 48))

        sla_hours = affected_service["sla_target_hours"] if affected_service else 4
        sla_breached = resolution_time > (sla_hours * 60) if resolution_time else False

        incidents.append({
            "incident_id": generate_uuid(),
            "incident_number": f"INC{i+1:07d}",
            "title": f"{subcategory} - {affected_ci['ci_name'] if affected_ci else 'Unknown CI'}",
            "description": f"{subcategory} detected on {affected_ci['ci_name'] if affected_ci else 'infrastructure'}. "
                          f"Impact: {category.lower()} related issue affecting service availability.",
            "severity": severity,
            "priority": priority,
            "status": status,
            "affected_ci_id": affected_ci["ci_id"] if affected_ci else "",
            "affected_service_id": affected_service["service_id"] if affected_service else "",
            "category": category,
            "subcategory": subcategory,
            "impact_scope": random.choice(["widespread", "limited", "localized"]),
            "reported_by": random.choice(OWNERS),
            "assigned_to": random.choice(OWNERS),
            "assignment_group": random.choice(TEAMS),
            "created_at": format_datetime(created_at),
            "acknowledged_at": format_datetime(acknowledged_at) if acknowledged_at else "",
            "resolved_at": format_datetime(resolved_at) if resolved_at else "",
            "closed_at": format_datetime(closed_at) if closed_at else "",
            "resolution_time_minutes": resolution_time if resolution_time else "",
            "sla_breached": str(sla_breached).lower(),
            "is_major_incident": str(severity == "critical" and random.random() < 0.5).lower()
        })

    return incidents

def generate_problems(cis: List[Dict], incidents: List[Dict], count: int = 50) -> List[Dict[str, Any]]:
    """Generate problem records."""
    problems = []
    statuses = ["open", "in_progress", "resolved", "closed"]
    status_weights = [0.15, 0.25, 0.3, 0.3]
    priorities = ["P1", "P2", "P3", "P4"]
    priority_weights = [0.1, 0.25, 0.4, 0.25]

    # Group incidents by category for realistic problem generation
    incidents_by_category = {}
    for inc in incidents:
        cat = inc["category"]
        if cat not in incidents_by_category:
            incidents_by_category[cat] = []
        incidents_by_category[cat].append(inc)

    for i in range(count):
        status = random.choices(statuses, status_weights)[0]
        priority = random.choices(priorities, priority_weights)[0]

        category = random.choice(list(INCIDENT_CATEGORIES.keys()))
        root_cause = random.choice(PROBLEM_ROOT_CAUSES)
        root_cause_ci = random.choice(cis) if random.random() < 0.8 else None

        related_incidents = incidents_by_category.get(category, [])[:random.randint(2, 10)]

        created_at = random_date(365, 30)
        identified_at = created_at + timedelta(days=random.randint(1, 14))
        resolved_at = None
        closed_at = None

        known_error = random.random() < 0.4
        workaround = random.choice(WORKAROUNDS) if known_error else ""

        if status in ["resolved", "closed"]:
            resolved_at = identified_at + timedelta(days=random.randint(7, 60))
            if status == "closed":
                closed_at = resolved_at + timedelta(days=random.randint(1, 14))

        problems.append({
            "problem_id": generate_uuid(),
            "problem_number": f"PRB{i+1:07d}",
            "title": f"Recurring {category.lower()} issues - {root_cause[:50]}",
            "description": f"Investigation into recurring {category.lower()} incidents. "
                          f"Multiple incidents reported with similar symptoms pointing to {root_cause.lower()}.",
            "status": status,
            "priority": priority,
            "root_cause": root_cause if status in ["resolved", "closed"] else "",
            "root_cause_ci_id": root_cause_ci["ci_id"] if root_cause_ci else "",
            "known_error": str(known_error).lower(),
            "known_error_description": f"Known issue: {root_cause}" if known_error else "",
            "workaround": workaround,
            "category": category,
            "owner": random.choice(OWNERS),
            "assigned_to": random.choice(OWNERS),
            "related_incident_count": len(related_incidents),
            "related_incident_ids": json.dumps([inc["incident_id"] for inc in related_incidents]),
            "created_at": format_datetime(created_at),
            "identified_at": format_datetime(identified_at),
            "resolved_at": format_datetime(resolved_at) if resolved_at else "",
            "closed_at": format_datetime(closed_at) if closed_at else ""
        })

    return problems

def generate_changes(cis: List[Dict], services: List[Dict], count: int = 250) -> List[Dict[str, Any]]:
    """Generate change records."""
    changes = []
    change_types = ["standard", "normal", "emergency"]
    type_weights = [0.4, 0.45, 0.15]
    statuses = ["pending", "open", "in_progress", "resolved", "closed"]
    status_weights = [0.1, 0.1, 0.15, 0.25, 0.4]
    risk_levels = ["low", "medium", "high", "critical"]

    for i in range(count):
        change_type = random.choices(change_types, type_weights)[0]
        status = random.choices(statuses, status_weights)[0]

        category = random.choice(CHANGE_CATEGORIES)
        affected_ci = random.choice(cis) if random.random() < 0.9 else None
        affected_service = None
        if affected_ci and affected_ci["service_id"]:
            affected_service = next((s for s in services if s["service_id"] == affected_ci["service_id"]), None)

        # Risk calculation based on CI importance and change type
        base_risk = random.uniform(0.1, 0.9)
        if change_type == "emergency":
            base_risk = min(base_risk + 0.2, 1.0)
        if affected_service and affected_service["criticality"] in ["platinum", "gold"]:
            base_risk = min(base_risk + 0.15, 1.0)

        risk_level = (
            "critical" if base_risk >= 0.8 else
            "high" if base_risk >= 0.6 else
            "medium" if base_risk >= 0.3 else
            "low"
        )

        created_at = random_date(90, 0)
        scheduled_start = created_at + timedelta(days=random.randint(1, 14))
        scheduled_end = scheduled_start + timedelta(hours=random.randint(1, 8))

        approved_at = None
        actual_start = None
        actual_end = None
        success = None
        caused_incident = False

        if status in ["in_progress", "resolved", "closed"]:
            approved_at = created_at + timedelta(hours=random.randint(4, 72))
            actual_start = scheduled_start + timedelta(minutes=random.randint(-30, 30))

            if status in ["resolved", "closed"]:
                actual_end = actual_start + timedelta(hours=random.randint(1, 6))
                success = random.random() > 0.1  # 90% success rate
                caused_incident = not success and random.random() < 0.5

        changes.append({
            "change_id": generate_uuid(),
            "change_number": f"CHG{i+1:07d}",
            "title": f"{category}: {affected_ci['ci_name'] if affected_ci else 'Infrastructure'}",
            "description": f"{category} for {affected_ci['ci_name'] if affected_ci else 'infrastructure'}. "
                          f"This change involves {category.lower()} activities.",
            "change_type": change_type,
            "status": status,
            "risk_level": risk_level,
            "computed_risk_score": round(base_risk, 4),
            "affected_ci_id": affected_ci["ci_id"] if affected_ci else "",
            "affected_service_id": affected_service["service_id"] if affected_service else "",
            "category": category,
            "reason": f"Required {category.lower()} to improve system stability and performance",
            "implementation_plan": f"1. Pre-checks\n2. Backup current state\n3. Apply {category.lower()}\n4. Verify\n5. Rollback if needed",
            "rollback_plan": "1. Stop change\n2. Restore from backup\n3. Verify service restoration\n4. Notify stakeholders",
            "test_plan": "1. Functional testing\n2. Performance validation\n3. Integration check",
            "requested_by": random.choice(OWNERS),
            "assigned_to": random.choice(OWNERS),
            "approved_by": random.choice(OWNERS) if approved_at else "",
            "implemented_by": random.choice(OWNERS) if actual_start else "",
            "scheduled_start": format_datetime(scheduled_start),
            "scheduled_end": format_datetime(scheduled_end),
            "actual_start": format_datetime(actual_start) if actual_start else "",
            "actual_end": format_datetime(actual_end) if actual_end else "",
            "created_at": format_datetime(created_at),
            "approved_at": format_datetime(approved_at) if approved_at else "",
            "closed_at": format_datetime(actual_end) if actual_end else "",
            "success": str(success).lower() if success is not None else "",
            "failure_reason": "Unexpected system behavior during change implementation" if success is False else "",
            "caused_incident": str(caused_incident).lower()
        })

    return changes

def generate_resolutions(incidents: List[Dict], count: int = 250) -> List[Dict[str, Any]]:
    """Generate resolution records for resolved/closed incidents."""
    resolutions = []
    resolution_types = ["fix", "workaround", "rollback", "restart", "configuration_change", "patch"]
    type_weights = [0.35, 0.2, 0.1, 0.15, 0.1, 0.1]

    # Get resolved/closed incidents
    resolved_incidents = [inc for inc in incidents if inc["status"] in ["resolved", "closed"]]

    for inc in resolved_incidents[:count]:
        resolution_type = random.choices(resolution_types, type_weights)[0]
        fix = random.choice(RESOLUTION_FIXES)
        workaround = random.choice(WORKAROUNDS) if resolution_type == "workaround" else ""
        preventive = random.choice(PREVENTIVE_ACTIONS)
        root_cause = random.choice(PROBLEM_ROOT_CAUSES)

        resolutions.append({
            "resolution_id": generate_uuid(),
            "incident_id": inc["incident_id"],
            "resolution_type": resolution_type,
            "title": f"Resolution for {inc['incident_number']}",
            "description": f"Resolved {inc['category'].lower()} issue by {fix.lower()}",
            "root_cause": root_cause,
            "fix_applied": fix,
            "workaround": workaround,
            "preventive_action": preventive,
            "resolved_by": inc["assigned_to"],
            "time_to_resolve_minutes": inc["resolution_time_minutes"],
            "was_effective": str(random.random() > 0.1).lower(),
            "reoccurrence_count": random.randint(0, 3),
            "knowledge_article_id": f"KB{random.randint(1000, 9999)}" if random.random() < 0.6 else "",
            "created_at": inc["resolved_at"],
            "updated_at": inc["closed_at"] if inc["closed_at"] else inc["resolved_at"]
        })

    return resolutions

def generate_metrics_usage(cis: List[Dict], count: int = 3000) -> List[Dict[str, Any]]:
    """Generate metrics usage records."""
    metrics = []
    metric_types = [
        ("cpu_usage", "%", 0, 100, 70, 90),
        ("memory_usage", "%", 0, 100, 75, 90),
        ("disk_usage", "%", 0, 100, 80, 95),
        ("network_in", "Mbps", 0, 1000, 700, 900),
        ("network_out", "Mbps", 0, 1000, 700, 900),
        ("request_count", "req/s", 0, 10000, 7000, 9000),
        ("error_rate", "%", 0, 10, 1, 5),
        ("latency_p50", "ms", 10, 500, 100, 200),
        ("latency_p99", "ms", 50, 2000, 500, 1000),
        ("connection_count", "count", 0, 1000, 700, 900)
    ]

    # Generate metrics for the last 30 days, every hour for selected CIs
    selected_cis = random.sample(cis, min(100, len(cis)))

    for _ in range(count):
        ci = random.choice(selected_cis)
        metric_name, unit, min_val, max_val, warn_thresh, crit_thresh = random.choice(metric_types)

        # Generate realistic value based on CI health
        if ci["health_status"] == "healthy":
            value = random.uniform(min_val, warn_thresh * 0.8)
        elif ci["health_status"] == "degraded":
            value = random.uniform(warn_thresh * 0.9, crit_thresh * 0.9)
        else:  # unhealthy
            value = random.uniform(crit_thresh * 0.9, max_val)

        value = round(value, 2)
        is_anomaly = value > crit_thresh or (value > warn_thresh and random.random() < 0.2)
        anomaly_score = round(min((value / crit_thresh) - 0.5, 1.0), 4) if is_anomaly else 0.0

        collected_at = random_date(30, 0)

        metrics.append({
            "metric_id": generate_uuid(),
            "ci_id": ci["ci_id"],
            "metric_type": metric_name,
            "metric_value": value,
            "unit": unit,
            "threshold_warning": warn_thresh,
            "threshold_critical": crit_thresh,
            "is_anomaly": str(is_anomaly).lower(),
            "anomaly_score": anomaly_score,
            "collected_at": format_datetime(collected_at)
        })

    return metrics

# ============================================================================
# CSV WRITERS
# ============================================================================

def write_csv(filename: str, data: List[Dict], fieldnames: List[str] = None):
    """Write data to CSV file."""
    if not data:
        print(f"Warning: No data to write for {filename}")
        return

    filepath = OUTPUT_DIR / filename
    fieldnames = fieldnames or list(data[0].keys())

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    print(f"Generated {filepath}: {len(data)} records")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Generate all sample datasets."""
    print("=" * 60)
    print("InfraSight-AI: Synthetic Data Generation")
    print("=" * 60)
    print()

    # Generate data in order of dependencies
    print("Generating services...")
    services = generate_services(30)

    print("Generating configuration items...")
    cis = generate_configuration_items(services, 300)

    print("Generating CI relationships...")
    relationships = generate_ci_relationships(cis, 400)

    print("Generating incidents...")
    incidents = generate_incidents(cis, services, 300)

    print("Generating problems...")
    problems = generate_problems(cis, incidents, 50)

    print("Generating changes...")
    changes = generate_changes(cis, services, 250)

    print("Generating resolutions...")
    resolutions = generate_resolutions(incidents, 250)

    print("Generating metrics usage...")
    metrics = generate_metrics_usage(cis, 3000)

    print()
    print("Writing CSV files...")

    # Write all CSVs
    write_csv("services.csv", services)
    write_csv("configuration_items.csv", cis)
    write_csv("ci_relationships.csv", relationships)
    write_csv("incidents.csv", incidents)
    write_csv("problems.csv", problems)
    write_csv("changes.csv", changes)
    write_csv("resolutions.csv", resolutions)
    write_csv("metrics_usage.csv", metrics)

    print()
    print("=" * 60)
    print("Data generation complete!")
    print(f"Output directory: {OUTPUT_DIR}")
    print("=" * 60)

    # Summary
    print("\nSummary:")
    print(f"  - Services: {len(services)}")
    print(f"  - Configuration Items: {len(cis)}")
    print(f"  - CI Relationships: {len(relationships)}")
    print(f"  - Incidents: {len(incidents)}")
    print(f"  - Problems: {len(problems)}")
    print(f"  - Changes: {len(changes)}")
    print(f"  - Resolutions: {len(resolutions)}")
    print(f"  - Metrics: {len(metrics)}")

if __name__ == "__main__":
    main()
