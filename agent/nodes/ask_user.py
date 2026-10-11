from datetime import datetime, timezone

from langgraph.types import interrupt

from agent.state import AgentState
from agent.policies.guard import is_repeated_question, record_question
from agent.memory.world_model import WorldModel


# Any of these means "stop, don't proceed"
CANCEL_TOKENS = {
    "no", "n", "cancel", "stop", "abort", "quit", "exit",
    "don't", "dont", "not", "nah", "nope", "never mind", "nevermind",
    "reject", "deny", "refuse",
}


def _is_cancel(answer) -> bool:
    """Check whether the user's answer means stop."""
    if isinstance(answer, dict):
        choice = answer.get("choice", "")
    else:
        choice = str(answer or "")
    return choice.strip().lower() in CANCEL_TOKENS


def ask_user_node(state: AgentState) -> dict:
    pending = state.get("pending_question") or {}
    question = pending.get("question", "I need clarification to proceed.")

    # Guard against repeating the same question.
    if is_repeated_question(state, question):
        wm = WorldModel(**(state.get("world_model") or {}))
        wm.add_fact("Terminated: same question asked again without progress")
        return {
            "world_model": wm.model_dump(),
            "pending_question": None,
            "status": "failed",
        }

    payload = {
        "question": question,
        "options": pending.get("options", []),
        "context": pending.get("context", ""),
    }

    # --- PAUSE ---
    answer = interrupt(payload)
    # --- RESUME ---

    asked = record_question(state, question)
    approvals = list(state.get("approvals") or [])
    wm = WorldModel(**(state.get("world_model") or {}))

    # Extract the human-readable choice
    if isinstance(answer, dict):
        choice = answer.get("choice")
        resolved_answer = choice if choice is not None else answer
    else:
        resolved_answer = answer

    approvals.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "answer": resolved_answer,
        "type": "clarification",
        "cancelled": _is_cancel(answer),
    })

    # --- CANCEL PATH: user said stop ---
    if _is_cancel(answer):
        wm.add_fact(f"User cancelled: {resolved_answer}")
        return {
            "approvals": approvals,
            "asked_questions": asked,
            "world_model": wm.model_dump(),
            "pending_question": None,
            "next_action": {
                "tool": "DONE",
                "args": {},
                "reason": "user cancelled",
            },
            "status": "failed",
        }

    # --- NORMAL PATH: use the answer ---
    if resolved_answer is not None:
        wm.add_fact(f"User answered '{question}': {resolved_answer}")

    return {
        "approvals": approvals,
        "asked_questions": asked,
        "pending_answer": {
            "question": question,
            "answer": resolved_answer,
        },
        "world_model": wm.model_dump(),
        "pending_question": None,
        "status": "running",
    }