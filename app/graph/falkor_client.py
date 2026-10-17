"""
FalkorDB Client and Context Manager for AgentMesh
Connects to real FalkorDB instance with automatic fallback to LocalGraphEngine
if the database server is not reachable.
"""

import socket
import logging
from typing import Dict, Any, List, Optional
from app.config import settings
from app.graph import queries
from app.graph.schema import AgentNode, GoalNode, TaskNode, MemoryNode, DecisionNode, ArtifactNode
from app.graph.local_engine import LocalGraphEngine

logger = logging.getLogger("agentmesh.graph")

def _is_server_available(host: str, port: int, timeout: float = 0.1) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

class FalkorClient:
    def __init__(self):
        self.is_connected = False
        self.mode = "uninitialized"
        self.graph = None
        self._init_connection()

    def _init_connection(self):
        # First do a fast socket probe so we don't block on TCP handshake timeouts
        if _is_server_available(settings.FALKORDB_HOST, settings.FALKORDB_PORT):
            try:
                from falkordb import FalkorDB
                logger.info(f"Connecting to FalkorDB at {settings.FALKORDB_HOST}:{settings.FALKORDB_PORT}...")
                client = FalkorDB(
                    host=settings.FALKORDB_HOST,
                    port=settings.FALKORDB_PORT,
                    password=settings.FALKORDB_PASSWORD,
                    socket_connect_timeout=1.0
                )
                client.list_graphs()
                self.graph = client.select_graph(settings.FALKORDB_GRAPH_NAME)
                self.is_connected = True
                self.mode = "falkordb_live"
                logger.info(f"Successfully connected to FalkorDB live instance (Graph: {settings.FALKORDB_GRAPH_NAME})")
                self._init_constraints()
                return
            except Exception as e:
                logger.warning(f"FalkorDB handshake error: {e}")

        if settings.AUTO_FALLBACK_LOCAL:
            logger.info("Initializing In-Memory Cypher Graph Engine (local development mode).")
            self.graph = LocalGraphEngine(settings.FALKORDB_GRAPH_NAME)
            self.is_connected = True
            self.mode = "in_memory_engine"
        else:
            raise ConnectionError(f"Could not connect to FalkorDB at {settings.FALKORDB_HOST}:{settings.FALKORDB_PORT}")

    def _init_constraints(self):
        if self.mode == "falkordb_live":
            for q in queries.INIT_INDEXES:
                try:
                    self.graph.query(q)
                except Exception as ex:
                    logger.debug(f"Index notice: {ex}")

    def query(self, cypher_query: str, params: Dict[str, Any] = None):
        return self.graph.query(cypher_query, params or {})

    # High-level Agent Node Operations
    def register_agent(self, agent: AgentNode) -> AgentNode:
        self.query(queries.CREATE_AGENT, {
            "id": agent.id,
            "name": agent.name,
            "role": agent.role.value if hasattr(agent.role, "value") else str(agent.role),
            "status": agent.status,
            "capabilities": agent.capabilities,
            "last_active": agent.last_active
        })
        return agent

    def create_goal(self, goal: GoalNode) -> GoalNode:
        self.query(queries.CREATE_GOAL, {
            "id": goal.id,
            "title": goal.title,
            "description": goal.description,
            "status": goal.status,
            "created_at": goal.created_at
        })
        return goal

    def create_task(self, task: TaskNode, goal_id: Optional[str] = None, depends_on: Optional[List[str]] = None) -> TaskNode:
        self.query(queries.CREATE_TASK, {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status.value if hasattr(task.status, "value") else str(task.status),
            "priority": task.priority,
            "assigned_to": task.assigned_to,
            "created_at": task.created_at,
            "completed_at": task.completed_at
        })
        if goal_id:
            self.query(queries.LINK_SUBTASK, {"task_id": task.id, "goal_id": goal_id})
        if depends_on:
            for dep_id in depends_on:
                self.query(queries.LINK_DEPENDENCY, {"task_id": task.id, "depends_on_id": dep_id})
        return task

    def record_memory(self, memory: MemoryNode, agent_id: str) -> MemoryNode:
        self.query(queries.CREATE_MEMORY, {
            "id": memory.id,
            "content": memory.content,
            "category": memory.category,
            "confidence": memory.confidence,
            "source_agent": memory.source_agent,
            "timestamp": memory.timestamp
        })
        self.query(queries.LINK_AGENT_MEMORY, {"agent_id": agent_id, "memory_id": memory.id})
        return memory

    def record_decision(self, decision: DecisionNode, agent_id: str, task_id: Optional[str] = None) -> DecisionNode:
        self.query(queries.CREATE_DECISION, {
            "id": decision.id,
            "rationale": decision.rationale,
            "outcome": decision.outcome,
            "decided_by": decision.decided_by,
            "timestamp": decision.timestamp
        })
        self.query(queries.LINK_AGENT_DECISION, {"agent_id": agent_id, "decision_id": decision.id})
        if task_id:
            self.query(queries.LINK_DECISION_TASK, {"decision_id": decision.id, "task_id": task_id})
        return decision

    def link_contradiction(self, dec_id_1: str, dec_id_2: str):
        return self.query(queries.LINK_DECISION_CONTRADICTION, {
            "decision_id_1": dec_id_1,
            "decision_id_2": dec_id_2
        })

    def update_task_status(self, task_id: str, status: str):
        q = "MATCH (t:Task {id: $id}) SET t.status = $status RETURN t"
        self.query(q, {"id": task_id, "status": status})

    # Coordination & Graph Traversal Operations
    def get_ready_tasks(self) -> List[Dict[str, Any]]:
        result = self.query(queries.GET_READY_TASKS)
        tasks = []
        for row in result:
            tasks.append({
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "priority": row[3]
            })
        return tasks

    def get_task_context_subgraph(self, task_id: str) -> Dict[str, Any]:
        result = self.query(queries.GET_TASK_CONTEXT_SUBGRAPH, {"task_id": task_id})
        if not result or len(result) == 0:
            return {}
        row = result.result_set[0] if hasattr(result, "result_set") and result.result_set else list(result)[0]
        return {
            "task_title": row[0],
            "task_desc": row[1],
            "goal_title": row[2],
            "prerequisites": row[3] or [],
            "past_decisions": row[4] or [],
            "memory_facts": row[5] or []
        }

    def detect_dependency_cycles(self) -> List[Dict[str, Any]]:
        result = self.query(queries.DETECT_CYCLES)
        cycles = []
        for row in result:
            nodes_data = []
            for n in row[0]:
                if hasattr(n, "properties"):
                    nodes_data.append(n.properties.get("title", n.properties.get("id")))
                elif isinstance(n, dict):
                    nodes_data.append(n.get("title", n.get("id")))
            cycles.append({
                "cycle": nodes_data,
                "length": row[1]
            })
        return cycles

    def get_all_memories(self) -> List[Dict[str, Any]]:
        result = self.query(queries.SEARCH_MEMORIES)
        memories = []
        for row in result:
            memories.append({
                "id": row[0],
                "content": row[1],
                "category": row[2],
                "confidence": row[3],
                "timestamp": row[4],
                "discovered_by": row[5]
            })
        return memories

    def get_cytoscape_elements(self) -> List[Dict[str, Any]]:
        result = self.query(queries.GET_FULL_GRAPH)
        elements = []
        node_ids_seen = set()
        edge_ids_seen = set()

        for row in result:
            s_labels, s_props, rel_type, rel_props, t_labels, t_props = row[0], row[1], row[2], row[3], row[4], row[5]
            if s_props and "id" in s_props:
                sid = s_props["id"]
                if sid not in node_ids_seen:
                    node_ids_seen.add(sid)
                    label = s_labels[0] if s_labels else "Node"
                    title = s_props.get("name") or s_props.get("title") or s_props.get("content", sid[:12])
                    elements.append({
                        "data": {
                            "id": sid,
                            "label": f"[{label}] {title[:25]}",
                            "type": label,
                            "properties": s_props
                        }
                    })

            if rel_type and t_props and "id" in t_props:
                tid = t_props["id"]
                if tid not in node_ids_seen:
                    node_ids_seen.add(tid)
                    label = t_labels[0] if t_labels else "Node"
                    title = t_props.get("name") or t_props.get("title") or t_props.get("content", tid[:12])
                    elements.append({
                        "data": {
                            "id": tid,
                            "label": f"[{label}] {title[:25]}",
                            "type": label,
                            "properties": t_props
                        }
                    })

                edge_id = f"e_{sid}_{rel_type}_{tid}"
                if edge_id not in edge_ids_seen:
                    edge_ids_seen.add(edge_id)
                    elements.append({
                        "data": {
                            "id": edge_id,
                            "source": sid,
                            "target": tid,
                            "label": rel_type,
                            "properties": rel_props or {}
                        }
                    })

        return elements

    def clear(self):
        if self.mode == "falkordb_live":
            self.graph.delete()
            self._init_connection()
        else:
            self.graph.clear()

# Global singleton
db_client = FalkorClient()
