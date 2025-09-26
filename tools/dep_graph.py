#!/usr/bin/env python3
"""Utility for maintaining a lightweight dependency graph of GenApp assets."""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

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

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    graph = load_graph(args.store)
    args.func(args, graph)
    save_graph(args.store, graph)


if __name__ == "__main__":
    main()
