from agent.memory.world_model import WorldModel
from agent.tools.registry import TOOLS
from agent.state import AgentState


# Tools that write to the world and need verification
WRITE_TOOLS = {
    "api_create_invoice",
    "browser_click",   # only when it's a submit action
}


def _is_write_action(tool: str, args: dict) -> bool:
    if tool == "api_create_invoice":
        return True
    if tool == "browser_click":
        # Only verify if the selector looks like a submit
        sel = (args.get("selector") or "").lower()
        return "submit" in sel
    return False


def _verify_api_create_invoice(args: dict, wm: WorldModel) -> dict:
    """
    Read back the created invoice from the API and compare
    against what we intended to write.
    """
    invoice_id = args.get("invoice_id")
    if not invoice_id:
        return {"passed": False, "reason": "no invoice_id in action args"}

    result = TOOLS["api_get_invoice"](invoice_id=invoice_id)
    if not result.get("success"):
        return {
            "passed": False,
            "reason": f"could not read back invoice {invoice_id}: {result.get('error')}",
        }

    actual = result["result"]
    expected = {
        "id": invoice_id,
        "vendor_id": args.get("vendor_id"),
        "amount": float(args.get("amount", 0)),
        "due_date": args.get("due_date") or None,
        "po_number": args.get("po_number") or None,
    }

    mismatches = []
    for key, expected_val in expected.items():
        actual_val = actual.get(key)
        # Normalize numbers
        if key == "amount" and actual_val is not None:
            try:
                actual_val = float(actual_val)
            except Exception:
                pass
        if actual_val != expected_val:
            mismatches.append(f"{key}: expected={expected_val!r} actual={actual_val!r}")

    if mismatches:
        return {
            "passed": False,
            "expected": expected,
            "actual": actual,
            "reason": "; ".join(mismatches),
            "evidence": {"api_response": actual},
        }

    return {
        "passed": True,
        "expected": expected,
        "actual": actual,
        "reason": "invoice matches intent",
        "evidence": {"api_response": actual},
    }


def _verify_browser_submit(state: AgentState) -> dict:
    """
    For browser submit clicks, check the page for a success message.
    This is a heuristic — the mock ERP shows 'SUCCESS: ...' or 'ERROR: ...'.
    """
    page = None
    try:
        from agent.tools.browser_session import BrowserSession
        page = BrowserSession.get().page()
    except Exception:
        return {"passed": False, "reason": "browser session not available"}

    try:
        # Look for a visible success or error message on the page
        body_text = page.inner_text("body")
    except Exception as e:
        return {"passed": False, "reason": f"could not read page: {e}"}

    body_lower = body_text.lower()

    if "success" in body_lower:
        # Extract the success line for evidence
        line = next((l for l in body_text.splitlines() if "success" in l.lower()), "")
        return {
            "passed": True,
            "reason": "page shows success message",
            "evidence": {"page_message": line.strip()},
        }

    if "error" in body_lower:
        line = next((l for l in body_text.splitlines() if "error" in l.lower()), "")
        return {
            "passed": False,
            "reason": f"page shows error: {line.strip()}",
            "evidence": {"page_message": line.strip()},
        }

    return {
        "passed": False,
        "reason": "no success or error message found on page",
    }


def verifier_node(state: AgentState) -> dict:
    action = state.get("next_action") or {}
    tool = action.get("tool", "")
    args = action.get("args", {})

    # Skip verification for non-write actions
    if not _is_write_action(tool, args):
        return {}   # no state change

    wm = WorldModel(**state.get("world_model", {}))

    if tool == "api_create_invoice":
        result = _verify_api_create_invoice(args, wm)
    elif tool == "browser_click":
        result = _verify_browser_submit(state)
    else:
        return {}

    # Add evidence
    evidence = list(state.get("evidence", []))
    if "evidence" in result:
        evidence.append({
            "step": state.get("step_count", 0),
            "tool": tool,
            "type": "verification",
            **result["evidence"],
        })

    verification = {
        "passed": result.get("passed", False),
        "expected": result.get("expected"),
        "actual": result.get("actual"),
        "reason": result.get("reason", ""),
    }

    return {
        "verification": verification,
        "evidence": evidence,
    }