"""
FastAPI REST API Routes for AgentMesh.
Provides endpoints for graph visualization, agent coordination, and live Cypher execution.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import time
from app.graph.falkor_client import db_client
from app.graph.schema import TaskNode, TaskStatus
from app.agents.swarm import AgentSwarm
from app.agents import scenarios

router = APIRouter()
swarm = AgentSwarm()

class CypherQueryRequest(BaseModel):
    query: str
    params: Optional[Dict[str, Any]] = None

class CreateTaskRequest(BaseModel):
    title: str
    description: str
    priority: int = 1
    goal_id: Optional[str] = None
    depends_on: Optional[List[str]] = None

@router.get("/status")
def get_status():
    elements = db_client.get_cytoscape_elements()
    node_count = sum(1 for e in elements if "source" not in e["data"])
    edge_count = sum(1 for e in elements if "source" in e["data"])
    cycles = db_client.detect_dependency_cycles()

    return {
        "engine_mode": db_client.mode,
        "is_connected": db_client.is_connected,
        "graph_name": db_client.graph.graph_name if hasattr(db_client.graph, "graph_name") else "agentmesh",
        "node_count": node_count,
        "edge_count": edge_count,
        "active_agents": len(swarm.agents),
        "deadlock_detected": len(cycles) > 0,
        "cycles": cycles
    }

@router.get("/graph/elements")
def get_graph_elements():
    """Returns nodes and edges formatted for Cytoscape.js rendering."""
    return db_client.get_cytoscape_elements()

@router.post("/graph/query")
def execute_cypher_query(req: CypherQueryRequest):
    """Executes an arbitrary Cypher query and returns execution time and formatted records."""
    start_time = time.time()
    try:
        result = db_client.query(req.query, req.params or {})
        latency_ms = round((time.time() - start_time) * 1000, 2)

        records = []
        header = getattr(result, "header", [])
        for row in result:
            record_row = []
            for cell in row:
                if hasattr(cell, "properties"):
                    record_row.append(cell.properties)
                else:
                    record_row.append(cell)
            records.append(record_row)

        return {
            "query": req.query,
            "latency_ms": latency_ms,
            "header": header,
            "records": records,
            "count": len(records)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tasks/ready")
def get_ready_tasks():
    """Returns tasks that have zero uncompleted dependencies."""
    return db_client.get_ready_tasks()

@router.post("/tasks/create")
def create_task(req: CreateTaskRequest):
    task = TaskNode(
        title=req.title,
        description=req.description,
        priority=req.priority
    )
    db_client.create_task(task, goal_id=req.goal_id, depends_on=req.depends_on)
    return {"message": "Task created successfully", "task": task.model_dump()}

@router.post("/swarm/step")
def swarm_step():
    """Executes a single step in multi-agent graph coordination."""
    return swarm.step()

@router.post("/swarm/run")
def swarm_run_all():
    """Runs autonomous coordination until all ready tasks are finished."""
    history = swarm.run_all()
    return {"executed_steps": len(history), "history": history}

@router.get("/memories")
def get_memories():
    return db_client.get_all_memories()

@router.post("/scenarios/reset")
def reset_scenario():
    data = scenarios.load_zero_trust_mission()
    return {"message": "Reset to Zero-Trust Deployment Mission", "data": data}

@router.post("/scenarios/cycle")
def inject_cycle():
    res = scenarios.inject_cycle_scenario()
    return {"message": "Injected circular dependency into graph", "data": res}
