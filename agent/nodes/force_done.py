# agent/nodes/force_done.py
from agent.state import AgentState


def force_done_node(state: AgentState) -> dict:
    return {"status": "failed", "next_action": {"tool": "DONE", "args": {}, "reason": "forced by guard"}}