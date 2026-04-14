"""Tree-sitter based TypeScript parser."""
from __future__ import annotations

import tree_sitter_typescript as ts_typescript
from tree_sitter import Language, Parser, Tree


TS_LANGUAGE = Language(ts_typescript.language_typescript())


def parse(source: str) -> Tree:
    """Parse TypeScript source into a tree-sitter CST."""
    parser = Parser(TS_LANGUAGE)
    return parser.parse(source.encode("utf-8"))


def node_text(node, source_bytes: bytes) -> str:
    """Extract the source text for a tree-sitter node."""
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8")
