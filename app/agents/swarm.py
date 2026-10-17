"""
Multi-Agent Swarm Orchestrator for AgentMesh.
Coordinates specialized agents using FalkorDB as the central nervous system.
"""

from typing import Dict, Any, List, Optional
import time
import logging
from app.graph.schema import AgentRole, TaskStatus, DecisionNode, MemoryNode
from app.graph.falkor_client import db_client
from app.agents.base import BaseAgent

logger = logging.getLogger("agentmesh.swarm")

class AgentSwarm:
    def __init__(self):
        self.client = db_client
        self.agents: Dict[str, BaseAgent] = {}
        self.init_default_swarm()

    def init_default_swarm(self):
        """Initializes specialized agents representing enterprise roles."""
        self.register_agent("Nova-Planner", AgentRole.PLANNER, ["goal_decomposition", "dependency_analysis"])
        self.register_agent("Sentinel-Security", AgentRole.AUDITOR, ["vulnerability_scan", "policy_audit", "conflict_resolution"])
        self.register_agent("Atlas-Engineer", AgentRole.ENGINEER, ["infrastructure_deployment", "code_generation", "containerization"])
        self.register_agent("Chronos-Memory", AgentRole.MEMORY_MANAGER, ["semantic_indexing", "cross_session_synthesis"])

    def register_agent(self, name: str, role: AgentRole, capabilities: List[str]) -> BaseAgent:
        agent = BaseAgent(name, role, capabilities)
        self.agents[agent.name] = agent
        return agent

    def dispatch_agent_for_task(self, task: Dict[str, Any]) -> BaseAgent:
        """Selects the most suitable agent based on task description and capabilities."""
        title = task["title"].lower()
        desc = task.get("description", "").lower()

        if any(w in title or w in desc for w in ["security", "audit", "compliance", "policy", "vulnerability"]):
            return self.agents.get("Sentinel-Security", list(self.agents.values())[0])
        elif any(w in title or w in desc for w in ["deploy", "build", "code", "database", "container", "api"]):
            return self.agents.get("Atlas-Engineer", list(self.agents.values())[0])
        elif any(w in title or w in desc for w in ["plan", "architecture", "design", "evaluate"]):
            return self.agents.get("Nova-Planner", list(self.agents.values())[0])
        else:
            return self.agents.get("Chronos-Memory", list(self.agents.values())[0])

    def step(self) -> Dict[str, Any]:
        """
        Executes one coordination step:
        1. Checks Cypher for ready tasks (all dependencies completed).
        2. Assigns appropriate agent.
        3. Executes task, updates graph state, records decisions & memories.
        """
        ready_tasks = self.client.get_ready_tasks()
        if not ready_tasks:
            # Check if there are remaining pending tasks that might be deadlocked
            cycles = self.client.detect_dependency_cycles()
            return {
                "executed": False,
                "message": "No ready tasks available.",
                "deadlock_detected": len(cycles) > 0,
                "cycles": cycles
            }

        # Pick the highest priority ready task
        task = ready_tasks[0]
        agent = self.dispatch_agent_for_task(task)

        logger.info(f"Dispatching Agent '{agent.name}' for Task '{task['title']}'...")
        result = agent.execute_task(task)

        return {
            "executed": True,
            "agent": agent.name,
            "task": task,
            "result": result,
            "remaining_ready": len(ready_tasks) - 1
        }

    def run_all(self, max_steps: int = 20) -> List[Dict[str, Any]]:
        """Runs the coordination loop until all tasks are completed or blocked."""
        history = []
        for _ in range(max_steps):
            step_result = self.step()
            history.append(step_result)
            if not step_result["executed"]:
                break
            time.sleep(0.05)
        return history
