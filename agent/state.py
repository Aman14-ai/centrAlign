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

    # identity and input
    task: str
    goal: str
    thread_id: str
    max_steps: int

    # Current step (short term memory)
    next_action: Action | None
    last_observation: Observation | None
    step_count: int

    # long term memory its like knowledge accumulator
    world_model: dict
    history: list[dict]
    evidence:list[dict]

    # reliability the guard system
    failures: list[dict]     # classified failure records
    recoveries: list[dict]   # what we tried to recover
    failed_actions: list[str]        # signatures of (tool, args) that failed
    asked_questions: list[str]       # signatures of questions already asked
    pending_answer: dict | None      # most recent user answer, unprocessed
    
    # verification and rollbacks
    verification:dict|None  # {passed, expected, actual, evidence, reason}
    rollback:dict|None

    # Loop counters and status
    recovery_attempts: int

    # HITL (Phase 7 uses these; harmless empty lists for now)
    approvals: list[dict]        # {question, decision, timestamp, node}
    pending_question: dict | None  # set when we interrupt
    risk_score: float            # 0.0 – 1.0, set by risk assessor

    # Output
    summary: str
    final_report: dict | None
    status: Literal["running", "done", "failed", "waiting_approval"]