
from contextlib import ExitStack

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

from agent.state import AgentState
from agent.nodes.intake import intake_node
from agent.nodes.planner import planner_node
from agent.nodes.executor import executor_node
from agent.nodes.observer import observer_node
from agent.nodes.router import route_after_observer,route_after_verifier,route_after_approval,route_before_executor
from agent.nodes.summarizer import summarizer_node
from agent.nodes.diagnoser import diagnoser_node
from agent.nodes.recovery import recovery_node
from agent.nodes.verifier import verifier_node
from agent.nodes.rollback import rollback_node
from agent.nodes.human_approval import human_approval_node
from agent.nodes.ask_user import ask_user_node
from agent.nodes.force_done import force_done_node
from agent.nodes.ask_user_trigger import ask_user_trigger_node

# Keep the SQLite connection alive while the graph is in use.
_checkpointer_stack = ExitStack()


def build_graph():
    # Nodes
    g=StateGraph(AgentState)
    g.add_node("intake", intake_node)
    g.add_node("planner", planner_node)
    g.add_node("executor", executor_node)
    g.add_node("observer", observer_node)
    g.add_node("diagnoser", diagnoser_node)
    g.add_node("recovery", recovery_node)
    g.add_node("summarizer", summarizer_node)
    g.add_node("verifier",verifier_node)
    g.add_node("rollback", rollback_node)
    g.add_node("approve", human_approval_node)
    g.add_node("ask_user", ask_user_node)


     # Entry
    g.add_edge(START, "intake")
    g.add_edge("intake", "planner")

    # Planner → [approve | executor]
    g.add_node("ask_user_trigger", ask_user_trigger_node)
    g.add_edge("ask_user_trigger", "ask_user")

    g.add_node("force_done", force_done_node)
    g.add_edge("force_done", "summarizer")

    g.add_conditional_edges(
        "planner",
        route_before_executor,
        {
            "approve": "approve",
            "execute": "executor",
            "ask_user_trigger": "ask_user_trigger",
            "force_done": "force_done",
        },
    )

    g.add_edge("executor", "observer")

    g.add_conditional_edges(
        "observer",
        route_after_observer,
        {
            "continue": "planner",
            "diagnose": "diagnoser",
            "verify": "verifier",
            "ask_user": "ask_user",
            "summarize": "summarizer",
        },
    )

    # Failure path
    g.add_edge("diagnoser", "recovery")
    g.add_edge("recovery", "executor")

    # Verification path
    g.add_conditional_edges(
        "verifier",
        route_after_verifier,
        {"summarize": "summarizer", "rollback": "rollback"},
    )
    g.add_edge("rollback", "summarizer")

    # HITL paths
    g.add_conditional_edges(
        "approve",
        route_after_approval,
        {"execute": "executor", "summarize": "summarizer"},
    )
    g.add_edge("ask_user", "planner")

    

    # End
    g.add_edge("summarizer", END)

    checkpointer = _checkpointer_stack.enter_context(
        SqliteSaver.from_conn_string("agent_checkpoints.db")
    )

    return g.compile(checkpointer=checkpointer)