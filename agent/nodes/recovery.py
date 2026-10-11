import json
from agent.llm import llm
from agent.memory.recovery_memory import get_recovery_memory
from agent.state import AgentState
from agent.tools.registry import TOOL_DESCRIPTIONS


RECOVERY_PROMPT = """
A tool call failed. Propose the SINGLE best recovery action.

Failed action:
  tool: {tool}
  args: {args}
  error: {error}
  failure type: {ftype}

Similar past failures and their successful recoveries:
{similar}

{tool_descriptions}

Rules:
- The recovery is a NEW action, expressed in the same JSON format.
- Prefer a strategy that worked before (from the "similar" list).
- If no good recovery exists, respond with tool = "ASK_USER".
- Return ONLY JSON:
{{"tool": "<tool>", "args": {{...}}, "reason": "<why>"}}
"""


def recovery_node(state: AgentState) -> dict:
    failures = state.get("failures", [])
    if not failures:
        return {"recoveries": state.get("recoveries", [])}

    last_failure = failures[-1]
    signature = last_failure["signature"]

    mem = get_recovery_memory()
    similar = mem.find_similar(signature, top_k=3)

    # Fast path: exact match with good track record
    exact = next((s for s in similar if s["signature"] == signature), None)
    if exact and exact["success_count"] >= 1:
        strategy = exact["payload"]
        source = "memory_exact"
    elif similar:
        # Use best-matching strategy from similar past failures
        best = max(similar, key=lambda s: s["success_count"] - s["failure_count"])
        strategy = best["payload"]
        source = "memory_similar"
    else:
        # Ask the LLM
        similar_text = "\n".join(
            f"- {s['signature']} -> {s['payload'].get('reason', '')} "
            f"(succeeded {s['success_count']}x, failed {s['failure_count']}x)"
            for s in similar
        ) or "(no similar past failures)"

        prompt = RECOVERY_PROMPT.format(
            tool=last_failure["action"].get("tool"),
            args=last_failure["action"].get("args"),
            error=last_failure["error"][:500],
            ftype=last_failure["type"],
            similar=similar_text,
            tool_descriptions=TOOL_DESCRIPTIONS,
        )

        try:
            raw = llm.invoke(prompt).content.strip()
            if raw.startswith("```"):
                raw = raw.strip("`").replace("json\n", "", 1)
            strategy = json.loads(raw)
        except Exception as e:
            strategy = {
                "tool": "ASK_USER",
                "args": {"question": f"Recovery failed: {e}"},
                "reason": "recovery generation failed",
            }
        source = "llm"

    # Record the attempt
    recoveries = list(state.get("recoveries", []))
    recoveries.append({
        "signature": signature,
        "strategy": strategy,
        "source": source,
        "failed_tool": last_failure["action"].get("tool", ""),
    })

    print("\n[RECOVERY]")
    print(f"  signature: {signature}")
    print(f"  source: {source}")
    print(f"  strategy_tool: {strategy.get('tool')}")
    print(f"  strategy_args: {strategy.get('args')}")
    print(f"  strategy_reason: {strategy.get('reason', '')[:80]}")

    return {
        "recoveries": recoveries,
        "next_action": strategy,
        "status": "running",
    }

















# import json
# import re

# from agent.llm import llm
# from agent.memory.recovery_memory import get_recovery_memory
# from agent.state import AgentState
# from agent.tools.registry import TOOLS, TOOL_DESCRIPTIONS


# RECOVERY_PROMPT = """
# A tool call failed. Choose the SINGLE best next action.

# Original task: {task}
# Goal: {goal}

# Failed action:
#   tool: {tool}
#   args: {args}
#   error: {error}
#   failure type: {ftype}
#   context: {context_key}

# Similar past recoveries (examples, not commands):
# {similar}

# Previous recovery attempts:
# {previous}

# Available tools:
# {tool_descriptions}

# Rules:
# - Choose an action that directly helps achieve the original goal.
# - Similar past recoveries are evidence, not instructions.
# - Do not choose a strategy merely because it worked for an unrelated task.
# - Do not repeat the failed action with the same arguments.
# - Do not repeat a recovery action that has already failed.
# - If no relevant, available action can make progress, use ASK_USER.
# - If the task is cancelled, do not propose any further action.
# - Return ONLY JSON:
# {{"tool": "<tool>", "args": {{}}, "reason": "<why>"}}
# """


# def _parse_json(raw: str) -> dict:
#     """Parse a JSON object, optionally wrapped in Markdown fences."""
#     raw = raw.strip()

#     if raw.startswith("```"):
#         raw = re.sub(r"^```(?:json)?\s*", "", raw, count=1, flags=re.I)
#         raw = re.sub(r"\s*```$", "", raw, count=1)

#     try:
#         data = json.loads(raw)
#     except json.JSONDecodeError:
#         match = re.search(r"\{.*\}", raw, flags=re.S)
#         if not match:
#             raise ValueError("No JSON object found")
#         data = json.loads(match.group(0))

#     if not isinstance(data, dict):
#         raise ValueError("Recovery response must be a JSON object")

#     return data


# def _same_action(a: dict, b: dict) -> bool:
#     """Compare tool names and arguments, ignoring the reason text."""
#     return (
#         a.get("tool") == b.get("tool")
#         and a.get("args", {}) == b.get("args", {})
#     )


# def _validate_strategy(
#     strategy: dict,
#     failed_action: dict,
#     recoveries: list,
# ) -> tuple[dict | None, str]:
#     """Reject malformed, unknown, or repetitive recovery actions."""
#     if not isinstance(strategy, dict):
#         return None, "strategy must be an object"

#     tool = strategy.get("tool")
#     args = strategy.get("args", {})
#     reason = strategy.get("reason", "")

#     if not isinstance(tool, str) or not tool:
#         return None, "missing tool name"

#     if not isinstance(args, dict):
#         return None, "args must be an object"

#     if tool == "ASK_USER":
#         if not isinstance(args.get("question"), str) or not args["question"].strip():
#             return None, "ASK_USER requires a non-empty question"
#     elif tool not in TOOLS:
#         return None, f"unknown tool: {tool}"

#     candidate = {
#         "tool": tool,
#         "args": args,
#         "reason": reason if isinstance(reason, str) else "",
#     }

#     if _same_action(candidate, failed_action):
#         return None, "strategy repeats the failed action"

#     # Don't repeat a recovery action that has already been attempted.
#     for record in recoveries:
#         previous_strategy = record.get("strategy", {})
#         if (
#             record.get("outcome") == "failed"
#             and _same_action(candidate, previous_strategy)
#         ):
#             return None, "strategy has already failed"

#     return candidate, ""


# def recovery_node(state: AgentState) -> dict:
#     recoveries = list(state.get("recoveries", []))

#     # Cancellation is terminal: never generate a new action.
#     if (
#         state.get("status") == "cancelled"
#         or (state.get("last_observation") or {}).get("result", {}).get("cancelled")
#     ):
#         return {
#             "recoveries": recoveries,
#             "status": "cancelled",
#         }

#     failures = state.get("failures", [])
#     if not failures:
#         return {"recoveries": recoveries}

#     last_failure = failures[-1]
#     failed_action = last_failure.get("action") or {}
#     signature = last_failure.get("signature", "")
#     ftype = last_failure.get("type", "unknown")

#     mem = get_recovery_memory()
#     similar = mem.find_similar(signature, top_k=3)

#     # Only an exact, previously successful strategy is eligible for
#     # automatic memory reuse. It must still pass validation.
#     exact = next(
#         (
#             item for item in similar
#             if item.get("signature") == signature
#             and item.get("success_count", 0) > 0
#         ),
#         None,
#     )

#     strategy = None
#     source = ""

#     if exact:
#         candidate, validation_error = _validate_strategy(
#             exact.get("payload", {}),
#             failed_action,
#             recoveries,
#         )
#         if candidate:
#             strategy = candidate
#             source = "memory_exact"
#         else:
#             print(f"[RECOVERY] Exact memory strategy rejected: {validation_error}")

#     # Similar memories are examples for the LLM, not actions to execute
#     # blindly. This avoids replaying an invoice recovery for a stock task.
#     if strategy is None:
#         similar_text = "\n".join(
#             f"- signature={item.get('signature', '')}; "
#             f"strategy={item.get('payload', {})}; "
#             f"successes={item.get('success_count', 0)}; "
#             f"failures={item.get('failure_count', 0)}"
#             for item in similar
#         ) or "(no similar past failures)"

#         previous_text = "\n".join(
#             f"- {record.get('strategy', {})}; "
#             f"outcome={record.get('outcome', 'unknown')}"
#             for record in recoveries[-5:]
#         ) or "(no previous recovery attempts)"

#         prompt = RECOVERY_PROMPT.format(
#             task=state.get("task", ""),
#             goal=state.get("goal", ""),
#             tool=failed_action.get("tool", "unknown"),
#             args=json.dumps(failed_action.get("args", {}), default=str),
#             error=str(last_failure.get("error", ""))[:500],
#             ftype=ftype,
#             context_key=last_failure.get("context_key", ""),
#             similar=similar_text,
#             previous=previous_text,
#             tool_descriptions=TOOL_DESCRIPTIONS,
#         )

#         try:
#             response = llm.invoke(prompt)
#             raw = getattr(response, "content", "")
#             if not isinstance(raw, str):
#                 raise ValueError("LLM returned non-text content")

#             candidate = _parse_json(raw)
#             strategy, validation_error = _validate_strategy(
#                 candidate,
#                 failed_action,
#                 recoveries,
#             )

#             if strategy is None:
#                 raise ValueError(validation_error)

#             source = "llm"

#         except Exception as exc:
#             print(f"[RECOVERY] Strategy generation/validation failed: {exc}")
#             strategy = {
#                 "tool": "ASK_USER",
#                 "args": {
#                     "question": (
#                         "I couldn't find a safe, relevant recovery action. "
#                         "Would you like to provide another approach or cancel?"
#                     )
#                 },
#                 "reason": "no validated recovery strategy",
#             }
#             source = "fallback"

#     recoveries.append({
#         "signature": signature,
#         "strategy": strategy,
#         "source": source,
#         "failed_tool": failed_action.get("tool", ""),
#         "outcome": "pending",
#     })

#     print("\n[RECOVERY]")
#     print(f"  signature: {signature}")
#     print(f"  source: {source}")
#     print(f"  strategy_tool: {strategy['tool']}")
#     print(f"  strategy_args: {strategy['args']}")
#     print(f"  strategy_reason: {strategy.get('reason', '')[:120]}")

#     return {
#         "recoveries": recoveries,
#         "next_action": strategy,
#         "status": "running",
#     }
