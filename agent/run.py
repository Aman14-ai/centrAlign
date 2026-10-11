import sys
import uuid
from langgraph.types import Command
from agent.graph import build_graph
from agent.memory.world_model import WorldModel
from agent.memory.session import save_report

thread_id = f"run-{uuid.uuid4().hex[:8]}"

def initial_state(task: str) -> dict:
    return {
        "task": task,
        "goal": "",
        "next_action": None,
        "last_observation": None,
        "history": [],
        "world_model": WorldModel().model_dump(),
        "step_count": 0,
        "max_steps": 15,
        "status": "running",
        "approvals": [],
        "pending_question": None,
        "risk_score": 0.0,
        "summary": "",
        "verification": None,
        "rollback": None,
        "evidence": [],
        "failures": [],
        "recoveries": [],
        "failed_actions": [],      # ← add
        "asked_questions": [],     # ← add
        "pending_answer": None,    # ← add
    }

def _print_interrupt(payload: dict) -> None:
    print("\n" + "-" * 60)
    print("⚠️  HUMAN INPUT REQUIRED")
    print("-" * 60)
    q = payload.get("question") or payload.get("payload", {}).get("question")
    print(f"Question: {q}")

    action = payload.get("action") or payload.get("payload", {}).get("action")
    if action:
        print(f"Action: {action.get('tool')}({action.get('args')})")
        if action.get("reason"):
            print(f"Reason: {action['reason']}")

    risk = payload.get("risk_score") or payload.get("payload", {}).get("risk_score")
    if risk is not None:
        print(f"Risk score: {risk}")

    evidence = payload.get("evidence") or payload.get("payload", {}).get("evidence", [])
    if evidence:
        print(f"Evidence: {len(evidence)} item(s)")

    options = payload.get("options") or payload.get("payload", {}).get("options", [])
    if options:
        print(f"Options: {options}")


CANCEL_ALIASES = {"cancel", "stop", "abort", "quit", "exit", "no", "n"}


def _prompt_decision(payload: dict) -> dict:
    _print_interrupt(payload)
    options = payload.get("options") or payload.get("payload", {}).get("options", [])
    is_approval = "approve" in options and "reject" in options

    raw = input("Your choice: ").strip()
    lowered = raw.lower()

    if is_approval:
        if lowered in ("a", "approve", "y", "yes"):
            return {"choice": "approve"}
        return {"choice": "reject"}

    # Clarification prompt — pass through, but normalize cancel tokens
    if lowered in CANCEL_ALIASES:
        return {"choice": "cancel"}

    return {"choice": raw}

def _print_report(result: dict) -> None:
    print("\n" + "=" * 60)
    print("TASK:", result.get("task", ""))
    print("=" * 60)
    print("\nGOAL:", result.get("goal", ""))

    print("\nSTEPS:")
    for h in result.get("history", []):
        tool = h["action"].get("tool", "?")
        print(f"  [{h['step']}] {tool:<20} -> {h['observation_summary']}")

    print("\nWORLD MODEL:")
    from agent.memory.world_model import WorldModel
    wm = WorldModel(**result.get("world_model", {}))
    print(wm.to_prompt_text())

    v = result.get("verification")
    if v:
        status = "PASSED" if v.get("passed") else "FAILED"
        print(f"\nVERIFICATION: {status}")
        if v.get("reason"):
            print(f"  {v['reason']}")

    if result.get("rollback"):
        r = result["rollback"]
        print(f"\nROLLBACK: performed={r.get('performed')} reason={r.get('reason')}")

    if result.get("approvals"):
        print("\nAPPROVALS:")
        for a in result["approvals"]:
            d = a.get("decision") or a.get("answer")
            print(f"  - {a.get('question')} -> {d}")

    if result.get("failures"):
        print("\nFAILURES:")
        for f in result["failures"]:
            print(f"  - {f.get('type')}: {f.get('signature')}")

    if result.get("evidence"):
        print("\nEVIDENCE:")
        for e in result["evidence"][:5]:
            print(f"  - [{e.get('type')}] {e.get('description', '')}")

    print("\nSUMMARY:")
    print(" ", result.get("summary", ""))

    print("\nSTATUS:", result.get("status"))
    print("=" * 60)

def main():
    if len(sys.argv) < 2:
        print('Usage: python -m agent.run "your task here"')
        return

    task = sys.argv[1]
    graph = build_graph()

    
    config = {"configurable": {"thread_id": thread_id}}
    print(f"\n[thread_id={thread_id}]")

    result = graph.invoke(initial_state(task), config)

    # Loop: keep resuming whenever the graph interrupts
    while "__interrupt__" in result:
        interrupts = result["__interrupt__"]
        # LangGraph returns a tuple of Interrupt objects
        payload = interrupts[0].value if hasattr(interrupts[0], "value") else interrupts[0]
        decision = _prompt_decision(payload)
        # Resume with the user's decision
        result = graph.invoke(Command(resume=decision), config)


    report = result.get("final_report")
    if report:
        path = save_report(report)
        print(f"\n[report saved: {path}]")

    _print_report(result)


if __name__ == "__main__":
    main()