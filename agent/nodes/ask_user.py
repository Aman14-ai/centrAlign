from datetime import datetime, timezone
from langgraph.types import interrupt
from agent.memory.entities import Vendor
from agent.tools.registry import TOOLS
from agent.state import AgentState
from agent.policies.guard import is_repeated_question, record_question
from agent.memory.world_model import WorldModel



def ask_user_node(state:AgentState):
    question = (state.get("pending_question") or {}).get(
        "question",
        "I need clarification to proceed.",
    )

    question = (state.get("pending_question") or {}).get("question", "Clarification needed?")

    # ---- GUARD: if we've already asked this, force stop ----
    if is_repeated_question(state, question):
        wm = WorldModel(**state.get("world_model", {}))
        wm.add_fact("Terminated: same question asked again without progress")
        return {
            "world_model": wm.model_dump(),
            "pending_question": None,
            "status": "failed",
        }

    options = (state.get("pending_question") or {}).get("options", [])

    payload = {
        "question": question,
        "options": options,
        "context": state.get("pending_question", {}).get("context", ""),
    }

    answer = interrupt(payload)
    asked = record_question(state, question)

    approvals = list(state.get("approvals", []))
    approvals.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "answer": answer,
        "type": "clarification",
    })

    
    wm = WorldModel(**state.get("world_model", {}))
    if isinstance(answer, dict):
        choice = answer.get("choice")
        wm.add_fact(f"User chose: {choice}")
        # Store as pending_answer so the planner knows to USE it
        pending_answer = {"question": question, "answer": choice}

    return {
        "approvals": approvals,
        "asked_questions": asked,
        "pending_answer": pending_answer,
        "world_model": wm.model_dump(),
        "pending_question": None,
        "status": "running",
    }