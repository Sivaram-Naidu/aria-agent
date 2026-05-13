from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from aria.core.state import ARIAState
from aria.core.nodes import (
    analyze_input,
    build_context,
    support_mode,
    friend_mode,
    format_response,
    route_by_emotion
)


def build_aria_graph():
    # Initialize the graph with our state schema
    graph = StateGraph(ARIAState)

    # ── Add all nodes ──
    graph.add_node("analyze_input", analyze_input)
    graph.add_node("build_context", build_context)
    graph.add_node("support_mode", support_mode)
    graph.add_node("friend_mode", friend_mode)
    graph.add_node("format_response", format_response)

    # ── Define the flow ──
    graph.set_entry_point("analyze_input")
    graph.add_edge("analyze_input", "build_context")

    # ── Conditional edge — the magic! ──
    graph.add_conditional_edges(
        "build_context",          # from this node
        route_by_emotion,         # call this function to decide
        {
            "support": "support_mode",   # if returns "support"
            "friend": "friend_mode"      # if returns "friend"
        }
    )

    # Both modes converge to format_response
    graph.add_edge("support_mode", "format_response")
    graph.add_edge("friend_mode", "format_response")
    graph.add_edge("format_response", END)

    # ── Compile with in-session memory ──
    memory = MemorySaver()
    compiled = graph.compile(checkpointer=memory)

    return compiled
