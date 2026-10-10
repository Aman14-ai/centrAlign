from agent.memory.world_model import WorldModel
from agent.state import AgentState


# Tools that are irreversible / dangerous
IRREVERSIBLE_TOOLS = {
    "api_create_invoice",
    "api_delete",
    "browser_click",   # only when it's a submit
}

# Amount above which we require approval (in rupees)
HIGH_VALUE_THRESHOLD = 100_000


def _is_submit_click(action: dict) -> bool:
    if action.get("tool") != "browser_click":
        return False
    sel = (action.get("args", {}).get("selector") or "").lower()
    return "submit" in sel


def compute_risk(state: AgentState) -> float:
    """
    Returns a risk score 0.0 – 1.0.
    Higher = more likely to interrupt for approval.
    """
    action = state.get("next_action") or {}
    tool = action.get("tool", "")
    args = action.get("args", {})

    wm = WorldModel(**state.get("world_model", {}))

    risk = 0.0

    # 1. Irreversible action
    if tool in IRREVERSIBLE_TOOLS or _is_submit_click(action):
        risk += 0.4

    # 2. High amount
    amount = 0.0
    try:
        amount = float(args.get("amount", 0) or 0)
    except (TypeError, ValueError):
        amount = 0.0

    if amount >= HIGH_VALUE_THRESHOLD:
        risk += 0.4
    elif amount >= HIGH_VALUE_THRESHOLD / 2:
        risk += 0.15

    # 3. Prior failures in this run
    if state.get("failures"):
        risk += 0.1

    # 4. Open uncertainties
    if wm.uncertainties:
        risk += 0.1

    return min(risk, 1.0)


def should_interrupt(state: AgentState) -> bool:
    """Decide whether to ask for approval before the next action."""
    return compute_risk(state) >= 0.7