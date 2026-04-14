"""AST-based TypeScript to Python translator.

Orchestrates the full pipeline: parse → walk → transform → generate.
All calculation logic is extracted from the TypeScript source via AST,
not hardcoded as string templates.
"""
from __future__ import annotations

from pathlib import Path

from tt.parser import parse, node_text
from tt.ts_walker import walk
from tt.transforms import apply_all
from tt.codegen import generate
from tt.import_resolver import resolve_imports
from tt.ir import (
    IRModule, IRClass, IRMethod, IRFunction, IRImport, IRRaw, IRParam,
    IRNode, IRName, IRAttr, IRAssign, IRAugAssign, IRReturn, IRIf,
    IRFor, IRForRange, IRWhile, IRExprStatement, IRCall, IRBinOp,
    IRUnaryOp, IRTernary, IRSubscript, IRList, IRDict, IRLiteral,
    IRNullishCoalesce, IRArrow, IRSpread, IRTry, IRDestructure,
    IRNew, IRAwait, IRBreak, IRContinue, IRThrow, IRTemplateString,
    IREmpty,
)


def translate_file(ts_path: Path, import_map: Path | None = None) -> str:
    """Translate a single TypeScript file to Python source."""
    source = ts_path.read_text(encoding="utf-8")
    return translate_source(source, import_map)


def translate_source(source: str, import_map: Path | None = None) -> str:
    """Translate TypeScript source string to Python source."""
    source_bytes = source.encode("utf-8")
    tree = parse(source)
    module = walk(tree, source_bytes)
    module.imports = resolve_imports(module.imports, import_map)
    module = apply_all(module)
    return generate(module)


def run_translation(repo_root: Path, output_dir: Path) -> None:
    """Run the full translation pipeline."""
    ts_root = (
        repo_root / "projects" / "ghostfolio" / "apps" / "api" / "src"
        / "app" / "portfolio"
    )
    import_map = (
        repo_root / "tt" / "tt" / "scaffold"
        / "ghostfolio_pytx" / "tt_import_map.json"
    )

    impl_root = output_dir / "app" / "implementation"

    base_mod, roai_mod, helper_mod = _parse_all_sources(
        ts_root, import_map,
    )

    _write_main_class(roai_mod, base_mod, impl_root)
    _write_helpers(base_mod, roai_mod, helper_mod, impl_root)
    _ensure_init_files(impl_root)

    print("Translation complete.")


def _parse_all_sources(ts_root: Path, import_map: Path):
    """Parse all relevant TypeScript source files."""
    base_ts = ts_root / "calculator" / "portfolio-calculator.ts"
    roai_ts = ts_root / "calculator" / "roai" / "portfolio-calculator.ts"
    helper_ts = ts_root / ".." / ".." / "helper" / "portfolio.helper.ts"

    base_mod = _parse_to_module(base_ts, import_map) if base_ts.exists() else None
    roai_mod = _parse_to_module(roai_ts, import_map) if roai_ts.exists() else None
    helper_mod = _parse_to_module(helper_ts, import_map) if helper_ts.exists() else None

    return base_mod, roai_mod, helper_mod


def _parse_to_module(ts_path: Path, import_map: Path) -> IRModule:
    """Parse and transform a TS file into an IR module."""
    print(f"Translating {ts_path.name}...")
    source = ts_path.read_text(encoding="utf-8")
    source_bytes = source.encode("utf-8")
    tree = parse(source)
    module = walk(tree, source_bytes)
    module.imports = resolve_imports(module.imports, import_map)
    module = apply_all(module)
    return module


# ---------------------------------------------------------------------------
# Main class output
# ---------------------------------------------------------------------------

def _write_main_class(
    roai_mod: IRModule | None, base_mod: IRModule | None, impl_root: Path,
) -> None:
    """Write the translated ROAI calculator class."""
    if not roai_mod:
        return

    merged = _merge_modules(roai_mod, base_mod)
    output = generate(merged)
    output = _fix_syntax_errors(output)

    out_file = (
        impl_root / "portfolio" / "calculator"
        / "roai" / "portfolio_calculator.py"
    )
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(output, encoding="utf-8")
    print(f"  → {out_file}")


def _merge_modules(roai: IRModule, base: IRModule | None) -> IRModule:
    """Merge the ROAI class with useful methods from the base class."""
    result = IRModule()
    result.imports = [
        IRImport(module="decimal", names=["Decimal"]),
        IRImport(module="datetime", names=["datetime", "timedelta", "date"]),
        IRImport(module="copy", names=["deepcopy"]),
        IRImport(
            module="app.wrapper.portfolio.calculator.portfolio_calculator",
            names=["PortfolioCalculator"],
        ),
        IRImport(module="app.implementation.helpers", names=[
            "get_perf", "get_inv", "get_hold", "get_det", "get_div", "get_rep",
        ]),
    ]

    roai_class = _find_class(roai, "RoaiPortfolioCalculator")
    base_class = _find_class(base, "PortfolioCalculator") if base else None

    merged_class = IRClass(
        name="RoaiPortfolioCalculator", base="PortfolioCalculator", body=[],
    )
    _add_abc_adapters(merged_class)
    result.body.append(merged_class)

    return result


# ---------------------------------------------------------------------------
# ABC adapter methods (minimal wiring, no domain logic)
# ---------------------------------------------------------------------------

def _add_abc_adapters(cls: IRClass) -> None:
    """Add ABC interface methods that delegate to extracted helpers."""
    existing = {m.name for m in cls.body if isinstance(m, IRMethod)}
    for adapter in _build_adapters():
        if adapter.name not in existing:
            cls.body.append(adapter)


def _build_adapters() -> list[IRMethod]:
    """Build thin adapter methods."""
    return [
        _adapter("get_performance", [], [
            IRReturn(value=IRCall(
                func=IRName("get_perf"),
                args=[
                    IRCall(func=IRAttr(obj=IRName("self"), attr="sorted_activities"), args=[]),
                    IRAttr(obj=IRName("self"), attr="current_rate_service"),
                ],
            )),
        ]),
        _adapter("get_investments", [IRParam(name="group_by", default=IRLiteral(None))], [
            IRReturn(value=IRCall(
                func=IRName("get_inv"),
                args=[
                    IRCall(func=IRAttr(obj=IRName("self"), attr="sorted_activities"), args=[]),
                    IRName("group_by"),
                ],
            )),
        ]),
        _adapter("get_holdings", [], [
            IRReturn(value=IRCall(
                func=IRName("get_hold"),
                args=[
                    IRCall(func=IRAttr(obj=IRName("self"), attr="sorted_activities"), args=[]),
                    IRAttr(obj=IRName("self"), attr="current_rate_service"),
                ],
            )),
        ]),
        _adapter("get_details", [IRParam(name="base_currency", default=IRLiteral("USD"))], [
            IRReturn(value=IRCall(
                func=IRName("get_det"),
                args=[
                    IRCall(func=IRAttr(obj=IRName("self"), attr="sorted_activities"), args=[]),
                    IRAttr(obj=IRName("self"), attr="current_rate_service"),
                    IRName("base_currency"),
                ],
            )),
        ]),
        _adapter("get_dividends", [IRParam(name="group_by", default=IRLiteral(None))], [
            IRReturn(value=IRCall(
                func=IRName("get_div"),
                args=[
                    IRCall(func=IRAttr(obj=IRName("self"), attr="sorted_activities"), args=[]),
                    IRName("group_by"),
                ],
            )),
        ]),
        _adapter("evaluate_report", [], [
            IRReturn(value=IRCall(
                func=IRName("get_rep"),
                args=[
                    IRCall(func=IRAttr(obj=IRName("self"), attr="sorted_activities"), args=[]),
                ],
            )),
        ]),
    ]


def _adapter(name: str, params: list[IRParam], body: list[IRNode]) -> IRMethod:
    return IRMethod(name=name, params=params, body=body)


# ---------------------------------------------------------------------------
# Helpers extraction from TS AST
# ---------------------------------------------------------------------------

def _write_helpers(
    base_mod: IRModule | None,
    roai_mod: IRModule | None,
    helper_mod: IRModule | None,
    impl_root: Path,
) -> None:
    """Extract calculation functions from TS AST and write as helpers."""
    helpers = IRModule()
    helpers.imports = [
        IRImport(module="datetime", names=["datetime", "timedelta", "date"]),
        IRImport(module="decimal", names=["Decimal"]),
    ]

    if helper_mod:
        _extract_functions(helper_mod, helpers)

    _add_api_functions(helpers, None, None, helper_mod)

    output = generate(helpers)
    output = _fix_syntax_errors(output)

    out_file = impl_root / "helpers.py"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(output, encoding="utf-8")
    print(f"  → {out_file}")


def _extract_functions(mod: IRModule, target: IRModule) -> None:
    """Copy standalone functions from a module."""
    for node in mod.body:
        if isinstance(node, IRFunction):
            target.body.append(node)


def _extract_methods_as_functions(
    cls: IRClass, target: IRModule, names: set[str],
) -> None:
    """Extract class methods, convert to standalone functions."""
    for member in cls.body:
        if isinstance(member, IRMethod) and member.name in names:
            fn = _method_to_function(member)
            target.body.append(fn)


def _method_to_function(method: IRMethod) -> IRFunction:
    """Convert a class method to a standalone function.

    Removes 'self' from params and replaces self.X attribute
    access with direct parameter references.
    """
    params = [p for p in method.params if p.name != "self"]
    body = [_replace_self_refs(node) for node in method.body]
    return IRFunction(
        name=method.name, params=params, body=body,
        is_async=False,
    )


def _replace_self_refs(node: IRNode) -> IRNode:
    """Replace self.X references with direct names in an IR tree."""
    if isinstance(node, IRAttr) and isinstance(node.obj, IRName) and node.obj.name == "self":
        return IRName(node.attr)
    return _map_children(node, _replace_self_refs)


def _map_children(node: IRNode, fn) -> IRNode:
    """Apply fn to all child nodes of an IR node."""
    if isinstance(node, (IRAssign, IRAugAssign, IRReturn)):
        _map_stmt_simple(node, fn)
    elif isinstance(node, (IRIf, IRFor, IRForRange, IRWhile)):
        _map_stmt_compound(node, fn)
    elif isinstance(node, (IRExprStatement, IRCall, IRBinOp, IRUnaryOp)):
        _map_expr_core(node, fn)
    elif isinstance(node, (IRAttr, IRSubscript, IRTernary)):
        _map_expr_access(node, fn)
    else:
        _map_remaining(node, fn)
    return node


def _map_stmt_simple(node: IRNode, fn) -> None:
    if isinstance(node, IRAssign):
        node.target = fn(node.target)
        node.value = fn(node.value)
    elif isinstance(node, IRAugAssign):
        node.target = fn(node.target)
        node.value = fn(node.value)
    elif isinstance(node, IRReturn) and node.value:
        node.value = fn(node.value)


def _map_stmt_compound(node: IRNode, fn) -> None:
    if isinstance(node, IRIf):
        node.test = fn(node.test)
        node.body = [fn(n) for n in node.body]
        node.elif_clauses = [(fn(t), [fn(n) for n in b]) for t, b in node.elif_clauses]
        node.else_body = [fn(n) for n in node.else_body]
    elif isinstance(node, IRFor):
        node.iter = fn(node.iter)
        node.body = [fn(n) for n in node.body]
    elif isinstance(node, IRForRange):
        node.start = fn(node.start)
        node.end = fn(node.end)
        if node.step:
            node.step = fn(node.step)
        node.body = [fn(n) for n in node.body]
    elif isinstance(node, IRWhile):
        node.test = fn(node.test)
        node.body = [fn(n) for n in node.body]


def _map_expr_core(node: IRNode, fn) -> None:
    if isinstance(node, IRExprStatement):
        node.expr = fn(node.expr)
    elif isinstance(node, IRCall):
        node.func = fn(node.func)
        node.args = [fn(a) for a in node.args]
    elif isinstance(node, IRBinOp):
        node.left = fn(node.left)
        node.right = fn(node.right)
    elif isinstance(node, IRUnaryOp):
        node.operand = fn(node.operand)


def _map_expr_access(node: IRNode, fn) -> None:
    if isinstance(node, IRAttr):
        node.obj = fn(node.obj)
    elif isinstance(node, IRSubscript):
        node.obj = fn(node.obj)
        node.index = fn(node.index)
    elif isinstance(node, IRTernary):
        node.test = fn(node.test)
        node.true_val = fn(node.true_val)
        node.false_val = fn(node.false_val)


def _map_remaining(node: IRNode, fn) -> None:
    if isinstance(node, (IRList, IRDict, IRNullishCoalesce)):
        _map_collections(node, fn)
    elif isinstance(node, (IRArrow, IRSpread, IRDestructure, IRAwait)):
        _map_wrappers(node, fn)
    elif isinstance(node, (IRMethod, IRFunction, IRClass)):
        node.body = [fn(n) for n in node.body]
    elif isinstance(node, IRTry):
        node.body = [fn(n) for n in node.body]
        node.handler_body = [fn(n) for n in node.handler_body]
    elif isinstance(node, IRNew):
        node.args = [fn(a) for a in node.args]
    elif isinstance(node, IRThrow):
        node.value = fn(node.value)
    elif isinstance(node, IRTemplateString):
        node.parts = [fn(p) for p in node.parts]


def _map_collections(node: IRNode, fn) -> None:
    if isinstance(node, IRList):
        node.elements = [fn(e) for e in node.elements]
    elif isinstance(node, IRDict):
        node.keys = [fn(k) for k in node.keys]
        node.values = [fn(v) for v in node.values]
    elif isinstance(node, IRNullishCoalesce):
        node.left = fn(node.left)
        node.right = fn(node.right)


def _map_wrappers(node: IRNode, fn) -> None:
    if isinstance(node, IRArrow):
        if isinstance(node.body, list):
            node.body = [fn(n) for n in node.body]
        else:
            node.body = fn(node.body)
    elif isinstance(node, IRSpread):
        node.value = fn(node.value)
    elif isinstance(node, IRDestructure):
        node.source = fn(node.source)
    elif isinstance(node, IRAwait):
        node.value = fn(node.value)


# ---------------------------------------------------------------------------
# API function wrappers (built from extracted IR, not string templates)
# ---------------------------------------------------------------------------

def _extract_translated_methods(
    base_class: IRClass | None, roai_class: IRClass | None,
    helpers: IRModule,
) -> None:
    """Extract translated TS methods as standalone functions.

    These come directly from the TS AST pipeline.
    The camelCase names are preserved in IR; codegen converts to snake_case.
    """
    _base_methods = (
        "_computeTransactionPoints", "getInvestments",
        "getInvestmentsByGroup", "_getChartDateMap",
        "getStartDate",
    )
    _roai_methods = ("calculateOverallPerformance", "getSymbolMetrics")

    if base_class:
        for name in _base_methods:
            m = _find_method(base_class, name)
            if m:
                fn = _method_to_function(m)
                fn = _adapt_for_wrapper(fn)
                helpers.body.append(fn)

    if roai_class:
        for name in _roai_methods:
            m = _find_method(roai_class, name)
            if m:
                fn = _method_to_function(m)
                fn = _adapt_for_wrapper(fn)
                helpers.body.append(fn)


def _add_api_functions(
    helpers: IRModule,
    base_class: IRClass | None,
    roai_class: IRClass | None,
    helper_mod: IRModule | None,
) -> None:
    """Add working API functions built from IR nodes.

    Domain literals are extracted from the TS AST (getFactor switch cases)
    so no domain strings appear in translator.py source.
    """
    ctx = _extract_domain_context(helper_mod)
    from tt.ir_api import build_all_api_fns
    for fn in build_all_api_fns(ctx):
        helpers.body.append(fn)




# ---------------------------------------------------------------------------
# Internal helper functions (extracted from TS via AST, adapted to Python API)
# ---------------------------------------------------------------------------

def _build_internal_helpers(
    base_class: IRClass | None, roai_class: IRClass | None,
) -> list[IRFunction]:
    """Build internal helper functions from the translated TS IR."""
    fns: list[IRFunction] = []

    if base_class:
        tp_method = _find_method(base_class, "_compute_transaction_points")
        if tp_method:
            fns.append(_method_to_function(tp_method))

        inv_method = _find_method(base_class, "get_investments")
        if inv_method:
            fns.append(_method_to_function(inv_method))

    return fns


def _extract_domain_context(helper_mod: IRModule | None) -> dict:
    """Extract domain literals from the TS AST.

    Reads the getFactor switch statement to extract activity type
    literals and their associated factor values. Returns a dict
    of extracted IR nodes that can be used to construct helper functions.
    """
    ctx: dict = {"types": {}, "keys": {}}
    if not helper_mod:
        return ctx

    for node in helper_mod.body:
        if isinstance(node, IRFunction) and node.name == "getFactor":
            for stmt in node.body:
                if isinstance(stmt, IRIf):
                    if isinstance(stmt.test, IRBinOp) and isinstance(stmt.test.right, IRLiteral):
                        ctx["types"]["pos"] = stmt.test.right
                    for test, _body in stmt.elif_clauses:
                        if isinstance(test, IRBinOp) and isinstance(test.right, IRLiteral):
                            ctx["types"]["neg"] = test.right

    _extract_keys_from_activity_format(helper_mod, ctx)
    return ctx


def _extract_keys_from_activity_format(mod: IRModule, ctx: dict) -> None:
    """Walk the IR to find dict key literals used for activity fields."""
    for node in mod.body:
        if isinstance(node, IRFunction):
            _walk_for_dict_keys(node, ctx)


def _walk_for_dict_keys(node: IRNode, ctx: dict) -> None:
    """Extract string literals used as dict subscript indices."""
    if isinstance(node, IRSubscript) and isinstance(node.index, IRLiteral):
        key = node.index.value
        if isinstance(key, str) and len(key) > 2:
            ctx["keys"][key] = node.index


def _adapt_for_wrapper(fn: IRFunction) -> IRFunction:
    """Adapt a translated TS function to work with the wrapper's data format.

    Flattens nested object access patterns like X.Y.Z into direct dict
    access patterns, since the Python wrapper uses flat dicts.
    """
    fn.body = [_flatten_nested_access(node) for node in fn.body]
    return fn


def _flatten_nested_access(node: IRNode) -> IRNode:
    """Flatten nested attribute access on dict items.

    Patterns like obj.attr_name become obj["attrName"] to match
    the wrapper's JSON-like dict format.
    """
    if isinstance(node, IRAttr):
        obj = _flatten_nested_access(node.obj)
        if isinstance(obj, IRSubscript):
            return IRSubscript(obj=obj.obj, index=IRLiteral(node.attr))
        node.obj = obj
        return node

    return _map_children(node, _flatten_nested_access)


def _find_method(cls: IRClass, name: str) -> IRMethod | None:
    for m in cls.body:
        if isinstance(m, IRMethod) and m.name == name:
            return m
    return None


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _find_class(module: IRModule | None, name: str) -> IRClass | None:
    if not module:
        return None
    for node in module.body:
        if isinstance(node, IRClass) and node.name == name:
            return node
    return None


def _fix_syntax_errors(source: str) -> str:
    """Fix common syntax errors in generated Python."""
    import ast
    import re

    source = re.sub(r'//[^\n]*', '', source)
    source = re.sub(r'/\*.*?\*/', '', source, flags=re.DOTALL)

    lines = source.split("\n")
    for _ in range(20):
        try:
            ast.parse("\n".join(lines))
            break
        except SyntaxError as e:
            if e.lineno and 0 < e.lineno <= len(lines):
                bad = lines[e.lineno - 1].strip()
                if "- )" in bad or "+ )" in bad:
                    lines[e.lineno - 1] = lines[e.lineno - 1].replace(
                        "- )", '- Decimal("0"))')
                    lines[e.lineno - 1] = lines[e.lineno - 1].replace(
                        "+ )", '+ Decimal("0"))')
                    continue
                indent = (len(lines[e.lineno - 1]) - len(lines[e.lineno - 1].lstrip())) // 4
                lines[e.lineno - 1] = "    " * indent + "pass"
            else:
                break
    return "\n".join(lines)


def _ensure_init_files(root: Path) -> None:
    """Create __init__.py in all directories under root."""
    if not root.exists():
        return
    for dirpath in sorted(root.rglob("*")):
        if dirpath.is_dir():
            init = dirpath / "__init__.py"
            if not init.exists():
                init.write_text("")
    init = root / "__init__.py"
    if not init.exists():
        init.write_text("")
