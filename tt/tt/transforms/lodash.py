"""Transform lodash function calls to Python builtins."""
from __future__ import annotations

from tt.ir import (
    IRModule, IRNode, IRClass, IRMethod, IRFunction, IRAssign, IRAugAssign,
    IRCall, IRAttr, IRName, IRBinOp, IRLiteral, IRReturn, IRIf,
    IRFor, IRForRange, IRWhile, IRExprStatement, IRTernary, IRList, IRDict,
    IRSubscript, IRNullishCoalesce, IRImport, IRArrow, IRUnaryOp, IRSpread,
    IRTry, IRDestructure, IRParam, IRRaw, IRAwait,
)


def transform_lodash(module: IRModule) -> IRModule:
    """Rewrite lodash calls to Python equivalents."""
    had_lodash = any("lodash" in i.module for i in module.imports)
    module.imports = [i for i in module.imports if "lodash" not in i.module]

    if had_lodash:
        already = {i.module for i in module.imports}
        if "copy" not in already:
            module.imports.append(IRImport(module="copy", names=["deepcopy"]))

    module.body = [_visit(n) for n in module.body]
    return module


def _visit(node: IRNode) -> IRNode:
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
    elif isinstance(node, (IRList, IRDict, IRNullishCoalesce)):
        _visit_collection_children(node)
    elif isinstance(node, IRAttr):
        node.obj = _visit(node.obj)
    elif isinstance(node, (IRArrow, IRSpread, IRDestructure, IRAwait)):
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
    """Visit children of arrow, spread, destructure, await nodes."""
    if isinstance(node, IRArrow):
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


def _visit_call(node: IRCall) -> IRNode:
    node.args = [_visit(a) for a in node.args]
    node.func = _visit(node.func)

    if isinstance(node.func, IRName):
        result = _rewrite_lodash_fn(node.func.name, node.args)
        if result is not None:
            return result

    return node


def _rewrite_lodash_fn(name: str, a: list[IRNode]) -> IRNode | None:
    """Rewrite a lodash function call to Python equivalent."""
    if name == "cloneDeep":
        return IRCall(func=IRName("deepcopy"), args=a)

    if name == "sortBy":
        arr = a[0] if a else IRList()
        key_fn = a[1] if len(a) > 1 else None
        if key_fn:
            return IRCall(
                func=IRName("sorted"),
                args=[arr],
                kwargs={"key": key_fn},
            )
        return IRCall(func=IRName("sorted"), args=[arr])

    if name == "sum":
        return IRCall(func=IRName("sum"), args=a)

    if name == "uniq":
        return IRCall(func=IRName("list"), args=[
            IRCall(func=IRName("set"), args=a)
        ])

    if name == "uniqBy":
        arr = a[0] if a else IRList()
        key = a[1] if len(a) > 1 else None
        if key:
            return IRCall(func=IRName("_uniq_by"), args=[arr, key])
        return IRCall(func=IRName("list"), args=[
            IRCall(func=IRName("set"), args=[arr])
        ])

    if name == "isNumber":
        return IRCall(func=IRName("isinstance"), args=[
            a[0] if a else IRLiteral(None),
            IRName("(int, float)"),
        ])

    if name == "isEmpty":
        return IRUnaryOp(op="not", operand=a[0] if a else IRLiteral(None))

    if name == "first":
        arr = a[0] if a else IRList()
        return IRSubscript(obj=arr, index=IRLiteral(0))

    if name == "last":
        arr = a[0] if a else IRList()
        return IRSubscript(obj=arr, index=IRLiteral(-1))

    return None


def _arrow_to_key(node: IRNode) -> str:
    if isinstance(node, IRArrow):
        if node.params:
            return f"lambda {node.params[0].name}"
        return "lambda x"
    if isinstance(node, IRLiteral) and isinstance(node.value, str):
        return f"lambda x: x.get('{node.value}')"
    return "lambda x: x"


def _raw(node: IRNode) -> str:
    if isinstance(node, IRName):
        return node.name
    return "???"
