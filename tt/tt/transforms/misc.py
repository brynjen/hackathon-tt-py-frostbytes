"""Miscellaneous JS → Python transformations."""
from __future__ import annotations

from tt.ir import (
    IRModule, IRNode, IRClass, IRMethod, IRFunction, IRAssign, IRAugAssign,
    IRCall, IRAttr, IRName, IRBinOp, IRLiteral, IRReturn, IRIf, IRNew,
    IRFor, IRForRange, IRWhile, IRExprStatement, IRTernary, IRList, IRDict,
    IRSubscript, IRNullishCoalesce, IRImport, IRArrow, IRUnaryOp, IRSpread,
    IRTry, IRDestructure, IRRaw, IRParam, IRAwait,
)


def transform_misc(module: IRModule) -> IRModule:
    """Apply miscellaneous JS-to-Python rewrites."""
    module.body = [_visit(n) for n in module.body]
    return module


def _visit(node: IRNode) -> IRNode:
    if isinstance(node, IRCall):
        return _visit_call(node)
    if isinstance(node, IRAttr):
        return _visit_attr(node)
    if isinstance(node, IRBinOp):
        return _visit_binop(node)
    if isinstance(node, IRNew):
        return _visit_new(node)

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
    if isinstance(node, IRUnaryOp):
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
    elif isinstance(node, IRNullishCoalesce):
        node.left = _visit(node.left)
        node.right = _visit(node.right)
    elif isinstance(node, IRArrow):
        if isinstance(node.body, list):
            node.body = [_visit(n) for n in node.body]
        else:
            node.body = _visit(node.body)
    elif isinstance(node, IRSpread):
        node.value = _visit(node.value)
    elif isinstance(node, IRTry):
        node.body = [_visit(n) for n in node.body]
        node.handler_body = [_visit(n) for n in node.handler_body]
    elif isinstance(node, IRDestructure):
        node.source = _visit(node.source)
    elif isinstance(node, IRAwait):
        node.value = _visit(node.value)


def _visit_call(node: IRCall) -> IRNode:
    node.args = [_visit(a) for a in node.args]
    node.func = _visit(node.func)

    if isinstance(node.func, IRAttr):
        result = _visit_method_call(node, node.func.obj, node.func.attr)
        if result is not None:
            return result

    if isinstance(node.func, IRName):
        result = _visit_static_call(node, node.func.name)
        if result is not None:
            return result

    return node


def _visit_method_call(node: IRCall, obj: IRNode, method: str) -> IRNode | None:
    """Rewrite method calls on JS built-in objects."""
    if isinstance(obj, IRName):
        result = _visit_builtin_call(node, obj.name, method)
        if result is not None:
            return result

    return _visit_instance_method(node, obj, method)


def _visit_builtin_call(node: IRCall, obj_name: str, method: str) -> IRNode | None:
    """Rewrite static method calls on Object, Array, Math, JSON, console."""
    if obj_name == "Object":
        return _visit_object_call(node, method)

    if obj_name == "Array":
        if method == "from":
            return IRCall(func=IRName("list"), args=node.args)
        if method == "isArray":
            return IRCall(func=IRName("isinstance"), args=[
                node.args[0] if node.args else IRLiteral(None),
                IRName("list"),
            ])

    if obj_name == "Math":
        math_map = {"abs": "abs", "max": "max", "min": "min", "round": "round",
                   "floor": "int", "ceil": "math.ceil", "pow": "pow", "sqrt": "math.sqrt",
                   "log": "math.log"}
        if method in math_map:
            return IRCall(func=IRName(math_map[method]), args=node.args)

    if obj_name == "JSON":
        if method == "parse":
            return IRCall(func=IRAttr(obj=IRName("json"), attr="loads"), args=node.args)
        if method == "stringify":
            return IRCall(func=IRAttr(obj=IRName("json"), attr="dumps"), args=node.args)

    if obj_name == "console":
        if method in ("log", "warn", "error", "info", "debug"):
            return IRCall(func=IRName("print"), args=node.args)

    return None


def _visit_object_call(node: IRCall, method: str) -> IRNode | None:
    """Rewrite Object.keys/values/entries/assign/fromEntries."""
    if method == "keys" and node.args:
        return IRCall(func=IRName("list"), args=[
            IRCall(func=IRAttr(obj=node.args[0], attr="keys"), args=[])
        ])
    if method == "values" and node.args:
        return IRCall(func=IRName("list"), args=[
            IRCall(func=IRAttr(obj=node.args[0], attr="values"), args=[])
        ])
    if method == "entries" and node.args:
        return IRCall(func=IRName("list"), args=[
            IRCall(func=IRAttr(obj=node.args[0], attr="items"), args=[])
        ])
    if method == "assign":
        if len(node.args) >= 2:
            return IRDict(
                keys=[IRSpread(a) for a in node.args],
                values=[IRLiteral(None) for _ in node.args],
            )
    if method == "fromEntries" and node.args:
        return IRCall(func=IRName("dict"), args=node.args)
    return None


def _visit_instance_method(node: IRCall, obj: IRNode, method: str) -> IRNode | None:
    """Rewrite instance method calls (push, includes, map, filter, etc.)."""
    if method == "push":
        return IRCall(func=IRAttr(obj=obj, attr="append"), args=node.args)

    if method == "includes":
        if node.args:
            return IRBinOp(left=node.args[0], op="in", right=obj)

    if method == "indexOf":
        return IRCall(func=IRAttr(obj=obj, attr="index"), args=node.args)

    if method == "splice":
        return IRRaw(code=f"# splice: not directly translatable")

    if method == "join":
        sep = node.args[0] if node.args else IRLiteral("")
        return IRCall(func=IRAttr(obj=sep, attr="join"), args=[obj])

    if method == "slice":
        return _rewrite_slice(node, obj)

    result = _rewrite_iteration_method(node, obj, method)
    if result is not None:
        return result

    return _rewrite_simple_method(node, obj, method)


def _rewrite_slice(node: IRCall, obj: IRNode) -> IRNode | None:
    """Rewrite .slice() calls."""
    if len(node.args) == 1:
        return IRSubscript(obj=obj, index=IRRaw(code=f"{_raw_expr(node.args[0])}:"))
    if len(node.args) == 2:
        return IRSubscript(obj=obj, index=IRRaw(
            code=f"{_raw_expr(node.args[0])}:{_raw_expr(node.args[1])}"
        ))
    return None


def _rewrite_iteration_method(node: IRCall, obj: IRNode, method: str) -> IRNode | None:
    """Rewrite filter/map/find/findIndex/some/every/forEach/reduce."""
    if method == "filter":
        if node.args and isinstance(node.args[0], IRArrow):
            return _arrow_to_listcomp(node.args[0], obj, "filter")

    if method == "map":
        if node.args and isinstance(node.args[0], IRArrow):
            return _arrow_to_listcomp(node.args[0], obj, "map")

    if method in ("find", "findIndex"):
        return _rewrite_find_method(node, obj, method)

    if method == "forEach":
        return IRRaw(code=f"# forEach: use for loop instead")

    if method == "reduce":
        return node

    return _rewrite_predicate_method(node, obj, method)


def _rewrite_find_method(node: IRCall, obj: IRNode, method: str) -> IRNode | None:
    """Rewrite find/findIndex method calls."""
    if not (node.args and isinstance(node.args[0], IRArrow)):
        return None
    arrow = node.args[0]
    param = arrow.params[0].name if arrow.params else "x"
    if method == "find":
        return IRCall(
            func=IRName("next"),
            args=[
                IRRaw(code=f"({param} for {param} in {_raw_expr(obj)} if {_raw_body(arrow)})"),
                IRLiteral(None),
            ],
        )
    if method == "findIndex":
        return IRCall(
            func=IRName("next"),
            args=[
                IRRaw(code=f"(i for i, {param} in enumerate({_raw_expr(obj)}) if {_raw_body(arrow)})"),
                IRLiteral(-1),
            ],
        )
    return None


def _rewrite_predicate_method(node: IRCall, obj: IRNode, method: str) -> IRNode | None:
    """Rewrite some/every method calls."""
    if method == "some":
        if node.args and isinstance(node.args[0], IRArrow):
            arrow = node.args[0]
            param = arrow.params[0].name if arrow.params else "x"
            return IRCall(
                func=IRName("any"),
                args=[IRRaw(code=f"{_raw_body(arrow)} for {param} in {_raw_expr(obj)}")]
            )

    if method == "every":
        if node.args and isinstance(node.args[0], IRArrow):
            arrow = node.args[0]
            param = arrow.params[0].name if arrow.params else "x"
            return IRCall(
                func=IRName("all"),
                args=[IRRaw(code=f"{_raw_body(arrow)} for {param} in {_raw_expr(obj)}")]
            )

    return None


def _rewrite_simple_method(node: IRCall, obj: IRNode, method: str) -> IRNode | None:
    """Rewrite simple method calls (keys, values, entries, toString, etc.)."""
    if method == "keys":
        return IRCall(func=IRAttr(obj=obj, attr="keys"), args=[])

    if method == "values":
        return IRCall(func=IRAttr(obj=obj, attr="values"), args=[])

    if method == "entries":
        return IRCall(func=IRAttr(obj=obj, attr="items"), args=[])

    if method == "toString":
        return IRCall(func=IRName("str"), args=[obj])

    if method == "parseInt":
        return IRCall(func=IRName("int"), args=node.args)

    if method == "parseFloat":
        return IRCall(func=IRName("float"), args=node.args)

    return None


def _visit_static_call(node: IRCall, name: str) -> IRNode | None:
    """Rewrite global function calls (parseInt, String, Number, etc.)."""
    if name == "parseInt":
        return IRCall(func=IRName("int"), args=node.args)

    if name == "parseFloat":
        return IRCall(func=IRName("float"), args=node.args)

    if name == "String":
        return IRCall(func=IRName("str"), args=node.args)

    if name == "Number":
        return IRCall(func=IRName("float"), args=node.args)

    if name == "Boolean":
        return IRCall(func=IRName("bool"), args=node.args)

    if name == "Array" and not node.args:
        return IRList()

    if name == "isNaN":
        return IRRaw(code=f"math.isnan({_raw_expr(node.args[0])})" if node.args else "False")

    return None


def _visit_attr(node: IRAttr) -> IRNode:
    node.obj = _visit(node.obj)

    if node.attr == "length":
        return IRCall(func=IRName("len"), args=[node.obj])

    if isinstance(node.obj, IRName) and node.obj.name == "Number":
        if node.attr == "EPSILON":
            return IRRaw(code="1e-10")
        if node.attr == "MAX_SAFE_INTEGER":
            return IRRaw(code="2**53 - 1")

    if isinstance(node.obj, IRName) and node.obj.name == "Math":
        if node.attr == "PI":
            return IRRaw(code="math.pi")
        if node.attr == "E":
            return IRRaw(code="math.e")

    return node


def _visit_binop(node: IRBinOp) -> IRNode:
    node.left = _visit(node.left)
    node.right = _visit(node.right)

    if node.op == "===":
        node.op = "=="
    elif node.op == "!==":
        node.op = "!="
    elif node.op == "&&":
        node.op = "and"
    elif node.op == "||":
        node.op = "or"

    if node.op == "in" and isinstance(node.left, IRLiteral) and isinstance(node.left.value, str):
        return IRBinOp(left=node.left, op="in", right=node.right)

    return node


def _visit_new(node: IRNew) -> IRNode:
    node.args = [_visit(a) for a in node.args]
    if isinstance(node.cls, IRName):
        if node.cls.name == "Map":
            return IRCall(func=IRName("dict"), args=node.args if node.args else [])
        if node.cls.name == "Set":
            return IRCall(func=IRName("set"), args=node.args if node.args else [])
        if node.cls.name == "Array":
            return IRList(elements=list(node.args))
        if node.cls.name == "RegExp":
            return IRRaw(code=f"re.compile({_raw_expr(node.args[0])})" if node.args else "re.compile('')")
        if node.cls.name == "Error":
            return IRCall(func=IRName("Exception"), args=node.args)
    return node


def _arrow_to_listcomp(arrow: IRArrow, iterable: IRNode, mode: str) -> IRNode:
    param = arrow.params[0].name if arrow.params else "x"
    body = arrow.body
    if isinstance(body, list) and len(body) == 1:
        from tt.ir import IRReturn as _Ret
        if isinstance(body[0], _Ret) and body[0].value:
            body = body[0].value

    if mode == "filter":
        return IRRaw(code=f"[{param} for {param} in {_raw_expr(iterable)} if {_raw_body(arrow)}]")
    else:
        return IRRaw(code=f"[{_raw_body(arrow)} for {param} in {_raw_expr(iterable)}]")


def _raw_expr(node: IRNode) -> str:
    from tt.codegen import _Generator, to_snake
    gen = _Generator()
    return gen._expr(node)


def _raw_body(arrow: IRArrow) -> str:
    from tt.codegen import _Generator
    gen = _Generator()
    body = arrow.body
    if isinstance(body, list):
        if len(body) == 1:
            from tt.ir import IRReturn as _Ret
            if isinstance(body[0], _Ret) and body[0].value:
                return gen._expr(body[0].value)
        return "None"
    return gen._expr(body)
