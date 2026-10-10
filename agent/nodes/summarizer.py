from agent.llm import llm
from agent.state import AgentState
from agent.memory.world_model import WorldModel
from agent.memory.evidence import collect_evidence
from agent.report import (
    FinalReport, ApprovalItem, FailureItem, RecoveryItem, now_iso,
)


SUMMARY_PROMPT = """
You are writing the executive summary of an AI worker's task.

Task: {task}
Goal: {goal}
Status: {status}

Steps taken ({step_count}):
{history}

Verification: {verification_text}
Rollback: {rollback_text}
Approvals: {approvals_text}
Failures: {failures_text}
Recoveries: {recoveries_text}

World model (final knowledge):
{world_model}

Write a 4-6 line summary that includes:
1. What the agent did (one line).
2. Specific values discovered (amounts, emails, IDs, dates).
3. Whether verification passed.
4. If rollback happened, mention it.
5. Whether the goal was achieved.

STRICT RULES:
- If the goal asked for a specific value, include it verbatim.
- Do NOT invent data.
- If verification failed or was skipped for a write, say so.
- If any human approval was required, mention the decision.

No preamble, no markdown, plain prose.
"""


def _format_verification(state: AgentState) -> str:
    v = state.get("verification")
    if not v:
        return "(not run)"
    return f"{'PASSED' if v.get('passed') else 'FAILED'} — {v.get('reason', '')}"


def _format_rollback(state: AgentState) -> str:
    r = state.get("rollback")
    if not r:
        return "(none)"
    return f"performed={r.get('performed')} reason={r.get('reason')}"


def _format_approvals(state: AgentState) -> str:
    approvals = state.get("approvals", [])
    if not approvals:
        return "(none)"
    lines = []
    for a in approvals:
        d = a.get("decision") or a.get("answer")
        lines.append(f"- {a.get('question')} -> {d}")
    return "\n".join(lines)


def _format_failures(state: AgentState) -> str:
    failures = state.get("failures", [])
    if not failures:
        return "(none)"
    return "\n".join(
        f"- {f.get('tool')}: {f.get('type')} ({f.get('signature')})"
        for f in failures
    )


def _format_recoveries(state: AgentState) -> str:
    recoveries = state.get("recoveries", [])
    if not recoveries:
        return "(none)"
    return "\n".join(
        f"- {r.get('signature')} -> {r.get('strategy', {}).get('tool')} ({r.get('source')})"
        for r in recoveries
    )


def _build_report(state: AgentState, narrative: str) -> FinalReport:
    history_text = [
        {
            "step": h.get("step"),
            "tool": h.get("action", {}).get("tool"),
            "summary": h.get("observation_summary"),
            "success": h.get("observation_success"),
        }
        for h in state.get("history", [])
    ]

    
    
    approvals = [
        ApprovalItem(
            timestamp=a.get("timestamp", ""),
            question=a.get("question", ""),
            decision=(
                a.get("decision").get("choice", "unknown")
                if isinstance(a.get("decision"), dict)
                else str(a.get("decision") or a.get("answer") or "unknown")
            ),
            answer=(
                a.get("answer").get("choice")
                if isinstance(a.get("answer"), dict)
                else a.get("answer")
            ),
            action=a.get("action"),
            risk_score=a.get("risk_score"),
        )
        for a in state.get("approvals", [])
    ]
    
    failures = [
        FailureItem(
            step=None,
            tool=f.get("action", {}).get("tool", ""),
            type=f.get("type", ""),
            error=f.get("error", "")[:300],
            signature=f.get("signature", ""),
        )
        for f in state.get("failures", [])
    ]

    recoveries = [
        RecoveryItem(
            signature=r.get("signature", ""),
            strategy_tool=r.get("strategy", {}).get("tool", ""),
            strategy_reason=r.get("strategy", {}).get("reason", ""),
            source=r.get("source", ""),
            succeeded=(r.get("source") in ("memory_exact", "memory_similar") or True),
        )
        for r in state.get("recoveries", [])
    ]

    v = state.get("verification") or {}
    rb = state.get("rollback") or {}

    return FinalReport(
        run_id=state.get("thread_id", ""),
        thread_id=state.get("thread_id", ""),
        timestamp=now_iso(),
        task=state.get("task", ""),
        goal=state.get("goal", ""),
        status=state.get("status", ""),
        summary=narrative,
        total_steps=state.get("step_count", 0),
        history=history_text,
        verification_passed=v.get("passed"),
        verification_reason=v.get("reason", ""),
        rollback_performed=bool(rb.get("performed")),
        rollback_reason=rb.get("reason", ""),
        approvals=approvals,
        failures=failures,
        recoveries=recoveries,
        evidence=collect_evidence(state),
        world_model=state.get("world_model", {}),
        metrics={
            "steps": state.get("step_count", 0),
            "failures": len(state.get("failures", [])),
            "recoveries": len(state.get("recoveries", [])),
            "approvals": len(state.get("approvals", [])),
        },
    )


def summarizer_node(state: AgentState) -> dict:
    wm = WorldModel(**state.get("world_model", {}))

    prompt = SUMMARY_PROMPT.format(
        task=state.get("task", ""),
        goal=state.get("goal", ""),
        status=state.get("status", ""),
        step_count=state.get("step_count", 0),
        history="\n".join(
            f"- {h.get('step')}: {h.get('action', {}).get('tool')} -> {h.get('observation_summary')}"
            for h in state.get("history", [])
        ) or "(no steps)",
        verification_text=_format_verification(state),
        rollback_text=_format_rollback(state),
        approvals_text=_format_approvals(state),
        failures_text=_format_failures(state),
        recoveries_text=_format_recoveries(state),
        world_model=wm.to_prompt_text(),
    )

    narrative = llm.invoke(prompt).content.strip()

    report = _build_report(state, narrative)

    

    final_status = state.get("status")
    if final_status in ("running", "waiting_approval") or not final_status:
        if (state.get("rollback") or {}).get("performed"):
            final_status = "failed"
        elif (state.get("verification") or {}).get("passed") is False:
            final_status = "failed"
        else:
            final_status = "done"

    # Check narrative for failure signals
    if final_status == "done":
        summary_lower = narrative.lower()
        if "not achieved" in summary_lower or "not fully" in summary_lower or "could not" in summary_lower:
            final_status = "partial"

    return {"summary": narrative, "status": final_status, "final_report": report.model_dump()}