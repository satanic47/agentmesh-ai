from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import time
import uuid

class NodeLabel(str, Enum):
    AGENT = "Agent"
    GOAL = "Goal"
    TASK = "Task"
    MEMORY = "Memory"
    DECISION = "Decision"
    ARTIFACT = "Artifact"

class EdgeType(str, Enum):
    ASSIGNED_TO = "ASSIGNED_TO"
    DEPENDS_ON = "DEPENDS_ON"
    SUBTASK_OF = "SUBTASK_OF"
    DISCOVERED = "DISCOVERED"
    DECIDED = "DECIDED"
    RESOLVES = "RESOLVES"
    CONTRADICTS = "CONTRADICTS"
    PRODUCED = "PRODUCED"

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"

class AgentRole(str, Enum):
    ORCHESTRATOR = "Orchestrator"
    RESEARCHER = "Researcher"
    PLANNER = "Planner"
    ENGINEER = "Engineer"
    AUDITOR = "Auditor"
    MEMORY_MANAGER = "MemoryManager"

class AgentNode(BaseModel):
    id: str = Field(default_factory=lambda: f"agent_{uuid.uuid4().hex[:8]}")
    name: str
    role: AgentRole
    capabilities: List[str] = Field(default_factory=list)
    status: str = "idle"
    last_active: float = Field(default_factory=time.time)

class GoalNode(BaseModel):
    id: str = Field(default_factory=lambda: f"goal_{uuid.uuid4().hex[:8]}")
    title: str
    description: str
    status: str = "active"
    created_at: float = Field(default_factory=time.time)

class TaskNode(BaseModel):
    id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:8]}")
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 1
    assigned_to: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    completed_at: Optional[float] = None

class MemoryNode(BaseModel):
    id: str = Field(default_factory=lambda: f"mem_{uuid.uuid4().hex[:8]}")
    content: str
    category: str = "episodic"  # episodic, semantic, procedural
    confidence: float = 1.0
    source_agent: str
    timestamp: float = Field(default_factory=time.time)

class DecisionNode(BaseModel):
    id: str = Field(default_factory=lambda: f"dec_{uuid.uuid4().hex[:8]}")
    rationale: str
    outcome: str
    decided_by: str
    timestamp: float = Field(default_factory=time.time)

class ArtifactNode(BaseModel):
    id: str = Field(default_factory=lambda: f"art_{uuid.uuid4().hex[:8]}")
    title: str
    uri: str
    artifact_type: str = "code"
    created_at: float = Field(default_factory=time.time)
