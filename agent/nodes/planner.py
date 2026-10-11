import json
import re
from agent.llm import llm
from agent.memory.world_model import WorldModel
from agent.state import AgentState
from agent.tools.registry import TOOL_DESCRIPTIONS


PLANNER_PROMPT = """
You are the planner of an autonomous AI worker.

Goal:
{goal}

What you already know:
{world_model_text}

Last observation:
{last_observation}

Recent history:
{history}

{tool_descriptions}

Decide the SINGLE NEXT action to move toward the goal.

Rules:
- If its normal chat acts like normal chatbots.
- Choose exactly one tool and its arguments.
- Do NOT call functions. Just return a JSON object with fields: tool, args, reason.
- If the goal is achieved, respond with: {{"tool": "DONE", "args": {{}}, "reason": "goal achieved"}}
- Do NOT repeat an action that already succeeded.
- Return ONLY valid JSON. No prose, no markdown, no function-call syntax.
- AMBIGUITY: If the goal requires selecting ONE entity, but multiple
  equally valid entities match, respond with:
  {{"tool": "ASK_USER", "args": {{"question": "...", "options": [...]}}, "reason": "ambiguous"}}
  Example: "Find the Acme vendor's email" → two Acme vendors exist → ASK_USER.
  Only ask when the task truly requires a single answer.

Correct output:
{{"tool": "read_file", "args": {{"path": "invoices/acme_inv_001.txt"}}, "reason": "read the invoice"}}

WRONG output (do not do this):
{{"name": "read_file", "arguments": {{"path": "..."}}}}
"""


def _extract_json_from_response(raw: str) -> dict | None:
    """Try hard to extract a usable action from the LLM output."""
    # Strip markdown fences
    if raw.startswith("```"):
        raw = raw.strip("`").replace("json\n", "", 1)

    # Try direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try to find a JSON object anywhere in the string
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def _normalize_action(parsed: dict) -> dict:
    """Normalize alternative key names the LLM might use."""
    # Handle native-style: {"name": ..., "arguments": ...}
    if "name" in parsed and "arguments" in parsed:
        return {
            "tool": parsed["name"].split(".")[-1],   # strip any namespace
            "args": parsed.get("arguments", {}),
            "reason": "normalized from native format",
        }
    # Standard format
    if "tool" in parsed:
        return {
            "tool": parsed.get("tool", "DONE"),
            "args": parsed.get("args", {}),
            "reason": parsed.get("reason", ""),
        }
    # Unknown format
    return {"tool": "DONE", "args": {}, "reason": "unrecognized planner output"}


def planner_node(state: AgentState) -> dict:
    wm = WorldModel(**state.get("world_model", {}))
    wm_text = wm.to_prompt_text()

    prompt = PLANNER_PROMPT.format(
        goal=state["goal"],
        world_model_text=wm_text,
        last_observation=state.get("last_observation"),
        history=state.get("history", [])[-5:],
        tool_descriptions=TOOL_DESCRIPTIONS,
    )

    # ---- Safely invoke the LLM ----
    try:
        response = llm.invoke(prompt)
        raw = response.content.strip()
        print(f"\n[PLANNER RAW]\n{raw}\n")

    except Exception as e:
        # Check if Groq returned a failed_generation we can salvage
        err_text = str(e)
        print(f"\n[PLANNER ERROR] {err_text[:200]}")

        # Groq error format: 'failed_generation': '{"name": ..., "arguments": ...}'
        match = re.search(r"'failed_generation':\s*'([^']+)'", err_text)
        if match:
            raw = match.group(1)
            print(f"\n[PLANNER SALVAGED]\n{raw}\n")
        else:
            # Can't recover — give up gracefully
            return {
                "next_action": {"tool": "DONE", "args": {}, "reason": "planner LLM error"},
                "status": "failed",
            }

    # ---- Parse and normalize ----
    parsed = _extract_json_from_response(raw)
    if not parsed:
        return {
            "next_action": {"tool": "DONE", "args": {}, "reason": "planner output unparseable"},
            "status": "failed",
        }

    action = _normalize_action(parsed)

    return {"next_action": action}