"""
Base Agent Interface for AgentMesh.
Provides agents with direct graph-native perception and action capabilities via FalkorDB.
"""

from typing import Dict, Any, List, Optional
import time
from app.graph.schema import AgentNode, AgentRole, MemoryNode, DecisionNode, TaskNode, TaskStatus
from app.graph.falkor_client import db_client

class BaseAgent:
    def __init__(self, name: str, role: AgentRole, capabilities: List[str] = None):
        self.node = AgentNode(
            name=name,
            role=role,
            capabilities=capabilities or [],
            status="idle"
        )
        self.client = db_client
        self._register()

    def _register(self):
        self.client.register_agent(self.node)

    @property
    def id(self) -> str:
        return self.node.id

    @property
    def name(self) -> str:
        return self.node.name

    def perceive_task_context(self, task_id: str) -> Dict[str, Any]:
        """
        Extracts the 2-hop connected graph context from FalkorDB for prompt injection.
        """
        context = self.client.get_task_context_subgraph(task_id)
        return context

    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a task using graph context, records decisions, and saves discovered memories.
        """
        task_id = task["id"]
        self.node.status = "working"
        self.client.update_task_status(task_id, TaskStatus.IN_PROGRESS.value)

        # 1. Fetch Graph Context Subgraph from FalkorDB
        context = self.perceive_task_context(task_id)

        # 2. Simulate Reasoning & Decision Making based on graph context
        rationale = f"Evaluated prerequisite state and {len(context.get('past_decisions', []))} prior decisions in FalkorDB. Executing {task['title']}."
        outcome = f"Successfully completed {task['title']} within security and architecture constraints."

        decision = DecisionNode(
            rationale=rationale,
            outcome=outcome,
            decided_by=self.name
        )
        self.client.record_decision(decision, self.id, task_id)

        # 3. Store new Semantic / Episodic Memory in FalkorDB
        memory = MemoryNode(
            content=f"{self.name} verified: {task['title']} conforms with operational criteria.",
            category="semantic",
            confidence=0.98,
            source_agent=self.name
        )
        self.client.record_memory(memory, self.id)

        # 4. Mark Task Completed in Graph
        self.client.update_task_status(task_id, TaskStatus.COMPLETED.value)
        self.node.status = "idle"

        return {
            "task_id": task_id,
            "decision": decision.model_dump(),
            "memory": memory.model_dump(),
            "status": "completed"
        }
