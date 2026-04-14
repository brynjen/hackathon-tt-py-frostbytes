"""Transform Big.js operations to Python Decimal."""
from __future__ import annotations

from tt.ir import (
    IRModule, IRNode, IRClass, IRMethod, IRFunction, IRAssign, IRAugAssign,
    IRCall, IRNew, IRAttr, IRName, IRBinOp, IRLiteral, IRReturn, IRIf,
    IRFor, IRForRange, IRWhile, IRExprStatement, IRTernary, IRList, IRDict,
    IRSubscript, IRNullishCoalesce, IRDestructure, IRImport, IRArrow,
    IRUnaryOp, IRSpread, IRTry, IRThrow, IRAwait, IRTemplateString,
)

_BIG_METHODS = {
    "plus": "+", "add": "+",
    "minus": "-", "sub": "-",
    "mul": "*", "times": "*",
    "div": "/",
    "mod": "%",
}

_BIG_CMP = {
    "gt": ">", "gte": ">=",
    "lt": "<", "lte": "<=",
    "eq": "==",
}


def transform_big_js(module: IRModule) -> IRModule:
    """Rewrite Big.js patterns to Decimal operations."""
    module.imports = [i for i in module.imports if i.module != "big.js"]

    has_big = _scan_for_big(module)
    if has_big:
        module.imports.insert(0, IRImport(module="decimal", names=["Decimal"]))

    module.body = [_visit(n) for n in module.body]
    return module


def _iter_ir_children(node) -> list:
    """Yield all IRNode children from a dataclass node."""
    if not hasattr(node, "__dataclass_fields__"):
        return []
    result = []
    for f in node.__dataclass_fields__:
        val = getattr(node, f)
        if isinstance(val, IRNode):
            result.append(val)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, IRNode):
                    result.append(item)
                elif isinstance(item, (tuple, list)):
                    result.extend(x for x in item if isinstance(x, IRNode))
    return result


def _scan_for_big(node) -> bool:
    """Check if any New(Big) or Big references exist."""
    if isinstance(node, IRNew) and isinstance(node.cls, IRName) and node.cls.name == "Big":
        return True
    if isinstance(node, IRName) and node.name == "Big":
        return True
    return any(_scan_for_big(c) for c in _iter_ir_children(node))


def _visit(node: IRNode) -> IRNode:
    """Recursively rewrite Big.js patterns."""
    if isinstance(node, IRNew):
        if isinstance(node.cls, IRName) and node.cls.name == "Big":
            arg = _visit(node.args[0]) if node.args else IRLiteral(0)
            return _make_decimal(arg)

    if isinstance(node, IRCall):
        return _visit_call(node)

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
    else:
        _visit_expr_children(node)


def _visit_if_children(node: IRIf) -> None:
    """Visit children of an IRIf node."""
    node.test = _visit(node.test)
    node.body = [_visit(n) for n in node.body]
    node.elif_clauses = [(_visit(t), [_visit(n) for n in b]) for t, b in node.elif_clauses]
    node.else_body = [_visit(n) for n in node.else_body]


def _visit_loop_children(node: IRNode) -> None:
    """Visit children of loop nodes (IRFor, IRForRange, IRWhile)."""
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
    elif isinstance(node, (IRList, IRDict, IRNullishCoalesce)):
        _visit_collection_children(node)
    elif isinstance(node, IRAttr):
        node.obj = _visit(node.obj)
    elif isinstance(node, (IRArrow, IRSpread, IRTry, IRThrow, IRDestructure, IRAwait)):
        _visit_remaining_children(node)


def _visit_collection_children(node: IRNode) -> None:
    """Visit children of collection/pair nodes."""
    if isinstance(node, IRList):
        node.elements = [_visit(e) for e in node.elements]
    elif isinstance(node, IRDict):
        node.keys = [_visit(k) for k in node.keys]
        node.values = [_visit(v) for v in node.values]
    elif isinstance(node, IRNullishCoalesce):
        node.left = _visit(node.left)
        node.right = _visit(node.right)


def _visit_remaining_children(node: IRNode) -> None:
    """Visit children of arrow, spread, try, throw, destructure, await nodes."""
    if isinstance(node, IRArrow):
        if isinstance(node.body, list):
            node.body = [_visit(n) for n in node.body]
        else:
            node.body = _visit(node.body)
    elif isinstance(node, IRSpread):
        node.value = _visit(node.value)
    elif isinstance(node, IRTry):
        node.body = [_visit(n) for n in node.body]
        node.handler_body = [_visit(n) for n in node.handler_body]
        node.finally_body = [_visit(n) for n in node.finally_body]
    elif isinstance(node, IRThrow):
        node.value = _visit(node.value)
    elif isinstance(node, IRDestructure):
        node.source = _visit(node.source)
    elif isinstance(node, IRAwait):
        node.value = _visit(node.value)


def _visit_call(node: IRCall) -> IRNode:
    node.args = [_visit(a) for a in node.args]
    node.func = _visit(node.func)

    if isinstance(node.func, IRAttr):
        method = node.func.attr
        obj = node.func.obj

        if method in _BIG_METHODS:
            op = _BIG_METHODS[method]
            right = node.args[0] if node.args else IRLiteral(0)
            return IRBinOp(left=obj, op=op, right=right)

        if method in _BIG_CMP:
            op = _BIG_CMP[method]
            right = node.args[0] if node.args else IRLiteral(0)
            return IRBinOp(left=obj, op=op, right=right)

        if method == "abs":
            return IRCall(func=IRName("abs"), args=[obj])

        if method == "toNumber":
            return IRCall(func=IRName("float"), args=[obj])

        if method == "toFixed":
            n = node.args[0] if node.args else IRLiteral(2)
            return IRCall(func=IRName("round"), args=[obj, n])

        if method == "toString":
            return IRCall(func=IRName("str"), args=[obj])

    if isinstance(node.func, IRName) and node.func.name == "Big":
        arg = node.args[0] if node.args else IRLiteral(0)
        return _make_decimal(arg)

    return node


def _make_decimal(arg: IRNode) -> IRCall:
    """Create Decimal(str(arg)) expression."""
    if isinstance(arg, IRLiteral):
        if isinstance(arg.value, (int, float)):
            return IRCall(func=IRName("Decimal"), args=[IRLiteral(str(arg.value))])
        if isinstance(arg.value, str):
            return IRCall(func=IRName("Decimal"), args=[arg])
    return IRCall(func=IRName("Decimal"), args=[
        IRCall(func=IRName("str"), args=[arg])
    ])
