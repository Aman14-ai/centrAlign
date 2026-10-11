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











# import json
# import re

# from agent.llm import llm
# from agent.memory.failures import (
#     FailureType,
#     classify_from_error_string,
#     make_signature,
# )
# from agent.state import AgentState


# VALID_FAILURE_TYPES = {item.value for item in FailureType}

# DIAGNOSER_PROMPT = """
# You are diagnosing a failed action in an AI agent.

# Classify the failure using the evidence provided.
# Do not invent details that are not present in the error.

# Action:
#   tool: {tool}
#   args: {args}

# Error:
#   {error}

# Choose exactly one category from:
#   selector_not_found, api_500, timeout, missing_field,
#   duplicate_record, permission_denied, ambiguous_data,
#   file_not_found, validation_error, unknown

# Also provide:
# - context_key: the most relevant resource or input identifying
#   this failure. Include the selector for browser selector errors,
#   the endpoint for API errors, or the path for file errors.
# - details: a short explanation supported by the error.
# - recovery_hint: one short, relevant next-step suggestion.
#   Do not suggest an unrelated tool or repeat the failed action
#   unchanged.

# Return ONLY a JSON object:
# {{"type":"<category>",
#   "context_key":"<string>",
#   "details":"<short explanation>",
#   "recovery_hint":"<short suggestion>"}}
# """


# def _extract_json(raw: str) -> dict:
#     """Parse a JSON object, including one wrapped in Markdown fences."""
#     raw = raw.strip()

#     # Remove an optional Markdown code fence.
#     if raw.startswith("```"):
#         raw = re.sub(r"^```(?:json)?\s*", "", raw, count=1, flags=re.I)
#         raw = re.sub(r"\s*```$", "", raw, count=1)

#     try:
#         data = json.loads(raw)
#     except json.JSONDecodeError:
#         # Fallback: try to extract a JSON object from surrounding text.
#         match = re.search(r"\{.*\}", raw, flags=re.S)
#         if not match:
#             raise ValueError("No JSON object found in diagnoser response")
#         data = json.loads(match.group(0))

#     if not isinstance(data, dict):
#         raise ValueError("Diagnoser response must be a JSON object")

#     return data


# def _context_key(action: dict) -> str:
#     """Build a useful, deterministic context key from action arguments."""
#     tool = action.get("tool", "unknown")
#     args = action.get("args") or {}

#     if not isinstance(args, dict):
#         return str(args)[:200]

#     # Browser actions: distinguish selectors and pages.
#     if tool in {"browser_read", "browser_click", "browser_fill"}:
#         page = args.get("page_name") or args.get("url") or ""
#         selector = args.get("selector") or ""
#         return f"{page}::{selector}" if page else str(selector)

#     if tool == "browser_open":
#         return str(args.get("url", ""))

#     # API actions: identify the endpoint.
#     if tool in {"api_get", "api_post", "api_put", "api_delete"}:
#         return str(args.get("endpoint", ""))

#     # Entity-specific API tools.
#     if tool in {"api_get_invoice", "api_get_vendor", "api_get_po"}:
#         return str(args.get("id") or args.get("invoice_id")
#                    or args.get("vendor_id") or args.get("po_id")
#                    or next(iter(args.values()), ""))

#     # File actions.
#     if tool in {"read_file", "list_files"}:
#         return str(args.get("path") or args.get("directory", ""))

#     # Generic deterministic fallback.
#     return json.dumps(args, sort_keys=True, default=str)[:200]


# def _fallback_diagnose(action: dict, error: str) -> dict:
#     failure_type = classify_from_error_string(error)

#     return {
#         "type": failure_type.value,
#         "context_key": _context_key(action),
#         "details": error[:200],
#         "recovery_hint": (
#             "Inspect the error and available evidence before choosing "
#             "a different recovery action."
#         ),
#     }


# def _validate_diagnosis(diagnosis: dict, action: dict, error: str) -> dict:
#     """Validate and normalize model output; fall back on invalid data."""
#     if not isinstance(diagnosis, dict):
#         return _fallback_diagnose(action, error)

#     failure_type = diagnosis.get("type")
#     if failure_type not in VALID_FAILURE_TYPES:
#         return _fallback_diagnose(action, error)

#     # Never allow missing model fields to produce malformed records.
#     context_key = diagnosis.get("context_key")
#     details = diagnosis.get("details")
#     recovery_hint = diagnosis.get("recovery_hint")

#     return {
#         "type": failure_type,
#         "context_key": (
#             context_key.strip()[:200]
#             if isinstance(context_key, str) and context_key.strip()
#             else _context_key(action)
#         ),
#         "details": (
#             details.strip()[:300]
#             if isinstance(details, str) and details.strip()
#             else error[:200]
#         ),
#         "recovery_hint": (
#             recovery_hint.strip()[:300]
#             if isinstance(recovery_hint, str) and recovery_hint.strip()
#             else "Inspect available evidence before retrying."
#         ),
#     }


# def diagnoser_node(state: AgentState) -> dict:
#     observation = state.get("last_observation") or {}
#     action = state.get("next_action") or {}
#     error = str(observation.get("error") or "")

#     # Don't ask the LLM to diagnose an action with no reported error.
#     if not error:
#         error = "No error message was provided for the failed action."

#     # Fast path: use deterministic classification when possible.
#     failure_type = classify_from_error_string(error)

#     if failure_type != FailureType.UNKNOWN:
#         diagnosis = _fallback_diagnose(action, error)
#     else:
#         prompt = DIAGNOSER_PROMPT.format(
#             tool=action.get("tool", "unknown"),
#             args=json.dumps(action.get("args", {}), default=str),
#             error=error[:500],
#         )

#         try:
#             response = llm.invoke(prompt)
#             raw = getattr(response, "content", "")
#             diagnosis = _extract_json(raw) if isinstance(raw, str) else {}
#         except Exception as exc:
#             print(f"[DIAGNOSER] LLM diagnosis failed: {exc}")
#             diagnosis = _fallback_diagnose(action, error)

#     diagnosis = _validate_diagnosis(diagnosis, action, error)

#     # The validated category is guaranteed to be recognized.
#     failure_type = FailureType(diagnosis["type"])

#     signature = make_signature(
#         failure_type,
#         action.get("tool", "unknown"),
#         diagnosis["context_key"],
#     )

#     failures = list(state.get("failures", []))
#     failures.append({
#         "action": action,
#         "error": error,
#         "type": failure_type.value,
#         "context_key": diagnosis["context_key"],
#         "details": diagnosis["details"],
#         "recovery_hint": diagnosis["recovery_hint"],
#         "signature": signature,
#     })

#     print("\n[DIAGNOSER]")
#     print(f"  error: {error[:120]}")
#     print(f"  type: {failure_type.value}")
#     print(f"  context_key: {diagnosis['context_key']}")
#     print(f"  recovery_hint: {diagnosis['recovery_hint']}")
#     print(f"  signature: {signature}")

#     return {"failures": failures}
