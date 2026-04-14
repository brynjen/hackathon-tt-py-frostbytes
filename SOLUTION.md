# Explanation of the submission

## Solution

**`tt`** is a small **TypeScript → Python** translator aimed at the Ghostfolio portfolio calculator: it reads the real TypeScript sources under `projects/ghostfolio/`, lowers them through an **intermediate representation (IR)**, applies a few **library-specific rewrites**, and emits Python into the **`ghostfolio_pytx`** translation tree next to the FastAPI scaffold.

At a high level it behaves like a **compiler pipeline** (not a line-by-line string replacer):

1. **Parse** — tree-sitter builds a concrete syntax tree for TypeScript (`tt/parser.py`).
2. **Walk** — a visitor turns that tree into IR dataclasses (`tt/ts_walker.py`, types in `tt/ir.py`).
3. **Imports** — TypeScript module paths are normalized or dropped using a JSON map so Nest/Ghostfolio-only imports do not become invalid Python (`tt/import_resolver.py`, `tt/tt/scaffold/ghostfolio_pytx/tt_import_map.json`).
4. **Transform** — ordered passes rewrite idioms (e.g. lodash, `Big.js`, `date-fns`, optional chaining) into shapes codegen understands (`tt/transforms/`).
5. **Generate** — IR is printed as Python source, including naming tweaks such as camelCase → snake_case where appropriate (`tt/codegen.py`).

The **per-file** pipeline is centralized in `translate_source`: parse → walk → resolve imports → apply transforms → generate.

```33:40:tt/tt/translator.py
def translate_source(source: str, import_map: Path | None = None) -> str:
    """Translate TypeScript source string to Python source."""
    source_bytes = source.encode("utf-8")
    tree = parse(source)
    module = walk(tree, source_bytes)
    module.imports = resolve_imports(module.imports, import_map)
    module = apply_all(module)
    return generate(module)
```

**End-to-end translation** (which files are read and where output goes) lives in `run_translation`: it points at Ghostfolio’s `portfolio` API sources, uses the import map beside the scaffold, and writes under `app/implementation` in the chosen output directory (typically `translations/ghostfolio_pytx`).

```43:64:tt/tt/translator.py
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
```

The **ROAI** calculator class is merged with selected methods from the **base** `PortfolioCalculator` in IR space, then fixed imports and thin **adapter methods** are added so the generated class fits the Python project’s expectations (inheritance from the TS wrapper class, delegation into hand-written helpers for some API-surface methods). That logic is in `_merge_modules` and related helpers in the same file (`tt/tt/translator.py`).

**Running it:** the `tt` CLI (`tt/tt/cli.py`, entrypoint from `tt/pyproject.toml`) first runs `helptools/setup_ghostfolio_scaffold_for_tt.py` to lay down the translation project, then calls `run_translation`. Evaluators in the repo use targets such as `make translate-and-test-ghostfolio_pytx` (see `Makefile`).

---

## Coding approach

How the team arrived at this shape:

1. **Scaffold first** — The translated app is not generated from scratch. The hackathon layout expects a working **FastAPI mirror** of Ghostfolio’s API surface; `tt translate` always refreshes that tree from the scaffold script before overwriting **implementation** modules. That keeps routing, models, and glue stable while the translator focuses on **portfolio math** (`tt/tt/cli.py` calling `run_translation` after setup).

2. **AST extraction instead of pasted logic** — The requirement was to derive behavior from the **real TypeScript** under `projects/ghostfolio/.../portfolio/`, not to reimplement formulas in Python by hand. tree-sitter gives a dependable parse for `.ts` without running the Node toolchain inside `tt` (`tt/parser.py`, `tt/ts_walker.py`).

3. **IR as the contract** — TypeScript and Python syntax differ enough that mapping TS nodes directly to strings would be brittle. The team introduced explicit IR types (`tt/ir.py`) so later steps only deal with a small, Python-oriented algebra (classes, methods, calls, control flow, etc.).

4. **Targeted scope** — `run_translation` only ingests the calculator and helper files the evaluation cares about (base calculator, ROAI variant, `portfolio.helper.ts`), then emits a small set of Python modules. That keeps the walker and transforms feasible within the hackathon window (`_parse_all_sources` in `tt/tt/translator.py`).

5. **Import map for ecosystem noise** — Many TS imports (`@nestjs/*`, Prisma, `@ghostfolio/*`, lodash, etc.) are irrelevant or intentionally replaced on the Python side. Mapping them to `null` or Python paths avoids emitting broken `import` lines (`tt/import_resolver.py` and `tt_import_map.json`).

6. **Transform passes for recurring idioms** — Instead of special-casing every node in the walker, recurring patterns are normalized in sequence: types, classes, Big.js, date-fns, lodash, optional chaining, misc (`tt/transforms/__init__.py` lists `ALL_TRANSFORMS`).

7. **Integration layer in IR** — Where the translated class must match a Python ABC or reuse shared helpers, the team **injects** imports and adapter `IRMethod` nodes after the merge (`_merge_modules`, `_add_abc_adapters` in `tt/tt/translator.py`) so domain logic still comes from TS while wiring stays explicit and reviewable.

Together, that yields a solution that is **explainable** (parse → IR → transforms → codegen), **anchored to upstream Ghostfolio TS**, and **testable** through the repo’s translation + API test targets.
