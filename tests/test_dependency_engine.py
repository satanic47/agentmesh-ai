import pytest
from app.graph.falkor_client import db_client
from app.graph.schema import TaskNode, TaskStatus
from app.agents.swarm import AgentSwarm
from app.agents.scenarios import load_zero_trust_mission, inject_cycle_scenario

def test_ready_tasks_resolution():
    db_client.clear()
    t1 = TaskNode(title="Alpha", description="Prereq", status=TaskStatus.PENDING)
    t2 = TaskNode(title="Beta", description="Depends on Alpha", status=TaskStatus.PENDING)
    
    db_client.create_task(t1)
    db_client.create_task(t2, depends_on=[t1.id])
    
    # Initially, only t1 should be ready
    ready = db_client.get_ready_tasks()
    ready_ids = [t["id"] for t in ready]
    assert t1.id in ready_ids
    assert t2.id not in ready_ids
    
    # Complete t1
    db_client.update_task_status(t1.id, "completed")
    
    # Now t2 must be ready
    ready = db_client.get_ready_tasks()
    ready_ids = [t["id"] for t in ready]
    assert t2.id in ready_ids

def test_deadlock_detection():
    db_client.clear()
    cycle_info = inject_cycle_scenario()
    
    cycles = db_client.detect_dependency_cycles()
    assert len(cycles) > 0

def test_swarm_execution_flow():
    load_zero_trust_mission()
    swarm = AgentSwarm()
    
    # Step 1
    res1 = swarm.step()
    assert res1["executed"] is True
    
    # Run all
    history = swarm.run_all(max_steps=10)
    assert len(history) > 0
