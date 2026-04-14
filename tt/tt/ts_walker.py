"""Walk a tree-sitter TypeScript CST and produce IR nodes."""
from __future__ import annotations

from tt.ir import (
    IRArrow, IRAssign, IRAttr, IRAugAssign, IRAwait, IRBinOp, IRBreak,
    IRCall, IRClass, IRContinue, IRDelete, IRDestructure, IRDict, IREmpty,
    IRExprStatement, IRFor, IRForRange, IRFunction, IRIf, IRImport, IRList,
    IRLiteral, IRMethod, IRModule, IRName, IRNew, IRNode, IRNullishCoalesce,
    IRParam, IRRaw, IRReturn, IRSpread, IRSubscript, IRTemplateString,
    IRTernary, IRThrow, IRTry, IRUnaryOp, IRWhile, IRArrayDestructure,
)
from tt.parser import node_text


def walk(tree, source: bytes) -> IRModule:
    """Convert a tree-sitter tree to an IRModule."""
    walker = _Walker(source)
    return walker.visit_program(tree.root_node)


class _Walker:
    def __init__(self, source: bytes) -> None:
        self._src = source

    def _text(self, node) -> str:
        return node_text(node, self._src)

    def _children_of_type(self, node, *types: str):
        return [c for c in node.children if c.type in types]

    def _child_of_type(self, node, *types: str):
        for c in node.children:
            if c.type in types:
                return c
        return None

    # ------------------------------------------------------------------
    # Module
    # ------------------------------------------------------------------

    def _collect_statements(self, children, skip_braces=False):
        """Visit children and collect non-empty statement results."""
        stmts: list[IRNode] = []
        for child in children:
            if skip_braces and child.type in ("{", "}"):
                continue
            result = self._visit_statement(child)
            if result is not None and not isinstance(result, IREmpty):
                if isinstance(result, list):
                    stmts.extend(result)
                else:
                    stmts.append(result)
        return stmts

    def visit_program(self, node) -> IRModule:
        mod = IRModule()
        for item in self._collect_statements(node.children):
            if isinstance(item, IRImport):
                mod.imports.append(item)
            else:
                mod.body.append(item)
        return mod

    # ------------------------------------------------------------------
    # Statement dispatch
    # ------------------------------------------------------------------

    def _visit_statement(self, node) -> IRNode | list[IRNode] | None:
        handler = getattr(self, f"_visit_{node.type}", None)
        if handler:
            return handler(node)
        if node.type in ("comment", "type_alias_declaration", "interface_declaration",
                         "enum_declaration", ";"):
            return IREmpty()
        if node.type == "expression_statement":
            return self._visit_expression_statement(node)
        return None

    # ------------------------------------------------------------------
    # Imports
    # ------------------------------------------------------------------

    def _visit_import_statement(self, node) -> IRImport:
        source_node = self._child_of_type(node, "string")
        module = ""
        if source_node:
            module = self._text(source_node).strip("'\"")

        names = []
        clause = self._child_of_type(node, "import_clause")
        if clause:
            named = self._child_of_type(clause, "named_imports")
            if named:
                for spec in self._children_of_type(named, "import_specifier"):
                    names.append(self._text(spec).strip())
            ident = self._child_of_type(clause, "identifier")
            if ident:
                names.append(self._text(ident))

        return IRImport(module=module, names=names)

    # ------------------------------------------------------------------
    # Exports
    # ------------------------------------------------------------------

    def _visit_export_statement(self, node) -> IRNode | None:
        for child in node.children:
            if child.type in ("class_declaration", "abstract_class_declaration"):
                return self._visit_class_declaration(child)
            if child.type in ("function_declaration",):
                return self._visit_function_declaration(child)
            if child.type in ("lexical_declaration",):
                return self._visit_lexical_declaration(child)
        return None

    # ------------------------------------------------------------------
    # Class
    # ------------------------------------------------------------------

    def _visit_class_declaration(self, node) -> IRClass:
        return self._parse_class(node)

    def _visit_abstract_class_declaration(self, node) -> IRClass:
        cls = self._parse_class(node)
        cls.is_abstract = True
        return cls

    def _parse_class(self, node) -> IRClass:
        name_node = self._child_of_type(node, "type_identifier")
        name = self._text(name_node) if name_node else "UnknownClass"

        base = None
        heritage = self._child_of_type(node, "class_heritage")
        if heritage:
            ext = self._child_of_type(heritage, "extends_clause")
            if ext:
                id_node = self._child_of_type(ext, "identifier", "type_identifier")
                if id_node:
                    base = self._text(id_node)

        body_node = self._child_of_type(node, "class_body")
        body: list[IRNode] = []
        if body_node:
            for child in body_node.children:
                if child.type == "method_definition":
                    body.append(self._visit_method_definition(child))
                elif child.type == "public_field_definition":
                    result = self._visit_field_definition(child)
                    if result:
                        body.append(result)

        return IRClass(name=name, base=base, body=body)

    def _visit_field_definition(self, node) -> IRNode | None:
        name_node = self._child_of_type(node, "property_identifier")
        if not name_node:
            return None
        name = self._text(name_node)
        value_node = None
        for c in node.children:
            if c.type not in ("property_identifier", "type_annotation", "accessibility_modifier",
                              "readonly", "static", "=", ";", "override"):
                value_node = c
                break
        value = self._visit_expr(value_node) if value_node else IRLiteral(None)
        return IRAssign(target=IRName(name), value=value)

    # ------------------------------------------------------------------
    # Method
    # ------------------------------------------------------------------

    def _visit_method_definition(self, node) -> IRMethod:
        access = "public"
        is_static = False
        is_async = False
        name = ""

        for child in node.children:
            if child.type == "accessibility_modifier":
                access = self._text(child)
            elif child.type == "static":
                is_static = True
            elif child.type == "async":
                is_async = True
            elif child.type == "property_identifier":
                name = self._text(child)
            elif child.type == "get":
                pass
            elif child.type == "set":
                pass

        params = self._extract_params(node)
        body = self._extract_body(node)

        return IRMethod(
            name=name,
            params=params,
            body=body,
            is_async=is_async,
            is_static=is_static,
            access=access,
        )

    def _extract_params(self, node) -> list[IRParam]:
        fp = self._child_of_type(node, "formal_parameters")
        if not fp:
            return []
        params: list[IRParam] = []
        for child in fp.children:
            if child.type == "required_parameter" or child.type == "optional_parameter":
                p = self._parse_param(child)
                if p:
                    params.append(p)
        return params

    def _parse_param(self, node) -> IRParam | None:
        pattern = self._child_of_type(node, "identifier")
        if pattern:
            name = self._text(pattern)
            default = None
            for c in node.children:
                if c.type == "=":
                    idx = list(node.children).index(c)
                    if idx + 1 < len(node.children):
                        default = self._visit_expr(node.children[idx + 1])
            return IRParam(name=name, default=default)

        obj_pattern = self._child_of_type(node, "object_pattern")
        if obj_pattern:
            return IRParam(name="_destructured_" + str(node.start_point[0]))

        return None

    # ------------------------------------------------------------------
    # Function
    # ------------------------------------------------------------------

    def _visit_function_declaration(self, node) -> IRFunction:
        name_node = self._child_of_type(node, "identifier")
        name = self._text(name_node) if name_node else "unknown"
        params = self._extract_params(node)
        body = self._extract_body(node)
        is_async = any(c.type == "async" for c in node.children)
        return IRFunction(name=name, params=params, body=body, is_async=is_async)

    # ------------------------------------------------------------------
    # Body extraction
    # ------------------------------------------------------------------

    def _extract_body(self, node) -> list[IRNode]:
        block = self._child_of_type(node, "statement_block")
        if not block:
            return []
        return self._visit_block(block)

    def _visit_block(self, node) -> list[IRNode]:
        return self._collect_statements(node.children, skip_braces=True)

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def _visit_expression_statement(self, node) -> IRNode:
        for child in node.children:
            if child.type == ";":
                continue
            expr = self._visit_expr(child)
            if expr:
                if isinstance(expr, (IRAssign, IRAugAssign)):
                    return expr
                return IRExprStatement(expr=expr)
        return IREmpty()

    def _visit_lexical_declaration(self, node) -> IRNode | list[IRNode]:
        results: list[IRNode] = []
        is_const = any(self._text(c) == "const" for c in node.children if c.type in ("const", "let", "var"))
        for child in node.children:
            if child.type == "variable_declarator":
                result = self._visit_variable_declarator(child, is_const)
                if isinstance(result, list):
                    results.extend(result)
                elif result:
                    results.append(result)
        return results if len(results) != 1 else results[0]

    def _visit_variable_declaration(self, node) -> IRNode | list[IRNode]:
        return self._visit_lexical_declaration(node)

    def _visit_variable_declarator(self, node, is_const: bool = False) -> IRNode | list[IRNode]:
        name_node = node.children[0] if node.children else None
        if not name_node:
            return IREmpty()

        value_node = None
        for i, c in enumerate(node.children):
            if c.type == "=":
                if i + 1 < len(node.children):
                    value_node = node.children[i + 1]

        value = self._visit_expr(value_node) if value_node else IRLiteral(None)

        if name_node.type == "object_pattern":
            return self._destructure_object(name_node, value)
        if name_node.type == "array_pattern":
            return self._destructure_array(name_node, value)

        name = self._text(name_node)
        return IRAssign(target=IRName(name), value=value, is_const=is_const)

    def _destructure_object(self, pattern_node, source: IRNode) -> list[IRNode]:
        assigns: list[IRNode] = []
        names: list[str] = []
        aliases: dict[str, str] = {}
        rest_name: str | None = None

        for child in pattern_node.children:
            if child.type == "shorthand_property_identifier_pattern":
                name = self._text(child)
                names.append(name)
            elif child.type == "pair_pattern":
                key_node = child.children[0] if child.children else None
                val_node = child.children[-1] if len(child.children) > 1 else None
                if key_node and val_node:
                    key = self._text(key_node)
                    val = self._text(val_node)
                    names.append(key)
                    if val != key:
                        aliases[key] = val
            elif child.type == "rest_pattern":
                ident = self._child_of_type(child, "identifier")
                if ident:
                    rest_name = self._text(ident)

        return [IRDestructure(names=names, aliases=aliases, source=source, rest=rest_name)]

    def _destructure_array(self, pattern_node, source: IRNode) -> list[IRNode]:
        names: list[str | None] = []
        for child in pattern_node.children:
            if child.type == "identifier":
                names.append(self._text(child))
            elif child.type == ",":
                continue
            elif child.type in ("[", "]"):
                continue
            else:
                names.append(None)
        return [IRArrayDestructure(names=names, source=source)]

    def _visit_return_statement(self, node) -> IRReturn:
        for child in node.children:
            if child.type not in ("return", ";"):
                return IRReturn(value=self._visit_expr(child))
        return IRReturn()

    def _visit_if_statement(self, node) -> IRIf:
        children = list(node.children)
        condition = None
        body: list[IRNode] = []
        elif_clauses: list[tuple[IRNode, list[IRNode]]] = []
        else_body: list[IRNode] = []

        i = 0
        while i < len(children):
            c = children[i]
            if c.type == "parenthesized_expression":
                condition = self._visit_expr(c)
            elif c.type == "statement_block":
                if condition is not None and not body:
                    body = self._visit_block(c)
                else:
                    else_body = self._visit_block(c)
            elif c.type == "else_clause":
                else_content = self._visit_else_clause(c)
                if isinstance(else_content, IRIf):
                    elif_clauses.append((else_content.test, else_content.body))
                    elif_clauses.extend(else_content.elif_clauses)
                    if else_content.else_body:
                        else_body = else_content.else_body
                else:
                    else_body = else_content if isinstance(else_content, list) else [else_content]
            elif c.type not in ("if", "(", ")", ";"):
                if condition is not None and not body:
                    stmt = self._visit_statement(c)
                    if stmt and not isinstance(stmt, IREmpty):
                        body = [stmt] if not isinstance(stmt, list) else stmt
            i += 1

        return IRIf(
            test=condition or IRLiteral(True),
            body=body,
            elif_clauses=elif_clauses,
            else_body=else_body,
        )

    def _visit_else_clause(self, node) -> IRIf | list[IRNode]:
        for child in node.children:
            if child.type == "if_statement":
                return self._visit_if_statement(child)
            if child.type == "statement_block":
                return self._visit_block(child)
        return []

    def _visit_for_statement(self, node) -> IRNode:
        children = list(node.children)
        paren_content, body_node = self._parse_for_clauses(children)

        semicolons = [i for i, c in enumerate(paren_content) if c.type == ";"]
        if len(semicolons) >= 2:
            result = self._build_for_range(paren_content, semicolons, body_node)
            if result is not None:
                return result

        body = self._visit_block(body_node) if body_node else []
        return IRWhile(test=IRLiteral(True), body=body)

    def _parse_for_clauses(self, children):
        """Extract parenthesized content and body node from for-statement children."""
        paren_content = []
        body_node = None
        in_paren = False
        for c in children:
            if c.type == "(":
                in_paren = True
                continue
            if c.type == ")":
                in_paren = False
                continue
            if in_paren:
                paren_content.append(c)
            elif c.type == "statement_block":
                body_node = c
        return paren_content, body_node

    def _build_for_range(self, paren_content, semicolons, body_node) -> IRNode | None:
        """Try to build an IRForRange from parsed for-statement clauses."""
        init_nodes = paren_content[:semicolons[0]]
        cond_nodes = paren_content[semicolons[0]+1:semicolons[1]]
        update_nodes = paren_content[semicolons[1]+1:]

        var_name, start_val = self._parse_for_init(init_nodes)
        end_val = self._parse_for_condition(cond_nodes)
        step_val = self._parse_for_update(update_nodes)

        body = self._visit_block(body_node) if body_node else []

        if var_name:
            return IRForRange(
                var=var_name,
                start=start_val,
                end=end_val,
                step=step_val,
                body=body,
            )

        return None

    def _parse_for_init(self, init_nodes) -> tuple[str | None, IRNode]:
        """Parse the initializer clause of a for statement."""
        var_name = None
        start_val = IRLiteral(0)
        if init_nodes:
            init_node = init_nodes[0]
            if init_node.type in ("lexical_declaration", "variable_declaration"):
                decl = self._visit_lexical_declaration(init_node)
                if isinstance(decl, IRAssign):
                    var_name = decl.target.name if isinstance(decl.target, IRName) else None
                    start_val = decl.value
        return var_name, start_val

    def _parse_for_condition(self, cond_nodes) -> IRNode:
        """Parse the condition clause of a for statement."""
        end_val = IRLiteral(0)
        if cond_nodes:
            cond_expr = self._visit_expr(cond_nodes[0])
            if isinstance(cond_expr, IRBinOp) and cond_expr.op in ("<", "<="):
                end_val = cond_expr.right
                if cond_expr.op == "<=":
                    end_val = IRBinOp(left=end_val, op="+", right=IRLiteral(1))
        return end_val

    def _parse_for_update(self, update_nodes) -> IRNode | None:
        """Parse the update clause of a for statement."""
        step_val = None
        if update_nodes:
            up = self._text(update_nodes[0])
            if "+=" in up:
                parts = up.split("+=")
                if len(parts) == 2:
                    step_val = IRLiteral(int(parts[1].strip()) if parts[1].strip().isdigit() else 1)
            elif "++" in up:
                step_val = IRLiteral(1)
        return step_val

    def _visit_for_in_statement(self, node) -> IRNode:
        children = list(node.children)
        target, destructure_names, body = self._parse_for_in_target(children)
        iter_expr = self._parse_for_in_iter(children)

        if destructure_names:
            destr_stmts = [
                IRAssign(
                    target=IRName(n),
                    value=IRSubscript(obj=IRName("_item"), index=IRLiteral(n)),
                )
                for n in destructure_names
            ]
            body = destr_stmts + body

        return IRFor(target=target, iter=iter_expr, body=body)

    def _parse_for_in_target(self, children) -> tuple[str, list[str], list[IRNode]]:
        """Parse the target variable and body from for-in statement children."""
        target = ""
        destructure_names: list[str] = []
        body: list[IRNode] = []

        for c in children:
            if c.type in ("identifier", "shorthand_property_identifier_pattern"):
                target = self._text(c)
            elif c.type == "object_pattern":
                destructure_names = self._extract_object_pattern_names(c)
                target = "_item"
            elif c.type == "array_pattern":
                idents = [self._text(ic) for ic in c.children if ic.type == "identifier"]
                target = ", ".join(idents) if idents else "_item"
            elif c.type in ("lexical_declaration", "variable_declaration"):
                target, destructure_names = self._parse_for_in_decl(c, target, destructure_names)
            elif c.type == "statement_block":
                body = self._visit_block(c)

        return target, destructure_names, body

    def _extract_object_pattern_names(self, pattern_node) -> list[str]:
        """Extract shorthand property names from an object pattern."""
        return [
            self._text(pc) for pc in pattern_node.children
            if pc.type == "shorthand_property_identifier_pattern"
        ]

    def _parse_for_in_decl(self, decl_node, target: str, destructure_names: list[str]) -> tuple[str, list[str]]:
        """Parse a lexical/variable declaration inside a for-in statement."""
        for dc in decl_node.children:
            if dc.type == "variable_declarator":
                name_n = dc.children[0] if dc.children else None
                if name_n and name_n.type == "identifier":
                    target = self._text(name_n)
                elif name_n and name_n.type == "array_pattern":
                    idents = [self._text(ic) for ic in name_n.children if ic.type == "identifier"]
                    target = ", ".join(idents) if idents else self._text(name_n)
                elif name_n and name_n.type == "object_pattern":
                    destructure_names = self._extract_object_pattern_names(name_n)
                    target = "_item"
        return target, destructure_names

    def _parse_for_in_iter(self, children) -> IRNode:
        """Parse the iterable expression from for-in statement children."""
        last_expr = None
        saw_of = False
        for c in children:
            if self._text(c) in ("of", "in"):
                saw_of = True
                continue
            if saw_of and c.type not in (")", "statement_block"):
                last_expr = c
                break
        if last_expr:
            return self._visit_expr(last_expr)
        return IRName("")

    def _visit_while_statement(self, node) -> IRWhile:
        cond = None
        body: list[IRNode] = []
        for c in node.children:
            if c.type == "parenthesized_expression":
                cond = self._visit_expr(c)
            elif c.type == "statement_block":
                body = self._visit_block(c)
        return IRWhile(test=cond or IRLiteral(True), body=body)

    def _visit_switch_statement(self, node) -> IRIf:
        disc = None
        for c in node.children:
            if c.type == "parenthesized_expression":
                disc = self._visit_expr(c)
                break

        body_node = self._child_of_type(node, "switch_body")
        if not body_node:
            return IRIf(test=IRLiteral(True))

        cases = self._parse_switch_cases(body_node)

        if not cases:
            return IRIf(test=IRLiteral(True))

        first_test, first_body = cases[0]
        test = IRBinOp(disc, "==", first_test) if disc and first_test else IRLiteral(True)

        elif_clauses = []
        else_body: list[IRNode] = []
        for case_val, case_body in cases[1:]:
            if case_val is None:
                else_body = case_body
            elif disc:
                elif_clauses.append((IRBinOp(disc, "==", case_val), case_body))

        return IRIf(test=test, body=first_body, elif_clauses=elif_clauses, else_body=else_body)

    def _parse_switch_cases(self, body_node) -> list[tuple[IRNode | None, list[IRNode]]]:
        """Parse all case/default clauses from a switch body."""
        cases: list[tuple[IRNode | None, list[IRNode]]] = []
        for child in body_node.children:
            if child.type == "switch_case":
                case_val, stmts = self._parse_single_case(child)
                cases.append((case_val, stmts))
            elif child.type == "switch_default":
                stmts = self._parse_default_case(child)
                cases.append((None, stmts))
        return cases

    def _parse_single_case(self, case_node) -> tuple[IRNode | None, list[IRNode]]:
        """Parse a single switch case clause."""
        case_val = None
        stmts: list[IRNode] = []
        for c in case_node.children:
            if c.type not in ("case", ":", ";"):
                if case_val is None and c.type != "statement_block":
                    case_val = self._visit_expr(c)
                else:
                    s = self._visit_statement(c)
                    if s and not isinstance(s, IREmpty):
                        if isinstance(s, list):
                            stmts.extend(s)
                        else:
                            stmts.append(s)
        stmts = [s for s in stmts if not isinstance(s, IRBreak)]
        return case_val, stmts

    def _parse_default_case(self, default_node) -> list[IRNode]:
        """Parse a switch default clause."""
        stmts: list[IRNode] = []
        for c in default_node.children:
            if c.type not in ("default", ":", ";"):
                s = self._visit_statement(c)
                if s and not isinstance(s, IREmpty):
                    if isinstance(s, list):
                        stmts.extend(s)
                    else:
                        stmts.append(s)
        stmts = [s for s in stmts if not isinstance(s, IRBreak)]
        return stmts

    def _visit_try_statement(self, node) -> IRTry:
        body: list[IRNode] = []
        handler_var = None
        handler_body: list[IRNode] = []
        finally_body: list[IRNode] = []

        for child in node.children:
            if child.type == "statement_block":
                body = self._visit_block(child)
            elif child.type == "catch_clause":
                for c in child.children:
                    if c.type == "identifier":
                        handler_var = self._text(c)
                    elif c.type == "statement_block":
                        handler_body = self._visit_block(c)
                    elif c.type == "catch_parameter":
                        ident = self._child_of_type(c, "identifier")
                        if ident:
                            handler_var = self._text(ident)
            elif child.type == "finally_clause":
                for c in child.children:
                    if c.type == "statement_block":
                        finally_body = self._visit_block(c)

        return IRTry(body=body, handler_var=handler_var, handler_body=handler_body, finally_body=finally_body)

    def _visit_break_statement(self, _node) -> IRBreak:
        return IRBreak()

    def _visit_continue_statement(self, _node) -> IRContinue:
        return IRContinue()

    def _visit_throw_statement(self, node) -> IRThrow:
        for c in node.children:
            if c.type not in ("throw", ";"):
                return IRThrow(value=self._visit_expr(c))
        return IRThrow(value=IRLiteral("Error"))

    # ------------------------------------------------------------------
    # Expression dispatch
    # ------------------------------------------------------------------

    def _visit_expr(self, node) -> IRNode:
        if node is None:
            return IRLiteral(None)

        t = node.type
        handler = getattr(self, f"_expr_{t}", None)
        if handler:
            return handler(node)

        if t == "parenthesized_expression":
            for c in node.children:
                if c.type not in ("(", ")"):
                    return self._visit_expr(c)
        if t == "non_null_expression":
            return self._visit_expr(node.children[0]) if node.children else IRLiteral(None)
        if t == "type_assertion":
            return self._visit_expr(node.children[0]) if node.children else IRLiteral(None)
        if t == "as_expression":
            return self._visit_expr(node.children[0]) if node.children else IRLiteral(None)
        if t == "satisfies_expression":
            return self._visit_expr(node.children[0]) if node.children else IRLiteral(None)

        return IRRaw(code=self._text(node))

    def _expr_identifier(self, node) -> IRName:
        return IRName(self._text(node))

    def _expr_property_identifier(self, node) -> IRName:
        return IRName(self._text(node))

    def _expr_shorthand_property_identifier(self, node) -> IRName:
        return IRName(self._text(node))

    def _expr_this(self, _node) -> IRName:
        return IRName("self")

    def _expr_number(self, node) -> IRLiteral:
        text = self._text(node)
        if "." in text:
            return IRLiteral(float(text), raw=text)
        return IRLiteral(int(text), raw=text)

    def _expr_string(self, node) -> IRLiteral:
        text = self._text(node)
        inner = text[1:-1]
        return IRLiteral(inner, raw=text)

    def _expr_template_string(self, node) -> IRTemplateString:
        parts: list[IRNode] = []
        for child in node.children:
            if child.type == "string_fragment" or child.type == "template_chars":
                parts.append(IRLiteral(self._text(child)))
            elif child.type == "template_substitution":
                for c in child.children:
                    if c.type not in ("${", "}"):
                        parts.append(self._visit_expr(c))
        return IRTemplateString(parts=parts)

    def _expr_true(self, _node) -> IRLiteral:
        return IRLiteral(True)

    def _expr_false(self, _node) -> IRLiteral:
        return IRLiteral(False)

    def _expr_null(self, _node) -> IRLiteral:
        return IRLiteral(None)

    def _expr_undefined(self, _node) -> IRLiteral:
        return IRLiteral(None)

    def _expr_array(self, node) -> IRList:
        elements = []
        for child in node.children:
            if child.type in ("[", "]", ","):
                continue
            if child.type == "spread_element":
                elements.append(IRSpread(self._visit_expr(child.children[-1])))
            else:
                elements.append(self._visit_expr(child))
        return IRList(elements=elements)

    def _expr_object(self, node) -> IRDict:
        keys: list[IRNode] = []
        values: list[IRNode] = []
        for child in node.children:
            if child.type == "pair":
                k = child.children[0] if child.children else None
                v = child.children[-1] if len(child.children) > 1 else None
                if k and v:
                    key_text = self._text(k)
                    if k.type == "computed_property_name":
                        keys.append(self._visit_expr(k.children[1]) if len(k.children) > 1 else IRLiteral(key_text))
                    else:
                        keys.append(IRLiteral(key_text))
                    values.append(self._visit_expr(v))
            elif child.type == "shorthand_property_identifier":
                name = self._text(child)
                keys.append(IRLiteral(name))
                values.append(IRName(name))
            elif child.type == "spread_element":
                keys.append(IRSpread(self._visit_expr(child.children[-1])))
                values.append(IREmpty())
            elif child.type == "method_definition":
                pass
        return IRDict(keys=keys, values=values)

    def _expr_member_expression(self, node) -> IRNode:
        children = list(node.children)
        obj_node = children[0] if children else None
        prop_node = children[-1] if len(children) > 1 else None

        if not obj_node or not prop_node:
            return IRRaw(code=self._text(node))

        obj = self._visit_expr(obj_node)

        if any(c.type == "[" for c in children):
            return IRSubscript(obj=obj, index=self._visit_expr(prop_node))

        if any(c.type == "?." for c in children):
            attr = self._text(prop_node)
            return IRAttr(obj=IRNullishCoalesce(left=obj, right=IRLiteral(None)), attr=attr)

        attr = self._text(prop_node)
        return IRAttr(obj=obj, attr=attr)

    def _expr_subscript_expression(self, node) -> IRSubscript:
        children = list(node.children)
        obj = self._visit_expr(children[0]) if children else IRName("")
        idx = IRLiteral(0)
        for c in children:
            if c.type not in ("[", "]", "?."):
                if c != children[0]:
                    idx = self._visit_expr(c)
        return IRSubscript(obj=obj, index=idx)

    def _expr_call_expression(self, node) -> IRNode:
        children = list(node.children)
        func_node = children[0] if children else None
        args_node = self._child_of_type(node, "arguments")

        func = self._visit_expr(func_node) if func_node else IRName("")
        args = self._parse_arguments(args_node) if args_node else []

        return IRCall(func=func, args=args)

    def _expr_new_expression(self, node) -> IRNew:
        children = [c for c in node.children if c.type != "new"]
        cls_node = children[0] if children else None
        args_node = self._child_of_type(node, "arguments")

        cls = self._visit_expr(cls_node) if cls_node else IRName("")
        args = self._parse_arguments(args_node) if args_node else []

        return IRNew(cls=cls, args=args)

    def _parse_arguments(self, node) -> list[IRNode]:
        args: list[IRNode] = []
        for child in node.children:
            if child.type in ("(", ")", ","):
                continue
            if child.type == "spread_element":
                args.append(IRSpread(self._visit_expr(child.children[-1])))
            else:
                args.append(self._visit_expr(child))
        return args

    def _expr_binary_expression(self, node) -> IRBinOp:
        children = list(node.children)
        left = self._visit_expr(children[0]) if children else IRLiteral(0)
        op = self._text(children[1]) if len(children) > 1 else "+"
        right = self._visit_expr(children[2]) if len(children) > 2 else IRLiteral(0)

        if op == "??":
            return IRNullishCoalesce(left=left, right=right)

        return IRBinOp(left=left, op=op, right=right)

    def _expr_unary_expression(self, node) -> IRUnaryOp:
        children = list(node.children)
        if len(children) >= 2:
            op = self._text(children[0])
            operand = self._visit_expr(children[1])
            return IRUnaryOp(op=op, operand=operand, prefix=True)
        return IRUnaryOp(op="!", operand=IRLiteral(False))

    def _expr_update_expression(self, node) -> IRAugAssign:
        text = self._text(node)
        if "++" in text:
            name = text.replace("++", "").strip()
            return IRAugAssign(target=IRName(name), op="+=", value=IRLiteral(1))
        elif "--" in text:
            name = text.replace("--", "").strip()
            return IRAugAssign(target=IRName(name), op="-=", value=IRLiteral(1))
        return IRAugAssign(target=IRRaw(code=text), op="+=", value=IRLiteral(0))

    def _expr_assignment_expression(self, node) -> IRAssign | IRAugAssign:
        children = list(node.children)
        target = self._visit_expr(children[0]) if children else IRName("")
        op_text = self._text(children[1]) if len(children) > 1 else "="
        value = self._visit_expr(children[2]) if len(children) > 2 else IRLiteral(None)

        if op_text != "=" and op_text.endswith("="):
            return IRAugAssign(target=target, op=op_text, value=value)
        return IRAssign(target=target, value=value)

    def _expr_augmented_assignment_expression(self, node) -> IRAugAssign:
        children = list(node.children)
        target = self._visit_expr(children[0]) if children else IRName("")
        op = self._text(children[1]) if len(children) > 1 else "+="
        value = self._visit_expr(children[2]) if len(children) > 2 else IRLiteral(0)
        return IRAugAssign(target=target, op=op, value=value)

    def _expr_ternary_expression(self, node) -> IRTernary:
        children = [c for c in node.children if c.type not in ("?", ":")]
        test = self._visit_expr(children[0]) if children else IRLiteral(True)
        true_val = self._visit_expr(children[1]) if len(children) > 1 else IRLiteral(None)
        false_val = self._visit_expr(children[2]) if len(children) > 2 else IRLiteral(None)
        return IRTernary(test=test, true_val=true_val, false_val=false_val)

    def _expr_arrow_function(self, node) -> IRArrow:
        params: list[IRParam] = []
        body: list[IRNode] | IRNode = []

        for child in node.children:
            if child.type == "formal_parameters":
                for p in child.children:
                    if p.type in ("required_parameter", "optional_parameter"):
                        param = self._parse_param(p)
                        if param:
                            params.append(param)
                    elif p.type == "identifier":
                        params.append(IRParam(name=self._text(p)))
            elif child.type == "identifier":
                if not params:
                    params.append(IRParam(name=self._text(child)))
                else:
                    body = self._visit_expr(child)
            elif child.type == "statement_block":
                body = self._visit_block(child)
            elif child.type not in ("=>", "(", ")", ",", "async"):
                body = self._visit_expr(child)

        return IRArrow(params=params, body=body)

    def _expr_await_expression(self, node) -> IRAwait:
        children = [c for c in node.children if c.type != "await"]
        return IRAwait(value=self._visit_expr(children[0]) if children else IRLiteral(None))

    def _expr_spread_element(self, node) -> IRSpread:
        children = [c for c in node.children if c.type != "..."]
        return IRSpread(value=self._visit_expr(children[0]) if children else IRName(""))

    def _expr_typeof_expression(self, node) -> IRCall:
        children = [c for c in node.children if c.type != "typeof"]
        arg = self._visit_expr(children[0]) if children else IRLiteral(None)
        return IRCall(func=IRName("type"), args=[arg])

    def _expr_regex(self, node) -> IRRaw:
        return IRRaw(code=f"re.compile(r'{self._text(node)}')")
