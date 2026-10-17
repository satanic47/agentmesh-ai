"""
Pre-built Real-World Multi-Agent Mission Scenarios for AgentMesh.
Populates FalkorDB with interconnected goals, tasks, dependencies, and baseline memories.
"""

from app.graph.schema import GoalNode, TaskNode, TaskStatus, MemoryNode, DecisionNode
from app.graph.falkor_client import db_client

def load_zero_trust_mission():
    """
    Loads an Enterprise Zero-Trust Architecture & Deployment Mission.
    Demonstrates graph-based task dependency resolution, multi-agent specialization,
    and causal decision auditing.
    """
    client = db_client
    client.clear()

    # 1. Main Goal
    goal = GoalNode(
        title="Deploy Enterprise Zero-Trust Microservice Mesh",
        description="Architect, audit, and deploy a secure microservice fabric with automated compliance verification in FalkorDB."
    )
    client.create_goal(goal)

    # 2. Tasks with Dependencies
    t1 = TaskNode(
        title="Threat Model & Attack Vector Analysis",
        description="Audit service communication topology and identify high-risk ingress points.",
        priority=3
    )
    client.create_task(t1, goal_id=goal.id)

    t2 = TaskNode(
        title="FalkorDB Context Store Provisioning",
        description="Deploy high-throughput FalkorDB graph database cluster for agent context and episodic memory.",
        priority=2
    )
    client.create_task(t2, goal_id=goal.id)

    t3 = TaskNode(
        title="Implement Mutual TLS & Policy Gateways",
        description="Configure mTLS certificates and fine-grained RBAC gateway across services.",
        priority=2
    )
    client.create_task(t3, goal_id=goal.id, depends_on=[t1.id, t2.id])

    t4 = TaskNode(
        title="Automated Penetration Test & Security Audit",
        description="Simulate privilege escalation and verify that zero-trust boundaries hold under adversarial load.",
        priority=3
    )
    client.create_task(t4, goal_id=goal.id, depends_on=[t3.id])

    t5 = TaskNode(
        title="Production Canary Release",
        description="Route 10% live customer traffic to verified zero-trust cluster with real-time telemetry.",
        priority=1
    )
    client.create_task(t5, goal_id=goal.id, depends_on=[t4.id])

    # 3. Seed Prior Institutional Memories
    m1 = MemoryNode(
        content="SOC2 Compliance Policy Sec-4.2 requires all service-to-service calls to use encrypted channels.",
        category="semantic",
        confidence=1.0,
        source_agent="Sentinel-Security"
    )
    client.record_memory(m1, "agent_security")

    m2 = MemoryNode(
        content="FalkorDB benchmark achieved <2ms Cypher latency on 10,000 node graph traversal.",
        category="episodic",
        confidence=0.99,
        source_agent="Atlas-Engineer"
    )
    client.record_memory(m2, "agent_engineer")

    return {
        "goal": goal.model_dump(),
        "tasks": [t1.model_dump(), t2.model_dump(), t3.model_dump(), t4.model_dump(), t5.model_dump()]
    }

def inject_cycle_scenario():
    """
    Injects a circular dependency to demonstrate FalkorDB's real-time deadlock detection.
    """
    client = db_client
    tA = TaskNode(title="Task Alpha: Compile Schema", description="Requires Task Gamma before finalizing.")
    tB = TaskNode(title="Task Beta: Generate API SDK", description="Requires Task Alpha to compile.")
    tC = TaskNode(title="Task Gamma: Validate Types", description="Requires Task Beta to exist.")

    client.create_task(tA)
    client.create_task(tB, depends_on=[tA.id])
    client.create_task(tC, depends_on=[tB.id])
    # Create cycle: Alpha depends on Gamma
    client.query("MATCH (tA:Task {id: $a}), (tC:Task {id: $c}) MERGE (tA)-[:DEPENDS_ON]->(tC)", {"a": tA.id, "c": tC.id})

    return {"cycle_created": [tA.id, tB.id, tC.id]}
