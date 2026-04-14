"""Strip TypeScript type annotations and convert access modifiers."""
from __future__ import annotations

from tt.ir import IRModule, IRNode, IRClass, IRMethod, IRImport


def transform_types(module: IRModule) -> IRModule:
    """Remove type-only imports and adjust method visibility."""
    module.imports = [
        imp for imp in module.imports
        if not _is_type_only_import(imp)
    ]
    module.body = [_visit(n) for n in module.body]
    return module


def _is_type_only_import(imp: IRImport) -> bool:
    type_only_modules = {
        "@prisma/client", "@nestjs/common", "@nestjs/bull",
        "class-transformer", "class-validator",
    }
    return imp.module in type_only_modules


def _visit(node: IRNode) -> IRNode:
    if isinstance(node, IRClass):
        node.body = [_visit(n) for n in node.body]
    if isinstance(node, IRMethod):
        if node.access in ("private",):
            if not node.name.startswith("_"):
                node.name = "_" + node.name
    return node
