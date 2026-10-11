from agent.state import AgentState
from agent.nodes.loop_guard import detect_loop
from agent.nodes.verifier import _is_write_action
from agent.policies.risk import should_interrupt
from agent.policies.guard import should_terminate,is_repeated_question




def route_after_observer(state: AgentState) -> str:
    if state.get("status") in ("done", "failed"):
        return "summarize"

    


    # ---- General termination check ----
    terminate, reason = should_terminate(state)
    if terminate:
        print(f"[ROUTER] terminating: {reason}")
        return "summarize"

    obs = state.get("last_observation") or {}
    action = state.get("next_action") or {}
    tool = action.get("tool", "")

    if not obs.get("success"):
        error = obs.get("error") or ""
        if error.startswith("blocked_action") or error.startswith("redundant_action"):
            return "continue"   # let the planner try something else
        return "diagnose"

    if action.get("tool") == "DONE":
        return "summarize"

      # Write actions need verification
    if _is_write_action(tool, action.get("args", {})):
        return "verify"

    if state.get("step_count", 0) >= state.get("max_steps", 20):
        return "summarize"

    return "continue"

def route_before_executor(state: AgentState) -> str:

    if state.get("status") == "failed":
        return "force_done"
    action = state.get("next_action") or {}

    if action.get("tool") == "ASK_USER":
        # If we've asked too many questions or this one is repeated, force stop
        terminate, reason = should_terminate(state)
        question = action.get("args", {}).get("question", "")
        if terminate or is_repeated_question(state, question):
            print(f"[ROUTER] refusing another question: {reason or 'repeated'}")
            return "force_done"
        return "ask_user_trigger"

    if should_interrupt(state):
        return "approve"

    return "execute"

def route_after_verifier(state: AgentState) -> str:
    v = state.get("verification") or {}
    if v.get("passed"):
        return "summarize"
    return "rollback"


def route_after_approval(state: AgentState) -> str:
    if state.get("status") == "failed":
        return "summarize"
    return "execute"