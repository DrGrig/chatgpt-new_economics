#!/usr/bin/env python3
"""Generate yEd-compatible GraphML views from ontology_master_v3_1.json."""

from __future__ import annotations

import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "visualization"
SOURCE = ROOT / "ontology_master_v3_1.json"

G = "http://graphml.graphdrawing.org/xmlns"
Y = "http://www.yworks.com/xml/graphml"
ET.register_namespace("", G)
ET.register_namespace("y", Y)

COLORS = {
    "base": ("#263238", "#FFFFFF"),
    "core": ("#DDEBFF", "#102A43"),
    "context": ("#DDF5E3", "#173B24"),
    "computed": ("#FFF1C7", "#4B3500"),
    "need": ("#FCE0E6", "#4A1621"),
    "level": ("#E8E1FA", "#2E2255"),
}


def q(ns: str, name: str) -> str:
    return f"{{{ns}}}{name}"


def new_graph(description: str):
    root = ET.Element(q(G, "graphml"), {q("http://www.w3.org/2001/XMLSchema-instance", "schemaLocation"): f"{G} http://www.yworks.com/xml/schema/graphml/1.1/ygraphml.xsd"})
    ET.SubElement(root, q(G, "key"), {"id": "d0", "for": "node", "yfiles.type": "nodegraphics"})
    ET.SubElement(root, q(G, "key"), {"id": "d1", "for": "edge", "yfiles.type": "edgegraphics"})
    ET.SubElement(root, q(G, "key"), {"id": "d2", "for": "graph", "attr.name": "description", "attr.type": "string"})
    graph = ET.SubElement(root, q(G, "graph"), {"id": "G", "edgedefault": "directed"})
    ET.SubElement(graph, q(G, "data"), {"key": "d2"}).text = description
    return root, graph


def add_node(graph, node_id: str, label: str, x: float, y_pos: float, kind="core", width=170, height=56):
    fill, text = COLORS[kind]
    node = ET.SubElement(graph, q(G, "node"), {"id": node_id})
    data = ET.SubElement(node, q(G, "data"), {"key": "d0"})
    shape = ET.SubElement(data, q(Y, "ShapeNode"))
    ET.SubElement(shape, q(Y, "Geometry"), {"height": str(height), "width": str(width), "x": str(x), "y": str(y_pos)})
    ET.SubElement(shape, q(Y, "Fill"), {"color": fill, "transparent": "false"})
    ET.SubElement(shape, q(Y, "BorderStyle"), {"color": "#455A64", "type": "line", "width": "1.5"})
    nl = ET.SubElement(shape, q(Y, "NodeLabel"), {"alignment": "center", "fontFamily": "Dialog", "fontSize": "12", "fontStyle": "plain", "textColor": text, "visible": "true"})
    nl.text = label
    ET.SubElement(shape, q(Y, "Shape"), {"type": "roundrectangle"})


def add_edge(graph, edge_id: str, source: str, target: str, label: str, style="relation"):
    edge = ET.SubElement(graph, q(G, "edge"), {"id": edge_id, "source": source, "target": target})
    data = ET.SubElement(edge, q(G, "data"), {"key": "d1"})
    poly = ET.SubElement(data, q(Y, "PolyLineEdge"))
    ET.SubElement(poly, q(Y, "Path"), {"sx": "0.0", "sy": "0.0", "tx": "0.0", "ty": "0.0"})
    if style == "inheritance":
        color, line, source_arrow, target_arrow = "#546E7A", "line", "none", "white_delta"
    elif style == "classification":
        color, line, source_arrow, target_arrow = "#8E6C00", "dashed", "none", "standard"
    else:
        color, line, source_arrow, target_arrow = "#607D8B", "line", "none", "standard"
    ET.SubElement(poly, q(Y, "LineStyle"), {"color": color, "type": line, "width": "1.2"})
    ET.SubElement(poly, q(Y, "Arrows"), {"source": source_arrow, "target": target_arrow})
    el = ET.SubElement(poly, q(Y, "EdgeLabel"), {"alignment": "center", "backgroundColor": "#FFFFFF", "fontFamily": "Dialog", "fontSize": "9", "fontStyle": "plain", "textColor": "#263238", "visible": "true"})
    el.text = label
    ET.SubElement(poly, q(Y, "BendStyle"), {"smoothed": "false"})


def write(root, filename: str):
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(OUT / filename, encoding="UTF-8", xml_declaration=True)


def class_kind(name: str, architecture: dict) -> str:
    if name == architecture["base_class"]:
        return "base"
    if name in architecture["context_layers"]:
        return "context"
    if name == "Need":
        return "need"
    if name in architecture["computed_classes"]:
        return "computed"
    return "core"


def relation_targets(rel: dict):
    if "target" in rel:
        yield rel["target"], rel.get("types", [])
    else:
        for target in rel["targets"]:
            yield target, rel["relation_groups"][target.lower()]


def overview(data: dict):
    arch = data["architecture"]
    classes = list(data["schema_module"]["ontology"]["classes"]) + arch["computed_classes"]
    root, graph = new_graph("Reality Ontology 3.1 — overview of classes, inheritance, core cycle, and context layers.")
    add_node(graph, "Entity", "Entity\n(base class)", 440, 30, "base", 190, 62)
    for i, name in enumerate(classes[1:]):
        angle = 2 * math.pi * i / (len(classes) - 1)
        x, y_pos = 440 + 390 * math.cos(angle), 330 + 245 * math.sin(angle)
        suffix = "\n(computed class)" if name == "Subject" else ""
        add_node(graph, name, name + suffix, x, y_pos, class_kind(name, arch), 180, 58)
        if name != "Subject":
            add_edge(graph, f"inh_{name}", name, "Entity", "inherits from", "inheritance")
    # These edges are the source-defined core_cycle transitions, not inferred links.
    cycle = arch["core_cycle"]
    by_pair = {(r["source"], t): r for r in data["relations_module"]["relations"] for t, _ in relation_targets(r)}
    for i, (source, target) in enumerate(zip(cycle, cycle[1:])):
        edge_source, edge_target = source, target
        rel = by_pair.get((edge_source, edge_target))
        if rel is None:
            edge_source, edge_target = target, source
            rel = by_pair[(edge_source, edge_target)]
        labels = next(labels for t, labels in relation_targets(rel) if t == edge_target)
        add_edge(graph, f"cycle_{i}", edge_source, edge_target, " / ".join(labels), "relation")
    write(root, "ontology_overview.graphml")


def hierarchy(data: dict):
    arch = data["architecture"]
    classes = data["schema_module"]["ontology"]["classes"]
    root, graph = new_graph("Reality Ontology 3.1 — detailed class hierarchy and source-declared class metadata counts.")
    add_node(graph, "Entity", "Entity\nbase class", 480, 25, "base", 220, 60)
    names = [n for n in classes if n != "Entity"]
    for i, name in enumerate(names):
        col, row = i % 5, i // 5
        c = classes[name]
        label = f"{name}\n{len(c.get('properties', []))} properties · {len(c.get('methods', []))} methods\n{len(c.get('constraints', []))} constraints"
        add_node(graph, name, label, 40 + col * 230, 180 + row * 180, class_kind(name, arch), 205, 78)
        add_edge(graph, f"inh_{name}", name, c["inherits_from"], "inherits from", "inheritance")
    add_node(graph, "Subject", "Subject\ncomputed class\nclassification rule in source", 500, 540, "computed", 220, 78)
    write(root, "ontology_class_hierarchy.graphml")


def relations(data: dict):
    arch = data["architecture"]
    rels = data["relations_module"]["relations"]
    root, graph = new_graph("Reality Ontology 3.1 — all explicitly declared relation groups. Edge labels preserve source relation type names.")
    names = list(data["schema_module"]["ontology"]["classes"])
    for i, name in enumerate(names):
        angle = 2 * math.pi * i / len(names)
        add_node(graph, name, name, 520 + 450 * math.cos(angle), 430 + 340 * math.sin(angle), class_kind(name, arch), 160, 52)
    edge_no = 0
    for rel in rels:
        for target, labels in relation_targets(rel):
            label = f"{rel['id']} [{rel['cardinality']}]\n" + " · ".join(labels)
            add_edge(graph, f"r{edge_no}", rel["source"], target, label)
            edge_no += 1
    write(root, "ontology_relations_detailed.graphml")


def needs(data: dict):
    model = data["needs_matrix_model"]
    levels = model["hierarchy"]["levels"]
    root, graph = new_graph("Reality Ontology 3.1 — declared NeedType → Subcategory → NeedInstance hierarchy and top-level NeedType classes.")
    for i, level in enumerate(levels):
        add_node(graph, level, level, 450, 40 + i * 190, "level", 250, 62)
    add_edge(graph, "h0", levels[0], levels[1], "has subcategory")
    add_edge(graph, "h1", levels[1], levels[2], "has instance")
    types = model["top_level_need_types_v1"]
    for i, name in enumerate(types):
        col, row = i % 4, i // 4
        node_id = f"type_{i}"
        add_node(graph, node_id, name, 20 + col * 255, 665 + row * 105, "need", 230, 55)
        add_edge(graph, f"type_edge_{i}", node_id, "NeedType", "is top-level NeedType", "classification")
    write(root, "ontology_needs_detailed.graphml")


def main():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))["ontology"]
    OUT.mkdir(exist_ok=True)
    overview(data)
    hierarchy(data)
    relations(data)
    needs(data)


if __name__ == "__main__":
    main()
