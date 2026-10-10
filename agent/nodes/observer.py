from agent.memory.world_model import WorldModel
from agent.memory.entities import (
    Vendor, PurchaseOrder, Invoice, FileFacts,
)
from agent.memory.extractor import extract_fields
from agent.state import AgentState


# ---------------- Tool-specific handlers ----------------

def _handle_read_file(wm: WorldModel, result: dict) -> None:
    content = result.get("content", "")
    path = result.get("path", "")
    if not content or not path:
        return

    extracted = extract_fields(content)
    if not extracted:
        return

    facts = FileFacts(
        path=path,
        vendor=extracted.get("vendor"),
        invoice_number=extracted.get("invoice_number"),
        amount=extracted.get("amount"),
        due_date=extracted.get("due_date"),
        po_number=extracted.get("po_number"),
        source="extractor",
    )
    wm.add_file_facts(facts)

    for field in facts.missing_fields():
        wm.add_uncertainty(f"{path}: missing {field}")

    if facts.invoice_number:
        wm.add_fact(
            f"File {path} contains invoice {facts.invoice_number} "
            f"from {facts.vendor or 'unknown vendor'}"
        )


def _handle_vendor(wm: WorldModel, data: dict) -> None:
    aliases_raw = data.get("aliases") or ""
    aliases = [a.strip() for a in aliases_raw.split(",") if a.strip()]
    wm.add_vendor(Vendor(
        id=data["id"],
        name=data["name"],
        aliases=aliases,
        email=data.get("email"),
    ))


def _handle_po(wm: WorldModel, data: dict) -> None:
    wm.add_po(PurchaseOrder(
        po_number=data["po_number"],
        vendor_id=data["vendor_id"],
        amount=data["amount"],
        status=data.get("status", "open"),
    ))


def _handle_invoice(wm: WorldModel, data: dict) -> None:
    wm.add_invoice(Invoice(
        id=data["id"],
        vendor_id=data["vendor_id"],
        amount=data["amount"],
        due_date=data.get("due_date"),
        po_number=data.get("po_number"),
        status=data.get("status", "pending"),
    ))


# ---------------- Router by tool name ----------------

def _update_from_observation(wm: WorldModel, tool: str, args: dict, result: dict) -> None:
    """Dispatch to the right handler based on tool name."""
    if tool == "read_file":
        _handle_read_file(wm, result)

    elif tool == "api_get_vendor":
        if isinstance(result, dict) and "id" in result:
            _handle_vendor(wm, result)

    elif tool == "api_get_po":
        if isinstance(result, dict) and "po_number" in result:
            _handle_po(wm, result)

    elif tool == "api_get_invoice":
        if isinstance(result, dict) and "id" in result:
            _handle_invoice(wm, result)
    elif tool == "api_create_invoice":
        if isinstance(result, dict) and "id" in result:
            _handle_invoice(wm, result)

    elif tool == "api_get":
        endpoint = args.get("endpoint", "")
        if isinstance(result, dict) and "id" in result:
            # single-entity responses
            if endpoint.startswith("/api/vendors/"):
                _handle_vendor(wm, result)
            elif endpoint.startswith("/api/purchase_orders/"):
                _handle_po(wm, result)
            elif endpoint.startswith("/api/invoices/"):
                _handle_invoice(wm, result)
        elif isinstance(result, list):
            # list responses — route by endpoint
            for item in result:
                if not isinstance(item, dict):
                    continue
                if "aliases" in item and "name" in item:
                    _handle_vendor(wm, item)
                elif "po_number" in item:
                    _handle_po(wm, item)
                elif "vendor_id" in item and "amount" in item:
                    _handle_invoice(wm, item)

    elif tool == "remember":
        note = args.get("note", "")
        if note:
            wm.add_scratch(note)

    


# ---------------- Node entry point ----------------

def observer_node(state: AgentState) -> dict:
    obs = state.get("last_observation") or {}
    action = state.get("next_action") or {}
    tool = action.get("tool", "")
    args = action.get("args", {})

    # Reconstruct typed world model from serialized state
    wm = WorldModel(**state.get("world_model", {}))

    # Update world model on success
    if obs.get("success"):
        try:
            _update_from_observation(wm, tool, args, obs.get("result", {}))
        except Exception as e:
            # Never let a memory update crash the agent
            wm.add_scratch(f"(memory update error after {tool}: {e})")

    new_step_count = state.get("step_count", 0) + 1

    # Append to history
    history_entry = {
        "step": new_step_count,
        "action": action,
        "observation_success": obs.get("success"),
        "observation_summary": _summarize_obs(obs),
    }
    history = list(state.get("history", []))
    history.append(history_entry)

        # ---- Persist successful recovery ----
    recoveries = state.get("recoveries", [])
    if recoveries and obs.get("success"):
        pending = recoveries[-1]
        strategy_tool = pending["strategy"].get("tool", "")
        failed_tool = pending.get("failed_tool", "")

        # Only persist real fixes — same category, not diagnostics
        CATEGORIES = {
            "browser_open": "browser", "browser_fill": "browser",
            "browser_click": "browser", "browser_read": "browser",
            "browser_screenshot": "diag",
            "api_get": "api", "api_post": "api",
            "api_get_invoice": "api", "api_create_invoice": "api",
            "api_get_vendor": "api", "api_get_po": "api",
            "list_files": "file", "read_file": "file",
            "remember": "meta",
        }
        failed_cat = CATEGORIES.get(failed_tool, "?")
        strategy_cat = CATEGORIES.get(strategy_tool, "?")

        if (state.get("next_action") or {}).get("tool") == strategy_tool:
            if failed_cat == strategy_cat and strategy_cat not in ("diag", "meta", "?"):
                from agent.memory.recovery_memory import get_recovery_memory
                mem = get_recovery_memory()

                # In the persist block, before mem.store_success:
                recent_recoveries = [
                    r for r in recoveries
                    if r.get("signature") == pending["signature"]
                ]
                if len(recent_recoveries) > 1:
                    # Already persisted this run; skip
                    pass
                else:
                    mem.store_success(
                        signature=pending["signature"],
                        payload={
                            "tool": strategy_tool,
                            "args": pending["strategy"].get("args", {}),
                            "reason": pending["strategy"].get("reason", ""),
                        },
                    )
                    wm.add_scratch(f"learned recovery: {pending['signature']}")

    return {
        "world_model": wm.model_dump(),
        "history": history,
        "step_count": state.get("step_count", 0) + 1,
    }


def _summarize_obs(obs: dict) -> str:
    if not obs:
        return "no observation"
    if not obs.get("success"):
        return f"FAILED: {obs.get('error')}"
    result = obs.get("result", {})
    if "files" in result:
        return f"listed {len(result['files'])} files"
    if "content" in result:
        return f"read {len(result['content'])} chars"
    if "id" in result:
        return f"got entity {result['id']}"
    if "po_number" in result:
        return f"got PO {result['po_number']}"
    return "ok"