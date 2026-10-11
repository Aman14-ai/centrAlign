from agent.state import AgentState
from agent.tools.registry import TOOLS
from agent.policies.guard import is_blocked_action, record_failed_action


def executor_node(state: AgentState) -> dict:
    action = state.get("next_action") or {}
    tool_name = action.get("tool")
    args = action.get("args", {})

    # DONE handling (unchanged)
    if tool_name == "DONE":
        print("[EXECUTOR] DONE")
        return {"last_observation": {"success": True, "result": {"done": True}, "error": None}}

    # ---- GUARD: block previously failed actions ----
    if is_blocked_action(state, tool_name, args):
        print(f"[EXECUTOR] blocked action: {tool_name} already failed with these args")
        return {
            "last_observation": {
                "success": False,
                "result": {},
                "error": f"blocked_action: {tool_name} already failed with these args",
            },
            "failed_actions": state.get("failed_actions", []),
        }

    # Unknown tool (unchanged)
    if tool_name not in TOOLS:
        return {"last_observation": {"success": False, "result": {}, "error": f"Unknown tool: {tool_name}"}}

    # ---- Run the tool ----
    try:
        result = TOOLS[tool_name](**args)
        print("\n[EXECUTOR RESULT]\n", result, "\n")
    except TypeError as e:
        result = {"success": False, "result": {}, "error": f"Bad arguments: {e}"}
        print("\n[EXECUTOR ERROR]\n", result, "\n")
    except Exception as e:
        print("\n[EXECUTOR ERROR]\n", result, "\n")
        result = {"success": False, "result": {}, "error": f"Tool crashed: {e}"}

    # ---- GUARD: record failure ----
    if not result.get("success"):
        failed = record_failed_action(state, tool_name, args)
        print(f"[EXECUTOR] failed action: {tool_name} with these args")
        return {"last_observation": result, "failed_actions": failed}

    return {"last_observation": result}