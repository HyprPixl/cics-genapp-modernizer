#!/usr/bin/env python3
"""Utility for maintaining a lightweight dependency graph of GenApp assets."""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import matplotlib.pyplot as plt
    import networkx as nx
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False

Graph = Dict[str, Any]


def load_graph(store: Path) -> Graph:
    if store.exists():
        with store.open("r", encoding="utf-8") as handle:
            data: Graph = json.load(handle)
            data.setdefault("nodes", {})
            return data
    return {"nodes": {}}


def save_graph(store: Path, graph: Graph) -> None:
    store.parent.mkdir(parents=True, exist_ok=True)
    with store.open("w", encoding="utf-8") as handle:
        json.dump(graph, handle, indent=2, sort_keys=True)
        handle.write("\n")


def get_nodes(graph: Graph) -> Dict[str, Dict[str, Any]]:
    return graph.setdefault("nodes", {})


def ensure_node(graph: Graph, name: str) -> Dict[str, Any]:
    nodes = get_nodes(graph)
    return nodes.setdefault(
        name,
        {
            "type": None,
            "description": None,
            "depends_on": [],
        },
    )


def add_dependency(graph: Graph, source: str, target: str) -> None:
    source_node = ensure_node(graph, source)
    ensure_node(graph, target)
    depends_on: List[str] = list(source_node.get("depends_on", []))
    if target not in depends_on:
        depends_on.append(target)
        depends_on.sort()
        source_node["depends_on"] = depends_on


def command_add_node(args: argparse.Namespace, graph: Graph) -> None:
    node = ensure_node(graph, args.name)
    if args.type:
        node["type"] = args.type
    if args.description:
        node["description"] = args.description
    for dep in args.depends_on or []:
        add_dependency(graph, args.name, dep)


def command_add_edge(args: argparse.Namespace, graph: Graph) -> None:
    add_dependency(graph, args.source, args.target)


def dependents_of(graph: Graph, name: str) -> List[str]:
    nodes = get_nodes(graph)
    result: List[str] = []
    for candidate, data in nodes.items():
        deps: List[str] = list(data.get("depends_on", []))
        if name in deps:
            result.append(candidate)
    result.sort()
    return result


def command_show(args: argparse.Namespace, graph: Graph) -> None:
    nodes = get_nodes(graph)
    node = nodes.get(args.name)
    if not node:
        print(f"{args.name} not found")
        return
    depends_on: List[str] = list(node.get("depends_on", []))
    print(f"Name: {args.name}")
    print(f"Type: {node.get('type') or '-'}")
    print(f"Description: {node.get('description') or '-'}")
    print("Depends on:")
    if depends_on:
        for dep in depends_on:
            print(f"  - {dep}")
    else:
        print("  (none)")
    if args.include_dependents:
        dependents = dependents_of(graph, args.name)
        print("Dependents:")
        if dependents:
            for entry in dependents:
                print(f"  - {entry}")
        else:
            print("  (none)")


def command_list_nodes(args: argparse.Namespace, graph: Graph) -> None:
    nodes = get_nodes(graph)
    for name in sorted(nodes.keys()):
        node = nodes[name]
        node_type: Optional[str] = node.get("type") if node.get("type") else None
        if args.type and node_type != args.type:
            continue
        description = node.get("description") or "-"
        print(f"{name}: {description}")


def command_dependents(args: argparse.Namespace, graph: Graph) -> None:
    deps = dependents_of(graph, args.name)
    if deps:
        for entry in deps:
            print(entry)
    else:
        print("(none)")


def command_visualize(args: argparse.Namespace, graph: Graph) -> None:
    """Generate a visual representation of the dependency graph."""
    if not VISUALIZATION_AVAILABLE:
        print("Visualization requires matplotlib and networkx. Install with:")
        print("pip install matplotlib networkx")
        return
    
    nodes = get_nodes(graph)
    if not nodes:
        print("No nodes in graph to visualize")
        return
    
    # Create NetworkX graph
    G = nx.DiGraph()
    
    # Add nodes with attributes
    for name, data in nodes.items():
        node_type = data.get("type") or "unknown"
        description = data.get("description") or ""
        G.add_node(name, type=node_type, description=description)
    
    # Add edges (dependencies)
    for name, data in nodes.items():
        depends_on = data.get("depends_on", [])
        for dep in depends_on:
            if dep in nodes:  # Only add edge if target exists
                G.add_edge(name, dep)  # from dependent to dependency
    
    # Filter by type if specified
    if args.filter_type:
        filtered_nodes = [n for n, d in G.nodes(data=True) 
                         if d.get("type") == args.filter_type]
        G = G.subgraph(filtered_nodes).copy()
        if not G.nodes():
            print(f"No nodes of type '{args.filter_type}' found")
            return
    
    # Set up the plot
    plt.figure(figsize=(args.width or 16, args.height or 12))
    plt.title(f"CICS GenApp Dependency Graph{' (' + args.filter_type + ')' if args.filter_type else ''}")
    
    # Define colors for different node types
    type_colors = {
        'cobol': '#4CAF50',      # Green
        'copybook': '#2196F3',   # Blue  
        'sql-include': '#3F51B5', # Indigo
        'db2-table': '#FF9800',  # Orange
        'vsam-file': '#9C27B0',  # Purple
        'jcl': '#795548',        # Brown
        'rexx': '#607D8B',       # Blue Grey
        'shell': '#424242',      # Dark Grey
        'bms-map': '#E91E63',    # Pink
        'dataset': '#FFC107',    # Amber
        'wsim-script': '#8BC34A', # Light Green
        'event-binding': '#FF5722', # Deep Orange
        'cics-counter': '#00BCD4', # Cyan
        'unknown': '#9E9E9E'     # Grey
    }
    
    # Color nodes by type
    node_colors = []
    for node in G.nodes():
        node_type = G.nodes[node].get('type', 'unknown')
        node_colors.append(type_colors.get(node_type, type_colors['unknown']))
    
    # Choose layout based on graph size and type
    if len(G.nodes()) < 20:
        pos = nx.spring_layout(G, k=3, iterations=50, seed=42)
    elif args.layout == 'hierarchical':
        # Try to create a hierarchical layout for larger graphs
        try:
            pos = nx.nx_agraph.graphviz_layout(G, prog='dot')
        except:
            pos = nx.spring_layout(G, k=1, iterations=30, seed=42)
    else:
        pos = nx.spring_layout(G, k=1, iterations=30, seed=42)
    
    # Draw the graph
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, 
                          node_size=1000, alpha=0.8)
    
    # Draw edges with arrows
    nx.draw_networkx_edges(G, pos, edge_color='gray', 
                          arrows=True, arrowsize=20, 
                          arrowstyle='->', alpha=0.6)
    
    # Add labels
    if args.show_labels:
        if len(G.nodes()) <= 30:  # Only show labels for smaller graphs
            nx.draw_networkx_labels(G, pos, font_size=8, font_weight='bold')
        else:
            print(f"Skipping labels for large graph ({len(G.nodes())} nodes). Use --show-labels to force.")
    
    # Create legend
    if not args.filter_type:  # Only show legend for full graph
        unique_types = set(G.nodes[node].get('type', 'unknown') for node in G.nodes())
        legend_elements = []
        for node_type in sorted(unique_types):
            color = type_colors.get(node_type, type_colors['unknown'])
            legend_elements.append(plt.Line2D([0], [0], marker='o', color='w', 
                                            markerfacecolor=color, markersize=10, 
                                            label=node_type))
        
        plt.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1.05, 1))
    
    plt.tight_layout()
    
    # Save the plot
    output_path = Path(args.output)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Visualization saved to: {output_path}")
    
    # Show statistics
    print(f"\nGraph Statistics:")
    print(f"  Nodes: {len(G.nodes())}")
    print(f"  Edges: {len(G.edges())}")
    if G.nodes():
        print(f"  Node types: {len(set(G.nodes[node].get('type', 'unknown') for node in G.nodes()))}")
        
        # Find nodes with most dependencies and dependents
        most_deps = max(G.nodes(), key=lambda n: len(list(G.predecessors(n))))
        most_dependents = max(G.nodes(), key=lambda n: len(list(G.successors(n))))
        
        print(f"  Most dependencies: {most_deps} ({len(list(G.predecessors(most_deps)))} deps)")
        print(f"  Most dependents: {most_dependents} ({len(list(G.successors(most_dependents)))} dependents)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage the CICS GenApp dependency graph."
    )
    parser.add_argument(
        "--store",
        default=Path("dependency_graph.json"),
        type=Path,
        help="Path to the JSON store (default: dependency_graph.json)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_node = subparsers.add_parser("add-node", help="Add or update a node")
    add_node.add_argument("name", help="Identifier for the node")
    add_node.add_argument("--type", help="Node category (e.g., cobol, copybook, jcl)")
    add_node.add_argument("--description", help="Short description for the node")
    add_node.add_argument(
        "--depends-on",
        nargs="*",
        default=[],
        help="Nodes this node depends on",
    )
    add_node.set_defaults(func=command_add_node)

    add_edge = subparsers.add_parser("add-edge", help="Create a dependency edge")
    add_edge.add_argument("source", help="Dependent node (the caller)")
    add_edge.add_argument("target", help="Dependency node")
    add_edge.set_defaults(func=command_add_edge)

    show = subparsers.add_parser("show", help="Display a node and its metadata")
    show.add_argument("name", help="Node identifier to show")
    show.add_argument(
        "--include-dependents",
        action="store_true",
        help="Also list nodes that reference this node",
    )
    show.set_defaults(func=command_show)

    list_nodes = subparsers.add_parser("list", help="List known nodes")
    list_nodes.add_argument(
        "--type",
        help="Filter output to a specific node type",
    )
    list_nodes.set_defaults(func=command_list_nodes)

    dependents = subparsers.add_parser(
        "dependents", help="List nodes that depend on the target"
    )
    dependents.add_argument("name", help="Node identifier to inspect")
    dependents.set_defaults(func=command_dependents)

    visualize = subparsers.add_parser("visualize", help="Generate a visual graph")
    visualize.add_argument(
        "--output", 
        default="dependency_graph.png",
        help="Output image file (default: dependency_graph.png)"
    )
    visualize.add_argument(
        "--filter-type",
        help="Show only nodes of specific type (e.g., cobol, db2-table)"
    )
    visualize.add_argument(
        "--layout",
        choices=["spring", "hierarchical"],
        default="spring",
        help="Graph layout algorithm (default: spring)"
    )
    visualize.add_argument(
        "--width",
        type=int,
        help="Figure width in inches (default: 16)"
    )
    visualize.add_argument(
        "--height", 
        type=int,
        help="Figure height in inches (default: 12)"
    )
    visualize.add_argument(
        "--show-labels",
        action="store_true",
        help="Force showing node labels even for large graphs"
    )
    visualize.set_defaults(func=command_visualize)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    graph = load_graph(args.store)
    args.func(args, graph)
    save_graph(args.store, graph)


if __name__ == "__main__":
    main()
