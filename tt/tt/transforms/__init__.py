"""IR transformation passes."""
from __future__ import annotations

from tt.ir import IRModule
from tt.transforms.types import transform_types
from tt.transforms.classes import transform_classes
from tt.transforms.big_js import transform_big_js
from tt.transforms.date_fns import transform_date_fns
from tt.transforms.lodash import transform_lodash
from tt.transforms.optional_chaining import transform_optional_chaining
from tt.transforms.misc import transform_misc


ALL_TRANSFORMS: list = [
    transform_types,
    transform_classes,
    transform_big_js,
    transform_date_fns,
    transform_lodash,
    transform_optional_chaining,
    transform_misc,
]


def apply_all(module: IRModule) -> IRModule:
    """Run all transform passes in sequence."""
    for transform in ALL_TRANSFORMS:
        module = transform(module)
    return module
