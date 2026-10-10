from agent.state import AgentState
from agent.policies.risk import compute_risk
from langgraph.types import interrupt
from datetime import datetime, timezone


def human_approval_node(state:AgentState):
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

    decision=interrupt(payload)


    approvals = list(state.get("approvals", []))
    approvals.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": payload["question"],
        "action": payload["action"],
        "risk_score": risk,
        "decision": decision,
    })

    # if rejected stop the graph cleanly
    if isinstance(decision, dict) and decision.get("choice") == "reject":
        return {
            "approvals": approvals,
            "status": "failed",
            "pending_question": None,
        }

    # Approved: continue with the same next_action
    return {
        "approvals": approvals,
        "pending_question": None,
        "status": "running",
    }