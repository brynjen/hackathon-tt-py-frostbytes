"""Resolve TypeScript import paths to Python module paths."""
from __future__ import annotations

import json
from pathlib import Path

from tt.ir import IRImport


def resolve_imports(imports: list[IRImport], map_file: Path | None = None) -> list[IRImport]:
    """Resolve TS imports using an optional mapping file."""
    mapping: dict[str, str | None] = {}
    if map_file and map_file.exists():
        mapping = json.loads(map_file.read_text(encoding="utf-8"))

    resolved: list[IRImport] = []
    for imp in imports:
        result = _resolve_one(imp, mapping)
        if result is not None:
            resolved.append(result)
    return resolved


def _resolve_one(imp: IRImport, mapping: dict[str, str | None]) -> IRImport | None:
    module = imp.module

    if module in mapping:
        py_mod = mapping[module]
        if py_mod is None:
            return None
        return IRImport(module=py_mod, names=imp.names)

    for key, val in mapping.items():
        if module.startswith(key):
            if val is None:
                return None
            return IRImport(module=val, names=imp.names)

    if module.startswith("@ghostfolio/") or module.startswith("@"):
        return None

    return imp
