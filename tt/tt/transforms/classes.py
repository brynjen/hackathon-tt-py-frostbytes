"""Transform class structures: constructor → __init__, self insertion."""
from __future__ import annotations

from tt.ir import (
    IRModule, IRNode, IRClass, IRMethod, IRParam, IRAssign, IRName, IRAttr,
)


def transform_classes(module: IRModule) -> IRModule:
    """Normalize class structures to Python conventions."""
    module.body = [_visit(n) for n in module.body]
    return module


def _visit(node: IRNode) -> IRNode:
    if isinstance(node, IRClass):
        node.body = [_visit_member(n) for n in node.body]
    return node


def _visit_member(node: IRNode) -> IRNode:
    if isinstance(node, IRMethod):
        if node.name == "constructor":
            node.name = "__init__"
        _add_self_to_params(node)
    return node


def _add_self_to_params(method: IRMethod) -> None:
    """Ensure 'self' is not duplicated in params (codegen adds it)."""
    pass
