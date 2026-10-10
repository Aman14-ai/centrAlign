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