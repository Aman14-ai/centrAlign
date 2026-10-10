from typing import TypedDict, Literal


class Action(TypedDict):
    tool: str
    args: dict
    reason: str


class Observation(TypedDict):
    success: bool
    result: dict
    error: str | None


class AgentState(TypedDict):

    thread_id: str
    final_report: dict | None
    # User input
    task: str
    goal: str

    # Loop control
    next_action: Action | None
    last_observation: Observation | None
    history: list[dict]

    # World model (serialized via WorldModel.model_dump())
    world_model: dict

    # failures and recoveries
    failures: list[dict]     # classified failure records
    recoveries: list[dict]   # what we tried to recover

    # verification
    verification:dict|None  # {passed, expected, actual, evidence, reason}
    rollback:dict|None
    evidence:list[dict]

    # Loop counters and status
    recovery_attempts: int
    step_count: int
    max_steps: int
    status: Literal["running", "done", "failed", "waiting_approval"]

    # HITL (Phase 7 uses these; harmless empty lists for now)
    approvals: list[dict]        # {question, decision, timestamp, node}
    pending_question: dict | None  # set when we interrupt
    risk_score: float            # 0.0 – 1.0, set by risk assessor

    # Reliability guard
    failed_actions: list[str]        # signatures of (tool, args) that failed
    asked_questions: list[str]       # signatures of questions already asked
    pending_answer: dict | None      # most recent user answer, unprocessed
    
    # Output
    summary: str