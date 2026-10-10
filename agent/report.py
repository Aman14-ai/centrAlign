from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    step: Optional[int] = None
    type: str                    # "screenshot" | "api_response" | "page_message" | "rollback" | "approval"
    description: str = ""
    data: dict = Field(default_factory=dict)


class ApprovalItem(BaseModel):
    timestamp: str
    question: str
    decision: Optional[str] = None
    answer: Optional[str] = None
    action: Optional[dict] = None
    risk_score: Optional[float] = None


class FailureItem(BaseModel):
    step: Optional[int] = None
    tool: str
    type: str
    error: str
    signature: str


class RecoveryItem(BaseModel):
    signature: str
    strategy_tool: str
    strategy_reason: str = ""
    source: str                  # "memory_exact" | "memory_similar" | "llm"
    succeeded: bool = False


class FinalReport(BaseModel):
    # Identity
    run_id: str
    thread_id: str
    timestamp: str

    # Task
    task: str
    goal: str
    status: str                  # "done" | "failed" | "waiting_approval"

    # Narrative
    summary: str                 # LLM-written prose

    # Steps
    total_steps: int
    history: list[dict] = Field(default_factory=list)

    # Verification
    verification_passed: Optional[bool] = None
    verification_reason: str = ""
    rollback_performed: bool = False
    rollback_reason: str = ""

    # HITL
    approvals: list[ApprovalItem] = Field(default_factory=list)

    # Failures & recovery
    failures: list[FailureItem] = Field(default_factory=list)
    recoveries: list[RecoveryItem] = Field(default_factory=list)

    # Evidence
    evidence: list[EvidenceItem] = Field(default_factory=list)

    # World model snapshot (final knowledge)
    world_model: dict = Field(default_factory=dict)

    # Cost / metrics (best effort)
    metrics: dict = Field(default_factory=dict)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()