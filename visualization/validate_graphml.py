#!/usr/bin/env python3
"""Validate generated GraphML structure and coverage against the JSON source."""

from __future__ import annotations

import json
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent.parent
VIS = ROOT / "visualization"
GRAPHML = "{http://graphml.graphdrawing.org/xmlns}"
YED = "{http://www.yworks.com/xml/graphml}"


def load_graph(name: str):
    path = VIS / name
    root = ET.parse(path).getroot()
    nodes = root.findall(f".//{GRAPHML}node")
    edges = root.findall(f".//{GRAPHML}edge")
    ids = [node.attrib["id"] for node in nodes]
    assert len(ids) == len(set(ids)), f"duplicate node id in {name}"
    assert all(edge.attrib["source"] in ids and edge.attrib["target"] in ids for edge in edges), f"unresolved endpoint in {name}"
    assert len(root.findall(f".//{YED}ShapeNode")) == len(nodes), f"missing yEd node graphics in {name}"
    assert len(root.findall(f".//{YED}PolyLineEdge")) == len(edges), f"missing yEd edge graphics in {name}"
    return root, nodes, edges


def source_relation_edges(relations: list[dict]) -> dict[tuple[str, str], tuple[str, set[str]]]:
    expected = {}
    for relation in relations:
        if "target" in relation:
            targets = [(relation["target"], relation["types"])]
        else:
            targets = [(target, relation["relation_groups"][target.lower()]) for target in relation["targets"]]
        for target, types in targets:
            expected[(relation["source"], target)] = (relation["id"], set(types))
    return expected


def main():
    ontology = json.loads((ROOT / "ontology_master_v3_1.json").read_text(encoding="utf-8"))["ontology"]
    expected_counts = {
        "ontology_overview.graphml": (12, 16),
        "ontology_class_hierarchy.graphml": (12, 10),
        "ontology_relations_detailed.graphml": (11, 26),
        "ontology_needs_detailed.graphml": (15, 14),
    }
    loaded = {}
    for name, counts in expected_counts.items():
        loaded[name] = load_graph(name)
        actual = (len(loaded[name][1]), len(loaded[name][2]))
        assert actual == counts, f"unexpected node/edge count in {name}: {actual} != {counts}"
        print(f"OK {name}: {actual[0]} nodes, {actual[1]} edges")

    root, _, edges = loaded["ontology_relations_detailed.graphml"]
    expected = source_relation_edges(ontology["relations_module"]["relations"])
    actual = {}
    for edge in edges:
        label = edge.find(f".//{YED}EdgeLabel").text or ""
        relation_id, type_line = label.split("\n", 1)
        relation_id = relation_id.split(" [", 1)[0]
        actual[(edge.attrib["source"], edge.attrib["target"])] = (relation_id, set(type_line.split(" · ")))
    assert actual == expected, "detailed relation edges or type labels differ from JSON source"

    source_classes = set(ontology["schema_module"]["ontology"]["classes"])
    relation_nodes = {node.attrib["id"] for node in root.findall(f".//{GRAPHML}node")}
    assert relation_nodes == source_classes, "detailed relation class set differs from JSON source"
    print(f"OK source coverage: {len(actual)}/{len(expected)} relation pairs with exact type labels")


if __name__ == "__main__":
    main()
