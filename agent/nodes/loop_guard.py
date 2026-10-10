from agent.state import AgentState


def detect_loop(state: AgentState) -> str | None:
    """
    Return a reason string if a loop is detected, else None.
    """
    history = state.get("history", [])
    if len(history) < 4:
        return None

    # Same action repeated twice in a row (failures don't count as progress)
    last = history[-1]
    prev = history[-2]
    if (
        last["action"] == prev["action"]
        and not last["observation_success"]
        and not prev["observation_success"]
    ):
        return "same action failed twice in a row"

    # Same tool failed 3 times within the last 5 steps
    recent = history[-5:]
    failed_tools = [
        h["action"].get("tool")
        for h in recent
        if not h["observation_success"]
    ]
    from collections import Counter
    if any(count >= 3 for count in Counter(failed_tools).values()):
        return "same tool failed 3+ times recently"

    # Too many total failures
    if len(state.get("failures", [])) >= 6:
        return "too many failures overall"

    return None