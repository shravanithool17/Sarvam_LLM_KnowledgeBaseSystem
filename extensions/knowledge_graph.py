"""
extensions/knowledge_graph.py — STUB: Knowledge graph generation (v3+)

Future capability:
  Extract entity-relationship triples from document facts and construct a
  property graph (nodes: entities, edges: relationships, properties: citations).
  Export to Neo4j, NetworkX, or a JSON-LD knowledge graph format.
"""


class KnowledgeGraphBuilder:
    """Placeholder — not implemented in v2."""

    def build(self, facts, chunks):
        raise NotImplementedError("KnowledgeGraphBuilder is not yet implemented.")

    def export_json_ld(self):
        raise NotImplementedError("KnowledgeGraphBuilder is not yet implemented.")
