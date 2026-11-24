import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class TaskRole(str, Enum):
    IMPLEMENT = "implement"
    TEST = "test"
    REVIEW = "review"
    DOCUMENT = "document"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    GATING = "gating"
    PASSED = "passed"
    FAILED = "failed"
    QUARANTINED = "quarantined"
    BLOCKED = "blocked"


class Task(BaseModel):
    id: str
    title: str
    description: str
    role: TaskRole
    dependencies: List[str] = Field(default_factory=list)
    agent_type: Optional[str] = None
    target_files: List[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    assigned_worktree: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    traceparent: Optional[str] = None


class TaskGraph(BaseModel):
    feature_title: str
    feature_description: str
    tasks: Dict[str, Task] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class AgentStatus(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentRun(BaseModel):
    run_id: str
    task_id: str
    agent_type: str
    worktree_path: str
    status: AgentStatus = AgentStatus.STARTING
    start_time: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    end_time: Optional[str] = None
    exit_code: Optional[int] = None
    log_output: List[str] = Field(default_factory=list)
    cost_usd: float = 0.0


class AgentResult(BaseModel):
    run_id: str
    task_id: str
    success: bool
    modified_files: List[str] = Field(default_factory=list)
    output_summary: str = ""
    error_log: Optional[str] = None


class GateCheckType(str, Enum):
    EVAL = "eval"
    REVIEW = "review"
    TEST = "test"


class GateResult(BaseModel):
    gate_type: GateCheckType
    passed: bool
    score: float = 1.0
    details: Dict[str, Any] = Field(default_factory=dict)
    violations: List[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class TaskGateReport(BaseModel):
    task_id: str
    all_passed: bool
    results: List[GateResult] = Field(default_factory=list)
    diagnosis: Optional[str] = None


class ModelRouteResult(BaseModel):
    task_role: TaskRole
    selected_model: str
    provider: str
    estimated_cost_per_1k: float
    latency_ms: Optional[float] = None
