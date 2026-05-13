import os
from dotenv import load_dotenv
load_dotenv()

from aria.core.agent import build_aria_graph

aria = build_aria_graph()

# Draw and save the graph
graph_image = aria.get_graph().draw_mermaid_png()

with open("aria_graph.png", "wb") as f:
    f.write(graph_image)

print("Graph saved as aria_graph.png — open it to see your agent!")
