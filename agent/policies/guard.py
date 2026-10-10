import hashlib
import json
from agent.state import AgentState


# Tools that can never be used as a recovery strategy
DESTRUCTIVE_TOOLS = {"api_delete", "browser_click"}  # browser_click only if it deletes


def is_destructive(tool_name: str) -> bool:
    return tool_name in DESTRUCTIVE_TOOLS

# ---------- Action tracking ----------

def action_signature(tool: str, args: dict) -> str:
    """Stable hash of (tool, args). Two identical actions have the same signature."""
    raw = json.dumps({"tool": tool, "args": args}, sort_keys=True, default=str)
    return f"{tool}::{hashlib.md5(raw.encode()).hexdigest()[:10]}"


def is_blocked_action(state: AgentState, tool: str, args: dict) -> bool:
    sig = action_signature(tool, args)
    return sig in state.get("failed_actions", [])


def record_failed_action(state: AgentState, tool: str, args: dict) -> list[str]:
    sig = action_signature(tool, args)
    blocked = list(state.get("failed_actions", []))
    if sig not in blocked:
        blocked.append(sig)
    return blocked


# ---------- Question tracking ----------

def question_signature(question: str) -> str:
    """Normalize: lowercase, strip whitespace, hash."""
    q = " ".join(question.lower().split())
    return hashlib.md5(q.encode()).hexdigest()[:10]


def is_repeated_question(state: AgentState, question: str) -> bool:
    sig = question_signature(question)
    return sig in state.get("asked_questions", [])


def record_question(state: AgentState, question: str) -> list[str]:
    sig = question_signature(question)
    asked = list(state.get("asked_questions", []))
    if sig not in asked:
        asked.append(sig)
    return asked


# ---------- Terminal conditions ----------

def should_terminate(state: AgentState) -> tuple[bool, str]:
    """
    Return (True, reason) if the agent should stop trying.
    General conditions — not tied to any specific tool.
    """
    # Too many failed attempts
    if len(state.get("failed_actions", [])) >= 5:
        return True, "too many failed actions"

    # Too many questions asked
    if len(state.get("asked_questions", [])) >= 3:
        return True, "too many clarification requests"

    # Step limit
    if state.get("step_count", 0) >= state.get("max_steps", 20):
        return True, "max steps reached"

    # Repeated identical action in last 5 steps
    history = state.get("history", [])
    if len(history) >= 5:
        recent = history[-5:]
        recent_sigs = [
            action_signature(h["action"].get("tool", ""), h["action"].get("args", {}))
            for h in recent
        ]
        if len(set(recent_sigs)) <= 2:
            return True, "action loop detected"

    return False, ""