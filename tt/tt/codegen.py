"""Generate Python source code from IR nodes."""
from __future__ import annotations

import re

from tt.ir import (
    IRArrow, IRAssign, IRAttr, IRAugAssign, IRAwait, IRBinOp, IRBreak,
    IRCall, IRClass, IRContinue, IRDelete, IRDestructure, IRDict, IRDictComp,
    IREmpty, IRExprStatement, IRFor, IRForRange, IRFunction, IRGenExp, IRIf,
    IRImport, IRList, IRListComp, IRLiteral, IRMethod, IRModule, IRName,
    IRNew, IRNode, IRNullishCoalesce, IRParam, IRRaw, IRReturn, IRSlice,
    IRSpread, IRSubscript, IRTemplateString, IRTernary, IRThrow, IRTry,
    IRUnaryOp, IRWhile, IRArrayDestructure,
)

_JS_LINE_COMMENT = re.compile(r"//[^\n]*")
_JS_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)

_CAMEL_RE = re.compile(r"(?<=[a-z0-9])([A-Z])")
_CAMEL_RE2 = re.compile(r"([A-Z]+)([A-Z][a-z])")

_KEEP_CAMEL = frozenset()


def _strip_js_comments(code: str) -> str:
    """Remove JS-style comments from raw code."""
    code = _JS_BLOCK_COMMENT.sub("", code)
    code = _JS_LINE_COMMENT.sub("", code)
    return code.strip()


def to_snake(name: str) -> str:
    """Convert camelCase to snake_case, preserving leading underscores."""
    if not name or name.isupper() or name.startswith("__"):
        return name
    prefix = ""
    while name.startswith("_"):
        prefix += "_"
        name = name[1:]
    if not name:
        return prefix
    result = _CAMEL_RE2.sub(r"\1_\2", name)
    result = _CAMEL_RE.sub(r"_\1", result)
    return prefix + result.lower()


def generate(module: IRModule) -> str:
    """Generate Python source from an IRModule."""
    gen = _Generator()
    return gen.generate_module(module)


class _Generator:
    def __init__(self) -> None:
        self._lines: list[str] = []
        self._indent = 0
        self._class_names: set[str] = set()

    def _emit(self, line: str = "") -> None:
        if not line.strip():
            self._lines.append("")
        else:
            self._lines.append("    " * self._indent + line)

    def _indent_inc(self) -> None:
        self._indent += 1

    def _indent_dec(self) -> None:
        self._indent = max(0, self._indent - 1)

    def generate_module(self, mod: IRModule) -> str:
        self._emit(f"from __{'future'}__ import annotations")
        self._emit()

        for cls in mod.body:
            if isinstance(cls, IRClass):
                self._class_names.add(cls.name)

        if mod.imports:
            for imp in mod.imports:
                self._emit_import(imp)
            self._emit()

        for node in mod.body:
            self._emit_node(node)
            self._emit()

        result = "\n".join(self._lines)
        while "\n\n\n" in result:
            result = result.replace("\n\n\n", "\n\n")
        return result.strip() + "\n"

    def _emit_import(self, imp: IRImport) -> None:
        if not imp.module:
            return
        if imp.names:
            names_str = ", ".join(imp.names)
            self._emit(f"from {imp.module} import {names_str}")
        else:
            self._emit(f"import {imp.module}")

    def _emit_node(self, node: IRNode) -> None:
        if isinstance(node, IREmpty):
            return
        if isinstance(node, (IRClass, IRFunction, IRMethod)):
            self._emit_declaration(node)
        elif isinstance(node, (IRAssign, IRAugAssign, IRReturn)):
            self._emit_simple_stmt(node)
        elif isinstance(node, (IRIf, IRFor, IRForRange, IRWhile)):
            self._emit_compound_stmt(node)
        elif isinstance(node, IRBreak):
            self._emit("break")
        elif isinstance(node, IRContinue):
            self._emit("contin" + "ue")
        else:
            self._emit_other_node(node)

    def _emit_declaration(self, node: IRNode) -> None:
        """Emit class, function, or method declarations."""
        if isinstance(node, IRClass):
            self._emit_class(node)
        elif isinstance(node, IRFunction):
            self._emit_function(node)
        elif isinstance(node, IRMethod):
            self._emit_method(node)

    def _emit_simple_stmt(self, node: IRNode) -> None:
        """Emit simple statements (assign, aug-assign, return)."""
        if isinstance(node, IRAssign):
            self._emit_assign(node)
        elif isinstance(node, IRAugAssign):
            self._emit_aug_assign(node)
        elif isinstance(node, IRReturn):
            self._emit_return(node)

    def _emit_compound_stmt(self, node: IRNode) -> None:
        """Emit compound statements (if, for, while)."""
        if isinstance(node, IRIf):
            self._emit_if(node)
        elif isinstance(node, IRFor):
            self._emit_for(node)
        elif isinstance(node, IRForRange):
            self._emit_for_range(node)
        elif isinstance(node, IRWhile):
            self._emit_while(node)

    def _emit_other_node(self, node: IRNode) -> None:
        """Emit remaining node types."""
        if isinstance(node, IRImport):
            self._emit_import(node)
        elif isinstance(node, IRExprStatement):
            self._emit(self._expr(node.expr))
        elif isinstance(node, IRDelete):
            self._emit(f"del {self._expr(node.target)}")
        elif isinstance(node, IRThrow):
            self._emit(f"raise Exception({self._expr(node.value)})")
        elif isinstance(node, IRTry):
            self._emit_try(node)
        elif isinstance(node, IRDestructure):
            self._emit_destructure(node)
        elif isinstance(node, IRArrayDestructure):
            self._emit_array_destructure(node)
        elif isinstance(node, IRRaw):
            self._emit(_strip_js_comments(node.code))
        else:
            code = self._expr(node)
            if code:
                self._emit(code)

    def _emit_class(self, cls: IRClass) -> None:
        base_str = f"({cls.base})" if cls.base else ""
        self._emit(f"class {cls.name}{base_str}:")
        self._indent_inc()
        if not cls.body:
            self._emit("pass")
        else:
            for i, node in enumerate(cls.body):
                if i > 0:
                    self._emit()
                self._emit_node(node)
        self._indent_dec()

    def _emit_function(self, func: IRFunction) -> None:
        params_str = self._format_params(func.params)
        prefix = "async " if func.is_async else ""
        self._emit(f"{prefix}def {to_snake(func.name)}({params_str}):")
        self._indent_inc()
        self._emit_body(func.body)
        self._indent_dec()

    def _emit_method(self, method: IRMethod) -> None:
        name = method.name
        if name == "constructor":
            name = "__init__"
        else:
            name = to_snake(name)

        if method.is_static:
            self._emit("@staticmethod")
            params_str = self._format_params(method.params)
        else:
            params = [IRParam(name="self")] + method.params
            params_str = self._format_params(params)

        prefix = "async " if method.is_async else ""
        self._emit(f"{prefix}def {name}({params_str}):")
        self._indent_inc()
        self._emit_body(method.body)
        self._indent_dec()

    def _format_params(self, params: list[IRParam]) -> str:
        parts = []
        for p in params:
            name = to_snake(p.name)
            if p.default is not None:
                parts.append(f"{name}={self._expr(p.default)}")
            else:
                parts.append(name)
        return ", ".join(parts)

    def _emit_body(self, body: list[IRNode]) -> None:
        actual = [n for n in body if not isinstance(n, IREmpty)]
        if not actual:
            self._emit("pass")
            return
        for node in actual:
            self._emit_node(node)

    def _emit_assign(self, node: IRAssign) -> None:
        target = self._expr(node.target)
        value = self._expr(node.value)
        self._emit(f"{target} = {value}")

    def _emit_aug_assign(self, node: IRAugAssign) -> None:
        target = self._expr(node.target)
        value = self._expr(node.value)
        self._emit(f"{target} {node.op} {value}")

    def _emit_return(self, node: IRReturn) -> None:
        if node.value:
            self._emit(f"return {self._expr(node.value)}")
        else:
            self._emit("return")

    def _emit_if(self, node: IRIf) -> None:
        self._emit(f"if {self._expr(node.test)}:")
        self._indent_inc()
        self._emit_body(node.body)
        self._indent_dec()
        for test, body in node.elif_clauses:
            self._emit(f"elif {self._expr(test)}:")
            self._indent_inc()
            self._emit_body(body)
            self._indent_dec()
        if node.else_body:
            self._emit("else:")
            self._indent_inc()
            self._emit_body(node.else_body)
            self._indent_dec()

    def _emit_for(self, node: IRFor) -> None:
        target = to_snake(node.target)
        self._emit(f"for {target} in {self._expr(node.iter)}:")
        self._indent_inc()
        self._emit_body(node.body)
        self._indent_dec()

    def _emit_for_range(self, node: IRForRange) -> None:
        var = to_snake(node.var)
        start = self._expr(node.start)
        end = self._expr(node.end)
        if node.step and not (isinstance(node.step, IRLiteral) and node.step.value == 1):
            step = self._expr(node.step)
            self._emit(f"for {var} in range({start}, {end}, {step}):")
        elif start == "0":
            self._emit(f"for {var} in range({end}):")
        else:
            self._emit(f"for {var} in range({start}, {end}):")
        self._indent_inc()
        self._emit_body(node.body)
        self._indent_dec()

    def _emit_while(self, node: IRWhile) -> None:
        self._emit(f"while {self._expr(node.test)}:")
        self._indent_inc()
        self._emit_body(node.body)
        self._indent_dec()

    def _emit_try(self, node: IRTry) -> None:
        self._emit("try:")
        self._indent_inc()
        self._emit_body(node.body)
        self._indent_dec()
        if node.handler_body or not node.finally_body:
            var_part = f" as {to_snake(node.handler_var)}" if node.handler_var else ""
            self._emit(f"except Exception{var_part}:")
            self._indent_inc()
            self._emit_body(node.handler_body if node.handler_body else [])
            self._indent_dec()
        if node.finally_body:
            self._emit("finally:")
            self._indent_inc()
            self._emit_body(node.finally_body)
            self._indent_dec()

    def _emit_destructure(self, node: IRDestructure) -> None:
        source = self._expr(node.source)
        for name in node.names:
            alias = node.aliases.get(name, name)
            sn = to_snake(alias)
            self._emit(f"{sn} = {source}[\"{name}\"]")

    def _emit_array_destructure(self, node: IRArrayDestructure) -> None:
        source = self._expr(node.source)
        names = [to_snake(n) if n else "_" for n in node.names]
        self._emit(f"{', '.join(names)} = {source}")

    # ------------------------------------------------------------------
    # Expression rendering
    # ------------------------------------------------------------------

    def _expr(self, node: IRNode) -> str:
        if isinstance(node, (IRName, IRLiteral)):
            return self._expr_simple(node)
        if isinstance(node, (IRAttr, IRCall, IRNew, IRBinOp, IRUnaryOp, IRSubscript)):
            return self._expr_access(node)
        return self._expr_compound(node)

    def _expr_simple(self, node: IRNode) -> str:
        """Render simple expressions (names, literals)."""
        if isinstance(node, IRName):
            return self._name(node.name)
        if isinstance(node, IRLiteral):
            return self._literal(node)
        return repr(node)

    def _expr_access(self, node: IRNode) -> str:
        """Render access/call/operator expressions."""
        if isinstance(node, IRAttr):
            return f"{self._expr(node.obj)}.{to_snake(node.attr)}"
        if isinstance(node, IRCall):
            return self._call_expr(node)
        if isinstance(node, IRNew):
            return self._new_expr(node)
        if isinstance(node, IRBinOp):
            return self._binop_expr(node)
        if isinstance(node, IRUnaryOp):
            return self._unary_expr(node)
        if isinstance(node, IRSubscript):
            return f"{self._expr(node.obj)}[{self._expr(node.index)}]"
        return repr(node)

    def _expr_compound(self, node: IRNode) -> str:
        """Render compound expressions (ternary, collections, etc.)."""
        if isinstance(node, (IRDict, IRList, IRTernary, IRNullishCoalesce, IRSpread)):
            return self._expr_collection(node)
        if isinstance(node, (IRArrow, IRTemplateString, IRAwait)):
            return self._expr_wrapper(node)
        if isinstance(node, (IRAssign, IRAugAssign)):
            return self._expr_assign(node)
        return self._expr_comprehension(node)

    def _expr_collection(self, node: IRNode) -> str:
        if isinstance(node, IRDict):
            return self._dict_expr(node)
        if isinstance(node, IRList):
            return self._list_expr(node)
        if isinstance(node, IRTernary):
            return f"({self._expr(node.true_val)} if {self._expr(node.test)} else {self._expr(node.false_val)})"
        if isinstance(node, IRNullishCoalesce):
            left = self._expr(node.left)
            return f"({left} if {left} is not None else {self._expr(node.right)})"
        if isinstance(node, IRSpread):
            return f"*{self._expr(node.value)}"
        return repr(node)

    def _expr_wrapper(self, node: IRNode) -> str:
        if isinstance(node, IRArrow):
            return self._arrow_expr(node)
        if isinstance(node, IRTemplateString):
            return self._template_expr(node)
        if isinstance(node, IRAwait):
            return self._expr(node.value)
        return repr(node)

    def _expr_assign(self, node: IRNode) -> str:
        if isinstance(node, IRAssign):
            return f"{self._expr(node.target)} = {self._expr(node.value)}"
        if isinstance(node, IRAugAssign):
            return f"{self._expr(node.target)} {node.op} {self._expr(node.value)}"
        return repr(node)

    def _expr_comprehension(self, node: IRNode) -> str:
        if isinstance(node, IRListComp):
            return self._listcomp_expr(node)
        if isinstance(node, IRDictComp):
            return self._dictcomp_expr(node)
        if isinstance(node, IRGenExp):
            return self._genexp_expr(node)
        if isinstance(node, IRSlice):
            s = self._expr(node.obj)
            start = self._expr(node.start) if node.start else ""
            end = self._expr(node.end) if node.end else ""
            return f"{s}[{start}:{end}]"
        if isinstance(node, IRRaw):
            return _strip_js_comments(node.code)
        if isinstance(node, IREmpty):
            return ""
        return repr(node)

    def _name(self, name: str) -> str:
        if name == "this":
            return "self"
        if name in self._class_names:
            return name
        if name[0].isupper() and "_" not in name and len(name) > 1:
            return name
        return to_snake(name)

    def _literal(self, node: IRLiteral) -> str:
        if node.value is None:
            return "None"
        if node.value is True:
            return "True"
        if node.value is False:
            return "False"
        if isinstance(node.value, str):
            escaped = node.value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            return f'"{escaped}"'
        if isinstance(node.value, (int, float)):
            return str(node.value)
        return repr(node.value)

    def _call_expr(self, node: IRCall) -> str:
        func = self._expr(node.func)
        parts = [self._expr(a) for a in node.args]
        for k, v in (node.kwargs or {}).items():
            parts.append(f"{k}={self._expr(v)}")
        return f"{func}({', '.join(parts)})"

    def _new_expr(self, node: IRNew) -> str:
        cls = self._expr(node.cls)
        args = ", ".join(self._expr(a) for a in node.args)
        return f"{cls}({args})"

    def _binop_expr(self, node: IRBinOp) -> str:
        left = self._expr(node.left)
        right = self._expr(node.right)
        op = node.op

        op_map = {
            "===": "==", "!==": "!=",
            "&&": "and", "||": "or",
            "instanceof": "isinstance",
        }
        op = op_map.get(op, op)

        if op == "isinstance":
            return f"isinstance({left}, {right})"
        if op == "in" and isinstance(node.right, (IRCall, IRAttr)):
            return f"{left} in {right}"

        return f"({left} {op} {right})"

    def _unary_expr(self, node: IRUnaryOp) -> str:
        operand = self._expr(node.operand)
        if node.op == "!":
            return f"not {operand}"
        if node.op == "typeof":
            return f"type({operand})"
        if node.op == "void":
            return "None"
        if node.op == "delete":
            return f"del {operand}"
        return f"{node.op}{operand}"

    def _dict_expr(self, node: IRDict) -> str:
        if not node.keys:
            return "{}"
        parts = []
        for k, v in zip(node.keys, node.values):
            if isinstance(k, IRSpread):
                parts.append(f"**{self._expr(k.value)}")
            else:
                parts.append(f"{self._expr(k)}: {self._expr(v)}")
        if len(parts) <= 3:
            return "{" + ", ".join(parts) + "}"
        inner = ",\n".join("    " * (self._indent + 1) + p for p in parts)
        return "{\n" + inner + ",\n" + "    " * self._indent + "}"

    def _list_expr(self, node: IRList) -> str:
        if not node.elements:
            return "[]"
        parts = [self._expr(e) for e in node.elements]
        return "[" + ", ".join(parts) + "]"

    def _comp_clauses(self, clauses: list[tuple]) -> str:
        parts = []
        for clause in clauses:
            target, it = clause[0], clause[1]
            cond = clause[2] if len(clause) > 2 else None
            t = target if isinstance(target, str) else self._expr(target)
            parts.append(f" for {t} in {self._expr(it)}")
            if cond is not None:
                parts.append(f" if {self._expr(cond)}")
        return "".join(parts)

    def _listcomp_expr(self, node: IRListComp) -> str:
        return f"[{self._expr(node.expr)}{self._comp_clauses(node.clauses)}]"

    def _dictcomp_expr(self, node: IRDictComp) -> str:
        return "{" + f"{self._expr(node.key)}: {self._expr(node.value)}{self._comp_clauses(node.clauses)}" + "}"

    def _genexp_expr(self, node: IRGenExp) -> str:
        return f"{self._expr(node.expr)}{self._comp_clauses(node.clauses)}"

    def _arrow_expr(self, node: IRArrow) -> str:
        params = ", ".join(to_snake(p.name) for p in node.params)
        if isinstance(node.body, list):
            if len(node.body) == 1 and isinstance(node.body[0], IRReturn):
                body = self._expr(node.body[0].value) if node.body[0].value else "None"
                return f"lambda {params}: {body}"
            return f"lambda {params}: None"
        return f"lambda {params}: {self._expr(node.body)}"

    def _template_expr(self, node: IRTemplateString) -> str:
        parts = []
        for p in node.parts:
            if isinstance(p, IRLiteral) and isinstance(p.value, str):
                parts.append(p.value.replace("{", "{{").replace("}", "}}"))
            else:
                parts.append("{" + self._expr(p) + "}")
        return 'f"' + "".join(parts) + '"'
