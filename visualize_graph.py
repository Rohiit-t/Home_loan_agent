"""
Visualize the Home Loan Application Graph structure.
Uses LangGraph's built-in visualization tools.
"""

from app.backend.graph.main import build_graph


def visualize_graph():
    """Generate and display graph visualization"""
    
    print("="*80)
    print("  HOME LOAN APPLICATION GRAPH VISUALIZATION")
    print("="*80)
    
    # Build the graph
    print("\nBuilding graph...")
    graph = build_graph()
    
    # Get the graph structure
    graph_structure = graph.get_graph()
    
    print("\n" + "="*80)
    print("  ASCII REPRESENTATION")
    print("="*80 + "\n")
    
    # Draw ASCII representation
    try:
        ascii_graph = graph_structure.draw_ascii()
        print(ascii_graph)
    except Exception as e:
        print(f"ASCII visualization not available: {e}")
    
    print("\n" + "="*80)
    print("  MERMAID DIAGRAM")
    print("="*80 + "\n")
    
    # Generate Mermaid diagram
    try:
        mermaid_code = graph_structure.draw_mermaid()
        print(mermaid_code)
        print("\n")
        print("Copy the above Mermaid code to: https://mermaid.live/")
        print("Or use a Mermaid viewer to visualize the graph")
    except Exception as e:
        print(f"Mermaid visualization error: {e}")
    
    print("\n" + "="*80)
    print("  GRAPH NODES")
    print("="*80 + "\n")
    
    # List all nodes
    nodes = graph_structure.nodes
    print(f"Total Nodes: {len(nodes)}\n")
    for node in nodes:
        print(f"  • {node}")
    
    print("\n" + "="*80)
    print("  GRAPH EDGES")
    print("="*80 + "\n")
    
    # List all edges
    edges = graph_structure.edges
    print(f"Total Edges: {len(edges)}\n")
    for edge in edges:
        print(f"  {edge.source} → {edge.target}")
    
    print("\n" + "="*80)
    print("  PNG VISUALIZATION")
    print("="*80 + "\n")
    
    # Try to generate PNG (requires graphviz)
    try:
        png_data = graph_structure.draw_mermaid_png()
        
        # Save to file
        output_file = "graph_visualization.png"
        with open(output_file, "wb") as f:
            f.write(png_data)
        
        print(f"✅ PNG visualization saved to: {output_file}")
        print("   Open this file to view the graph structure")
    except Exception as e:
        print(f"⚠️  PNG generation failed: {e}")
        print("   Install required dependencies: pip install pygraphviz")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    visualize_graph()
