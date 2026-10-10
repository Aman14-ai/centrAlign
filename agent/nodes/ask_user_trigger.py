# agent/nodes/ask_user_trigger.py
from agent.state import AgentState


def ask_user_trigger_node(state: AgentState) -> dict:
    action = state.get("next_action") or {}
    args = action.get("args", {})
    return {
        "pending_question": {
            "question": args.get("question", "I need clarification."),
            "options": args.get("options", []),
            "context": action.get("reason", ""),
        },
    }