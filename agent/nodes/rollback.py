from agent.state import AgentState
from agent.tools.registry import TOOLS
from agent.tools.api import api_delete


def rollback_node(state:AgentState):
    verification=state.get("verification") or {}
    if verification.get("passed"):
        return {} # nothing to roll back

    action = state.get("next_action") or {}
    tool = action.get("tool", "")
    args = action.get("args", {})

    performed=False
    reason=""

    if tool == "api_create_invoice":
        invoice_id = args.get("invoice_id")
        if invoice_id:
            res = TOOLS["api_post"](
                endpoint=f"/api/invoices/{invoice_id}",
                data={},
            )
            
            res = api_delete(f"/api/invoices/{invoice_id}")
            performed = res.get("success", False)
            reason = f"deleted invoice {invoice_id}" if performed else res.get("error", "")

    elif tool == "browser_click":
        # Reset the form by navigating away and back
        res = TOOLS["browser_open"](url="/app/erp", page_name="erp")
        performed = res.get("success", False)
        reason = "reset ERP form" if performed else res.get("error", "")

    # Record the rollback
    rollback = {
        "performed": performed,
        "action": tool,
        "reason": reason,
        "original_failure": verification.get("reason", ""),
    }

    # Add evidence
    evidence = list(state.get("evidence", []))
    evidence.append({
        "step": state.get("step_count", 0),
        "type": "rollback",
        "performed": performed,
        "reason": reason,
    })

    return {
        "rollback": rollback,
        "evidence": evidence,
        "status": "failed",   # rollback means the run is a failure
    }