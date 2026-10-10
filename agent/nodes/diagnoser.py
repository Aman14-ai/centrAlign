import json
from agent.llm import llm
from agent.memory.failures import (
    FailureType, classify_from_error_string, make_signature,
)
from agent.state import AgentState


DIAGNOSER_PROMPT = """
An agent's action failed. Classify the failure.

Action:
  tool: {tool}
  args: {args}

Error:
  {error}

Choose the single best category from:
  selector_not_found, api_500, timeout, missing_field,
  duplicate_record, permission_denied, ambiguous_data,
  file_not_found, validation_error, unknown

Also produce a short "context_key" — the most relevant string
for distinguishing this failure from others. Examples:
  - for selector failures: the page name + selector
  - for api failures: the endpoint
  - for file failures: the file path

Return ONLY JSON:
{{"type": "<category>", "context_key": "<string>", "details": "<short>"}}
"""


def _fallback_diagnose(action: dict, error: str) -> dict:
    ftype = classify_from_error_string(error)
    tool = action.get("tool", "unknown")
    args = action.get("args", {})

    # Guess context_key based on tool
    context_key = ""
    if tool == "browser_click" or tool == "browser_fill":
        page = args.get("page_name", "")
        sel = args.get("selector", "")
        context_key = f"{page}::{sel}" if page else sel
    elif tool in ("api_get", "api_post"):
        context_key = args.get("endpoint", "")
    elif tool in ("api_get_invoice", "api_get_vendor", "api_get_po"):
        context_key = str(list(args.values())[0]) if args else ""
    elif tool == "read_file":
        context_key = args.get("path", "")

    return {
        "type": ftype.value,
        "context_key": context_key,
        "details": error[:200],
    }


def diagnoser_node(state: AgentState) -> dict:
    obs = state.get("last_observation") or {}
    action = state.get("next_action") or {}
    error = obs.get("error") or ""

    # Fast path: deterministic classification
    ftype = classify_from_error_string(error)
    if ftype != FailureType.UNKNOWN:
        diagnosis = _fallback_diagnose(action, error)
    else:
        # Slow path: ask the LLM
        prompt = DIAGNOSER_PROMPT.format(
            tool=action.get("tool"),
            args=action.get("args"),
            error=error[:500],
        )
        try:
            raw = llm.invoke(prompt).content.strip()
            if raw.startswith("```"):
                raw = raw.strip("`").replace("json\n", "", 1)
            diagnosis = json.loads(raw)
        except Exception:
            diagnosis = _fallback_diagnose(action, error)

    # Build a stable signature
    ftype_enum = FailureType(diagnosis.get("type", "unknown"))
    signature = make_signature(
        ftype_enum,
        action.get("tool", "unknown"),
        diagnosis.get("context_key", ""),
    )

    # Attach to the last failure record
    failures = list(state.get("failures", []))
    failures.append({
        "action": action,
        "error": error,
        "type": ftype_enum.value,
        "context_key": diagnosis.get("context_key", ""),
        "details": diagnosis.get("details", ""),
        "signature": signature,
    })

    print("\n[DIAGNOSER]")
    print(f"  error: {error[:120]}")
    print(f"  type: {ftype_enum.value}")
    print(f"  context_key: {diagnosis.get('context_key', '')}")
    print(f"  signature: {signature}")

    return {"failures": failures}