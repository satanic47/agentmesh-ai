import pytest
from app.graph.falkor_client import db_client
from app.graph.schema import AgentNode, AgentRole, GoalNode, TaskNode, MemoryNode, DecisionNode

def test_node_creation_and_query():
    db_client.clear()
    
    # Create Agent
    agent = AgentNode(name="Test-Orchestrator", role=AgentRole.ORCHESTRATOR)
    db_client.register_agent(agent)
    
    # Create Goal
    goal = GoalNode(title="Test Mission", description="Verify Cypher Query Operations")
    db_client.create_goal(goal)
    
    # Create Task
    task = TaskNode(title="Unit Test Task", description="Execute assertion")
    db_client.create_task(task, goal_id=goal.id)
    
    # Query graph
    elements = db_client.get_cytoscape_elements()
    node_ids = [e["data"]["id"] for e in elements if "source" not in e["data"]]
    
    assert agent.id in node_ids
    assert goal.id in node_ids
    assert task.id in node_ids

def test_relationship_linking():
    db_client.clear()
    t1 = TaskNode(title="Prerequisite Task", description="Step 1")
    t2 = TaskNode(title="Dependent Task", description="Step 2")
    
    db_client.create_task(t1)
    db_client.create_task(t2, depends_on=[t1.id])
    
    elements = db_client.get_cytoscape_elements()
    edges = [e["data"] for e in elements if "source" in e["data"]]
    
    dep_edge = next((e for e in edges if e["source"] == t2.id and e["target"] == t1.id and e["label"] == "DEPENDS_ON"), None)
    assert dep_edge is not None
