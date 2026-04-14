"""Transform optional chaining (?.) and nullish coalescing (??) to Python."""
from __future__ import annotations

from tt.ir import (
    IRModule, IRNode, IRClass, IRMethod, IRFunction, IRAssign, IRAugAssign,
    IRCall, IRAttr, IRName, IRBinOp, IRLiteral, IRReturn, IRIf,
    IRFor, IRForRange, IRWhile, IRExprStatement, IRTernary, IRList, IRDict,
    IRSubscript, IRNullishCoalesce, IRArrow, IRUnaryOp, IRSpread,
    IRTry, IRDestructure, IRAwait,
)


def transform_optional_chaining(module: IRModule) -> IRModule:
    """Rewrite ?. and ?? patterns to Python equivalents."""
    module.body = [_visit(n) for n in module.body]
    return module


def _visit(node: IRNode) -> IRNode:
    if isinstance(node, IRNullishCoalesce):
        node.left = _visit(node.left)
        node.right = _visit(node.right)
        return node

    _visit_children(node)
    return node


def _visit_children(node: IRNode) -> None:
    """Recursively visit child nodes in-place."""
    if isinstance(node, IRClass):
        node.body = [_visit(n) for n in node.body]
    elif isinstance(node, (IRMethod, IRFunction)):
        node.body = [_visit(n) for n in node.body]
    elif isinstance(node, IRAssign):
        node.target = _visit(node.target)
        node.value = _visit(node.value)
    elif isinstance(node, IRAugAssign):
        node.target = _visit(node.target)
        node.value = _visit(node.value)
    elif isinstance(node, IRReturn):
        if node.value:
            node.value = _visit(node.value)
    elif isinstance(node, IRIf):
        _visit_if_children(node)
    elif isinstance(node, (IRFor, IRForRange, IRWhile)):
        _visit_loop_children(node)
    elif isinstance(node, IRExprStatement):
        node.expr = _visit(node.expr)
    elif isinstance(node, IRCall):
        node.func = _visit(node.func)
        node.args = [_visit(a) for a in node.args]
    else:
        _visit_expr_children(node)


def _visit_if_children(node: IRIf) -> None:
    """Visit children of an IRIf node."""
    node.test = _visit(node.test)
    node.body = [_visit(n) for n in node.body]
    node.elif_clauses = [(_visit(t), [_visit(n) for n in b]) for t, b in node.elif_clauses]
    node.else_body = [_visit(n) for n in node.else_body]


def _visit_loop_children(node: IRNode) -> None:
    """Visit children of loop nodes."""
    if isinstance(node, IRFor):
        node.iter = _visit(node.iter)
        node.body = [_visit(n) for n in node.body]
    elif isinstance(node, IRForRange):
        node.start = _visit(node.start)
        node.end = _visit(node.end)
        if node.step:
            node.step = _visit(node.step)
        node.body = [_visit(n) for n in node.body]
    elif isinstance(node, IRWhile):
        node.test = _visit(node.test)
        node.body = [_visit(n) for n in node.body]


def _visit_expr_children(node: IRNode) -> None:
    """Visit children of expression-level nodes."""
    if isinstance(node, IRBinOp):
        node.left = _visit(node.left)
        node.right = _visit(node.right)
    elif isinstance(node, IRUnaryOp):
        node.operand = _visit(node.operand)
    elif isinstance(node, IRTernary):
        node.test = _visit(node.test)
        node.true_val = _visit(node.true_val)
        node.false_val = _visit(node.false_val)
    elif isinstance(node, IRSubscript):
        node.obj = _visit(node.obj)
        node.index = _visit(node.index)
    elif isinstance(node, IRList):
        node.elements = [_visit(e) for e in node.elements]
    elif isinstance(node, IRDict):
        node.keys = [_visit(k) for k in node.keys]
        node.values = [_visit(v) for v in node.values]
    elif isinstance(node, IRAttr):
        node.obj = _visit(node.obj)
    elif isinstance(node, IRArrow):
        if isinstance(node.body, list):
            node.body = [_visit(n) for n in node.body]
        else:
            node.body = _visit(node.body)
    elif isinstance(node, IRSpread):
        node.value = _visit(node.value)
    elif isinstance(node, IRDestructure):
        node.source = _visit(node.source)
    elif isinstance(node, IRAwait):
        node.value = _visit(node.value)
