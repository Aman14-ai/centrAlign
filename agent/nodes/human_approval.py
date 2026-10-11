from datetime import datetime, timezone

from langgraph.types import interrupt

from agent.state import AgentState
from agent.policies.risk import compute_risk


CANCEL_TOKENS = {
    "no", "n", "cancel", "stop", "abort", "quit", "exit",
    "don't", "dont", "not", "nah", "nope", "reject", "deny", "refuse",
}


def _is_reject(decision) -> bool:
    if isinstance(decision, dict):
        choice = (decision.get("choice") or "").strip().lower()
    else:
        choice = str(decision or "").strip().lower()
    return choice in CANCEL_TOKENS


def human_approval_node(state: AgentState) -> dict:
    action = state.get("next_action") or {}
    risk = compute_risk(state)

    payload = {
        "question": "Approve this action?",
        "action": {
            "tool": action.get("tool"),
            "args": action.get("args"),
            "reason": action.get("reason"),
        },
        "risk_score": risk,
        "evidence": state.get("evidence", [])[-3:],
        "options": ["approve", "reject"],
    }

    # --- PAUSE ---
    decision = interrupt(payload)
    # --- RESUME ---

    approvals = list(state.get("approvals", []))
    approvals.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": payload["question"],
        "action": payload["action"],
        "risk_score": risk,
        "decision": decision,
    })

    # --- REJECT / CANCEL ---
    if _is_reject(decision):
        return {
            "approvals": approvals,
            "next_action": {"tool": "DONE", "args": {}, "reason": "user rejected"},
            "pending_question": None,
            "status": "failed",
        }

    # --- APPROVED ---
    return {
        "approvals": approvals,
        "pending_question": None,
        "status": "running",
    }