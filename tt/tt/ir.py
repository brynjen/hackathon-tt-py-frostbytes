"""Intermediate representation for the TS-to-Python translation pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

@dataclass
class IRNode:
    """Base for all IR nodes."""


# ---------------------------------------------------------------------------
# Module-level
# ---------------------------------------------------------------------------

@dataclass
class IRImport(IRNode):
    module: str
    names: list[str] = field(default_factory=list)
    alias: str | None = None
    is_default: bool = False


@dataclass
class IRModule(IRNode):
    imports: list[IRImport] = field(default_factory=list)
    body: list[IRNode] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Declarations
# ---------------------------------------------------------------------------

@dataclass
class IRParam(IRNode):
    name: str
    default: IRNode | None = None
    annotation: str | None = None


@dataclass
class IRMethod(IRNode):
    name: str
    params: list[IRParam] = field(default_factory=list)
    body: list[IRNode] = field(default_factory=list)
    is_async: bool = False
    is_static: bool = False
    access: str = "public"
    return_type: str | None = None
    decorators: list[str] = field(default_factory=list)


@dataclass
class IRClass(IRNode):
    name: str
    base: str | None = None
    body: list[IRNode] = field(default_factory=list)
    is_abstract: bool = False


@dataclass
class IRFunction(IRNode):
    name: str
    params: list[IRParam] = field(default_factory=list)
    body: list[IRNode] = field(default_factory=list)
    is_async: bool = False


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------

@dataclass
class IRAssign(IRNode):
    target: IRNode
    value: IRNode
    is_const: bool = False
    annotation: str | None = None


@dataclass
class IRAugAssign(IRNode):
    target: IRNode
    op: str
    value: IRNode


@dataclass
class IRReturn(IRNode):
    value: IRNode | None = None


@dataclass
class IRIf(IRNode):
    test: IRNode
    body: list[IRNode] = field(default_factory=list)
    elif_clauses: list[tuple[IRNode, list[IRNode]]] = field(default_factory=list)
    else_body: list[IRNode] = field(default_factory=list)


@dataclass
class IRFor(IRNode):
    target: str
    iter: IRNode
    body: list[IRNode] = field(default_factory=list)


@dataclass
class IRForRange(IRNode):
    var: str
    start: IRNode
    end: IRNode
    step: IRNode | None = None
    body: list[IRNode] = field(default_factory=list)


@dataclass
class IRWhile(IRNode):
    test: IRNode
    body: list[IRNode] = field(default_factory=list)


@dataclass
class IRBreak(IRNode):
    pass


@dataclass
class IRContinue(IRNode):
    pass


@dataclass
class IRExprStatement(IRNode):
    expr: IRNode


@dataclass
class IRDelete(IRNode):
    target: IRNode


@dataclass
class IRThrow(IRNode):
    value: IRNode


@dataclass
class IRTry(IRNode):
    body: list[IRNode] = field(default_factory=list)
    handler_var: str | None = None
    handler_body: list[IRNode] = field(default_factory=list)
    finally_body: list[IRNode] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------

@dataclass
class IRName(IRNode):
    name: str


@dataclass
class IRAttr(IRNode):
    obj: IRNode
    attr: str


@dataclass
class IRCall(IRNode):
    func: IRNode
    args: list[IRNode] = field(default_factory=list)
    kwargs: dict[str, IRNode] = field(default_factory=dict)


@dataclass
class IRNew(IRNode):
    cls: IRNode
    args: list[IRNode] = field(default_factory=list)


@dataclass
class IRBinOp(IRNode):
    left: IRNode
    op: str
    right: IRNode


@dataclass
class IRUnaryOp(IRNode):
    op: str
    operand: IRNode
    prefix: bool = True


@dataclass
class IRSubscript(IRNode):
    obj: IRNode
    index: IRNode


@dataclass
class IRDict(IRNode):
    keys: list[IRNode] = field(default_factory=list)
    values: list[IRNode] = field(default_factory=list)


@dataclass
class IRList(IRNode):
    elements: list[IRNode] = field(default_factory=list)


@dataclass
class IRLiteral(IRNode):
    value: object
    raw: str | None = None


@dataclass
class IRTernary(IRNode):
    test: IRNode
    true_val: IRNode
    false_val: IRNode


@dataclass
class IRSpread(IRNode):
    value: IRNode


@dataclass
class IRArrow(IRNode):
    params: list[IRParam] = field(default_factory=list)
    body: list[IRNode] | IRNode = field(default_factory=list)


@dataclass
class IRTemplateString(IRNode):
    parts: list[IRNode] = field(default_factory=list)


@dataclass
class IRAwait(IRNode):
    value: IRNode


@dataclass
class IRTypeAssertion(IRNode):
    expr: IRNode
    type_name: str


@dataclass
class IRNullishCoalesce(IRNode):
    left: IRNode
    right: IRNode


@dataclass
class IROptionalChain(IRNode):
    expr: IRNode


@dataclass
class IRRaw(IRNode):
    """Escape hatch: raw Python code string."""
    code: str


@dataclass
class IRComputedProperty(IRNode):
    obj: IRNode
    prop: IRNode


@dataclass
class IRDestructure(IRNode):
    """Object destructuring: const { a, b } = expr."""
    names: list[str]
    aliases: dict[str, str] = field(default_factory=dict)
    source: IRNode = field(default_factory=lambda: IRName(""))
    rest: str | None = None


@dataclass
class IRArrayDestructure(IRNode):
    names: list[str | None]
    source: IRNode = field(default_factory=lambda: IRName(""))


@dataclass
class IRListComp(IRNode):
    """List comprehension: [expr for target in iter if condition]."""
    expr: IRNode
    clauses: list[tuple] = field(default_factory=list)  # [(target, iter, condition?), ...]


@dataclass
class IRDictComp(IRNode):
    """Dict comprehension: {key: val for target in iter if condition}."""
    key: IRNode
    value: IRNode
    clauses: list[tuple] = field(default_factory=list)  # [(target, iter, condition?), ...]


@dataclass
class IRGenExp(IRNode):
    """Generator expression: (expr for target in iter if condition)."""
    expr: IRNode
    clauses: list[tuple] = field(default_factory=list)  # [(target, iter, condition?), ...]


@dataclass
class IRSlice(IRNode):
    """Slice expression: obj[start:end]."""
    obj: IRNode
    start: IRNode | None = None
    end: IRNode | None = None


@dataclass
class IREmpty(IRNode):
    """Placeholder for nodes we want to skip."""
