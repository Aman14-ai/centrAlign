from agent.state import AgentState
from agent.report import EvidenceItem


def collect_evidence(state: AgentState) -> list[EvidenceItem]:
    """
    Walk the state and produce a normalized list of evidence items.
    """
    items: list[EvidenceItem] = []

    # 1. Screenshots taken during the run
    for h in state.get("history", []):
        action = h.get("action", {})
        if action.get("tool") == "browser_screenshot":
            name = action.get("args", {}).get("name")
            if name:
                items.append(EvidenceItem(
                    step=h.get("step"),
                    type="screenshot",
                    description=f"screenshot: {name}.png",
                    data={"path": f"screenshots/{name}.png"},
                ))

    # 2. API responses captured by the verifier
    for e in state.get("evidence", []):
        if e.get("type") == "verification":
            items.append(EvidenceItem(
                step=e.get("step"),
                type="api_response",
                description=f"verified {e.get('tool')}",
                data=e.get("api_response", {}),
            ))
        elif e.get("type") == "rollback":
            items.append(EvidenceItem(
                step=e.get("step"),
                type="rollback",
                description=e.get("reason", "rollback performed"),
                data={"performed": e.get("performed")},
            ))

    # 3. Approval records
    for a in state.get("approvals", []):
        items.append(EvidenceItem(
            step=None,
            type="approval",
            description=a.get("question", "approval"),
            data={"decision": a.get("decision") or a.get("answer")},
        ))

    return items