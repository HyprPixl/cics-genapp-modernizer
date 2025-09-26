#!/usr/bin/env python3
"""
Dependency Graph Visualization Tool for CICS GenApp Modernizer

Creates visual representations of the dependency graph stored in dependency_graph.json.
Uses networkx for graph manipulation and matplotlib for rendering.
"""

import argparse
import json
import matplotlib.pyplot as plt
import networkx as nx
from pathlib import Path
from typing import Dict, Any, List, Tuple


def load_dependency_graph(store_path: Path) -> Dict[str, Any]:
    """Load the dependency graph from JSON file."""
    if not store_path.exists():
        raise FileNotFoundError(f"Dependency graph not found: {store_path}")
    
    with store_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def create_networkx_graph(graph_data: Dict[str, Any]) -> nx.DiGraph:
    """Convert dependency graph data to NetworkX directed graph."""
    G = nx.DiGraph()
    
    nodes = graph_data.get("nodes", {})
    
    # Add nodes with attributes
    for node_name, node_data in nodes.items():
        G.add_node(
            node_name,
            type=node_data.get("type", "unknown"),
            description=node_data.get("description", ""),
        )
    
    # Add edges based on dependencies
    # Edge direction: from dependent TO dependency (A depends on B: A -> B)
    for node_name, node_data in nodes.items():
        dependencies = node_data.get("depends_on", [])
        for dep in dependencies:
            if dep in nodes:  # Only add edge if target node exists
                G.add_edge(node_name, dep)  # node_name -> dep (node_name depends on dep)
    
    return G


def get_node_colors_and_shapes(G: nx.DiGraph) -> Tuple[List[str], Dict[str, str]]:
    """Assign colors and shapes based on node types."""
    color_map = {
        "cobol": "#4CAF50",           # Green for COBOL programs
        "copybook": "#2196F3",        # Blue for copybooks
        "sql-include": "#9C27B0",     # Purple for SQL includes
        "db2-table": "#FF9800",       # Orange for DB2 tables
        "vsam-file": "#F44336",       # Red for VSAM files
        "unknown": "#9E9E9E",         # Gray for unknown types
    }
    
    shape_map = {
        "cobol": "o",          # Circle for COBOL
        "copybook": "s",       # Square for copybooks
        "sql-include": "^",    # Triangle for SQL includes
        "db2-table": "D",      # Diamond for DB2 tables
        "vsam-file": "h",      # Hexagon for VSAM files
        "unknown": ".",        # Point for unknown
    }
    
    node_colors = []
    node_shapes = {}
    
    for node in G.nodes():
        node_type = G.nodes[node].get("type", "unknown")
        node_colors.append(color_map.get(node_type, color_map["unknown"]))
        node_shapes[node_type] = shape_map.get(node_type, "o")
    
    return node_colors, node_shapes


def create_visualization(G: nx.DiGraph, output_path: Path, title: str = "CICS GenApp Dependency Graph"):
    """Create and save the dependency graph visualization."""
    plt.figure(figsize=(16, 12))
    
    # Use hierarchical layout to show dependencies clearly
    try:
        # Try to use hierarchical layout if possible
        pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
    except:
        # Fall back to spring layout if graphviz not available
        pos = nx.spring_layout(G, k=3, iterations=50, seed=42)
    
    # Get node colors
    node_colors, node_shapes = get_node_colors_and_shapes(G)
    
    # Draw nodes by type to get different shapes
    node_types = {}
    for node in G.nodes():
        node_type = G.nodes[node].get("type", "unknown")
        if node_type not in node_types:
            node_types[node_type] = []
        node_types[node_type].append(node)
    
    # Draw each node type with its specific shape and color
    for node_type, nodes in node_types.items():
        node_positions = {node: pos[node] for node in nodes}
        color = {
            "cobol": "#4CAF50",
            "copybook": "#2196F3", 
            "sql-include": "#9C27B0",
            "db2-table": "#FF9800",
            "vsam-file": "#F44336",
            "unknown": "#9E9E9E",
        }.get(node_type, "#9E9E9E")
        
        shape = {
            "cobol": "o",
            "copybook": "s",
            "sql-include": "^", 
            "db2-table": "D",
            "vsam-file": "h",
            "unknown": "o",
        }.get(node_type, "o")
        
        nx.draw_networkx_nodes(
            G, node_positions, nodelist=nodes,
            node_color=color, node_shape=shape,
            node_size=1000, alpha=0.8
        )
    
    # Draw edges
    nx.draw_networkx_edges(
        G, pos, edge_color="#666666", 
        arrows=True, arrowsize=20, arrowstyle="->",
        alpha=0.6, width=1.5
    )
    
    # Draw labels
    nx.draw_networkx_labels(G, pos, font_size=8, font_weight="bold")
    
    plt.title(title, size=16, weight="bold", pad=20)
    
    # Create legend
    legend_elements = [
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="#4CAF50", 
                  markersize=10, label="COBOL Programs"),
        plt.Line2D([0], [0], marker="s", color="w", markerfacecolor="#2196F3", 
                  markersize=10, label="Copybooks"),
        plt.Line2D([0], [0], marker="^", color="w", markerfacecolor="#9C27B0", 
                  markersize=10, label="SQL Includes"),
        plt.Line2D([0], [0], marker="D", color="w", markerfacecolor="#FF9800", 
                  markersize=10, label="DB2 Tables"),
        plt.Line2D([0], [0], marker="h", color="w", markerfacecolor="#F44336", 
                  markersize=10, label="VSAM Files"),
    ]
    
    plt.legend(handles=legend_elements, loc="upper left", bbox_to_anchor=(0, 1))
    
    # Remove axes
    plt.axis("off")
    
    # Adjust layout and save
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight", 
                facecolor="white", edgecolor="none")
    plt.close()
    
    print(f"Visualization saved to: {output_path}")


def print_graph_statistics(G: nx.DiGraph):
    """Print interesting statistics about the dependency graph."""
    print("\n=== Dependency Graph Statistics ===")
    print(f"Total nodes: {G.number_of_nodes()}")
    print(f"Total edges: {G.number_of_edges()}")
    
    # Node type distribution
    type_counts = {}
    for node in G.nodes():
        node_type = G.nodes[node].get("type", "unknown")
        type_counts[node_type] = type_counts.get(node_type, 0) + 1
    
    print("\nNode type distribution:")
    for node_type, count in sorted(type_counts.items(), key=lambda x: (x[0] or "unknown")):
        display_type = node_type if node_type else "unknown"
        print(f"  {display_type}: {count}")
    
    # Find nodes with most dependencies
    in_degrees = dict(G.in_degree())
    out_degrees = dict(G.out_degree())
    
    print(f"\nMost depended upon (highest in-degree):")
    sorted_in = sorted(in_degrees.items(), key=lambda x: x[1], reverse=True)[:5]
    for node, degree in sorted_in:
        if degree > 0:
            print(f"  {node}: {degree} dependents")
    
    print(f"\nMost complex components (highest out-degree - depend on many others):")
    sorted_out = sorted(out_degrees.items(), key=lambda x: x[1], reverse=True)[:5]
    for node, degree in sorted_out:
        if degree > 0:
            print(f"  {node}: depends on {degree} others")
    
    # Find isolated nodes
    isolated = list(nx.isolates(G))
    if isolated:
        print(f"\nIsolated nodes (no dependencies): {len(isolated)}")
        for node in isolated[:5]:  # Show first 5
            print(f"  {node}")
        if len(isolated) > 5:
            print(f"  ... and {len(isolated) - 5} more")


def suggest_documentation_priorities(G: nx.DiGraph) -> List[str]:
    """Suggest which components to document first based on graph analysis."""
    suggestions = []
    
    # High impact nodes (many dependents) - these are nodes with high in-degree
    in_degrees = dict(G.in_degree())
    high_impact = [node for node, degree in in_degrees.items() if degree >= 3]
    
    if high_impact:
        suggestions.append("High Impact Components (many dependents):")
        for node in sorted(high_impact, key=lambda x: in_degrees[x], reverse=True):
            node_type = G.nodes[node].get("type", "unknown")
            description = G.nodes[node].get("description", "No description")
            suggestions.append(f"  • {node} ({node_type}): {in_degrees[node]} dependents - {description}")
    
    # Foundation nodes (no dependencies but others depend on them) - out-degree = 0, in-degree > 0
    foundation = [node for node in G.nodes() 
                 if G.out_degree(node) == 0 and G.in_degree(node) > 0]
    
    if foundation:
        suggestions.append("\nFoundation Components (no dependencies, but others depend on them):")
        for node in sorted(foundation, key=lambda x: in_degrees[x], reverse=True):
            node_type = G.nodes[node].get("type", "unknown")
            description = G.nodes[node].get("description", "No description")
            suggestions.append(f"  • {node} ({node_type}): {in_degrees[node]} dependents - {description}")
    
    # Entry points (high out-degree, meaning they depend on many others - front-end components)
    out_degrees = dict(G.out_degree())
    entry_points = [node for node, degree in out_degrees.items() if degree >= 3]
    
    if entry_points:
        suggestions.append("\nLikely Entry Points (many dependencies, suggesting front-end role):")
        for node in sorted(entry_points, key=lambda x: out_degrees[x], reverse=True):
            node_type = G.nodes[node].get("type", "unknown")
            description = G.nodes[node].get("description", "No description")
            suggestions.append(f"  • {node} ({node_type}): depends on {out_degrees[node]} others - {description}")
    
    return suggestions


def main():
    parser = argparse.ArgumentParser(
        description="Generate dependency graph visualization for CICS GenApp"
    )
    parser.add_argument(
        "--store",
        type=Path,
        default=Path("dependency_graph.json"),
        help="Path to dependency graph JSON file (default: dependency_graph.json)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tools/dependency_graph_current_state.png"),
        help="Output path for visualization (default: tools/dependency_graph_current_state.png)"
    )
    parser.add_argument(
        "--title",
        default="CICS GenApp Dependency Graph - Current State",
        help="Title for the visualization"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print graph statistics"
    )
    parser.add_argument(
        "--suggestions",
        action="store_true", 
        help="Print documentation priority suggestions"
    )
    
    args = parser.parse_args()
    
    try:
        # Load and process the dependency graph
        graph_data = load_dependency_graph(args.store)
        G = create_networkx_graph(graph_data)
        
        # Create visualization
        create_visualization(G, args.output, args.title)
        
        if args.stats:
            print_graph_statistics(G)
        
        if args.suggestions:
            suggestions = suggest_documentation_priorities(G)
            print("\n=== Documentation Priority Suggestions ===")
            for suggestion in suggestions:
                print(suggestion)
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())