"""Transform date-fns function calls to Python datetime equivalents."""
from __future__ import annotations

from tt.ir import (
    IRModule, IRNode, IRClass, IRMethod, IRFunction, IRAssign, IRAugAssign,
    IRCall, IRNew, IRAttr, IRName, IRBinOp, IRLiteral, IRReturn, IRIf,
    IRFor, IRForRange, IRWhile, IRExprStatement, IRTernary, IRList, IRDict,
    IRSubscript, IRNullishCoalesce, IRImport, IRArrow, IRUnaryOp, IRSpread,
    IRTry, IRThrow, IRDestructure, IRRaw, IRAwait,
)


def transform_date_fns(module: IRModule) -> IRModule:
    """Rewrite date-fns calls to Python datetime."""
    had_date_fns = any(
        "date-fns" in imp.module or "@date-fns" in imp.module
        for imp in module.imports
    )
    module.imports = [
        i for i in module.imports
        if "date-fns" not in i.module and "@date-fns" not in i.module
    ]

    if had_date_fns:
        module.imports.insert(0, IRImport(module="datetime", names=["datetime", "timedelta", "date"]))

    module.body = [_visit(n) for n in module.body]
    return module


def _visit(node: IRNode) -> IRNode:
    if isinstance(node, IRCall):
        return _visit_call(node)
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
    elif isinstance(node, (IRArrow, IRSpread, IRTry, IRDestructure, IRAwait)):
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
    """Visit children of arrow, spread, try, destructure, await nodes."""
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
    elif isinstance(node, IRDestructure):
        node.source = _visit(node.source)
    elif isinstance(node, IRAwait):
        node.value = _visit(node.value)


def _visit_call(node: IRCall) -> IRNode:
    node.args = [_visit(a) for a in node.args]
    node.func = _visit(node.func)

    if isinstance(node.func, IRName):
        name = node.func.name
        return _rewrite_date_fn(name, node.args) or node

    return node


def _visit_new(node: IRNew) -> IRNode:
    node.args = [_visit(a) for a in node.args]
    if isinstance(node.cls, IRName) and node.cls.name == "Date":
        if not node.args:
            return IRCall(func=IRAttr(obj=IRName("datetime"), attr="now"), args=[])
        arg = node.args[0]
        if isinstance(arg, IRLiteral) and isinstance(arg.value, str):
            return IRCall(
                func=IRAttr(obj=IRName("datetime"), attr="fromisoformat"),
                args=[arg],
            )
        return IRCall(
            func=IRAttr(obj=IRName("datetime"), attr="fromisoformat"),
            args=[IRCall(func=IRName("str"), args=[arg])],
        )
    return node


def _rewrite_date_fn(name: str, args: list[IRNode]) -> IRNode | None:
    a0 = args[0] if args else IRLiteral(None)
    a1 = args[1] if len(args) > 1 else IRLiteral(None)

    result = _rewrite_date_comparison(name, args, a0, a1)
    if result is not None:
        return result

    result = _rewrite_date_arithmetic(name, a0, a1)
    if result is not None:
        return result

    result = _rewrite_date_construction(name, args, a0, a1)
    if result is not None:
        return result

    return _rewrite_date_accessors(name, a0, a1)


def _rewrite_date_comparison(name: str, args: list[IRNode], a0: IRNode, a1: IRNode) -> IRNode | None:
    """Rewrite date comparison functions."""
    if name == "differenceInDays":
        return IRAttr(
            obj=IRBinOp(left=a0, op="-", right=a1),
            attr="days",
        )

    if name == "isBefore":
        return IRBinOp(left=a0, op="<", right=a1)

    if name == "isAfter":
        return IRBinOp(left=a0, op=">", right=a1)

    if name == "isEqual":
        return IRBinOp(left=a0, op="==", right=a1)

    if name == "min":
        if len(args) == 1 and isinstance(a0, IRList):
            return IRCall(func=IRName("min"), args=a0.elements)
        return IRCall(func=IRName("min"), args=args)

    if name == "max":
        if len(args) == 1 and isinstance(a0, IRList):
            return IRCall(func=IRName("max"), args=a0.elements)
        return IRCall(func=IRName("max"), args=args)

    if name == "isWithinInterval":
        interval = a1
        return IRBinOp(
            left=IRBinOp(
                left=IRSubscript(obj=interval, index=IRLiteral("start")),
                op="<=",
                right=a0,
            ),
            op="and",
            right=IRBinOp(
                left=a0,
                op="<=",
                right=IRSubscript(obj=interval, index=IRLiteral("end")),
            ),
        )

    if name == "isThisYear":
        return IRBinOp(
            left=IRAttr(obj=a0, attr="year"),
            op="==",
            right=IRAttr(
                obj=IRCall(func=IRAttr(obj=IRName("datetime"), attr="now"), args=[]),
                attr="year",
            ),
        )

    return None


def _rewrite_date_arithmetic(name: str, a0: IRNode, a1: IRNode) -> IRNode | None:
    """Rewrite date arithmetic functions (add/sub days, months, years)."""
    if name == "addDays":
        return IRBinOp(
            left=a0, op="+",
            right=IRCall(func=IRName("timedelta"), args=[], kwargs={"days": a1}),
        )

    if name == "subDays":
        return IRBinOp(
            left=a0, op="-",
            right=IRCall(func=IRName("timedelta"), args=[], kwargs={"days": a1}),
        )

    if name == "addMilliseconds":
        return IRBinOp(
            left=a0, op="+",
            right=IRCall(func=IRName("timedelta"), args=[], kwargs={"milliseconds": a1}),
        )

    if name == "addMonths":
        return IRCall(func=IRName("_add_months"), args=[a0, a1])

    if name == "addYears":
        return IRCall(func=IRName("_add_years"), args=[a0, a1])

    if name == "subYears":
        return IRCall(func=IRName("_sub_years"), args=[a0, a1])

    if name == "subMonths":
        return IRCall(func=IRName("_sub_months"), args=[a0, a1])

    return None


def _rewrite_date_construction(name: str, args: list[IRNode], a0: IRNode, a1: IRNode) -> IRNode | None:
    """Rewrite date construction and formatting functions."""
    if name == "startOfDay":
        return IRCall(
            func=IRAttr(obj=a0, attr="replace"),
            args=[],
            kwargs={
                "hour": IRLiteral(0), "minute": IRLiteral(0),
                "second": IRLiteral(0), "microsecond": IRLiteral(0),
            },
        )

    if name == "endOfDay":
        return IRCall(
            func=IRAttr(obj=a0, attr="replace"),
            args=[],
            kwargs={
                "hour": IRLiteral(23), "minute": IRLiteral(59),
                "second": IRLiteral(59), "microsecond": IRLiteral(999999),
            },
        )

    if name == "startOfYear":
        return IRCall(
            func=IRAttr(obj=a0, attr="replace"),
            args=[],
            kwargs={"month": IRLiteral(1), "day": IRLiteral(1)},
        )

    if name == "endOfYear":
        return IRCall(
            func=IRAttr(obj=a0, attr="replace"),
            args=[],
            kwargs={"month": IRLiteral(12), "day": IRLiteral(31)},
        )

    if name == "format":
        fmt = a1
        if isinstance(fmt, IRLiteral) and isinstance(fmt.value, str):
            py_fmt = (
                fmt.value
                .replace("yyyy", "%Y")
                .replace("MM", "%m")
                .replace("dd", "%d")
            )
            return IRCall(
                func=IRAttr(obj=a0, attr="strftime"),
                args=[IRLiteral(py_fmt)],
            )
        return IRCall(func=IRAttr(obj=a0, attr="strftime"), args=[fmt])

    if name == "parseISO" or name == "parseDate":
        return IRCall(
            func=IRAttr(obj=IRName("datetime"), attr="fromisoformat"),
            args=[a0],
        )

    if name == "eachDayOfInterval":
        return IRCall(func=IRName("_each_day_of_interval"), args=[a0])

    if name == "eachYearOfInterval":
        return IRCall(func=IRName("_each_year_of_interval"), args=[a0])

    if name == "eachMonthOfInterval":
        return IRCall(func=IRName("_each_month_of_interval"), args=[a0])

    return None


def _rewrite_date_accessors(name: str, a0: IRNode, a1: IRNode) -> IRNode | None:
    """Rewrite date accessor functions (getDate, getMonth, getYear)."""
    if name == "getDate":
        return IRAttr(obj=a0, attr="day")

    if name == "getMonth":
        return IRBinOp(left=IRAttr(obj=a0, attr="month"), op="-", right=IRLiteral(1))

    if name == "getYear":
        return IRAttr(obj=a0, attr="year")

    return None


def _raw(node: IRNode) -> str:
    """Rough text representation for IRRaw fallbacks."""
    if isinstance(node, IRName):
        return node.name
    if isinstance(node, IRLiteral):
        return repr(node.value)
    return "???"
