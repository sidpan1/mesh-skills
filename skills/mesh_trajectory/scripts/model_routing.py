"""Per-layer model routing for the MESH trajectory pipeline.

The config at skills/mesh_trajectory/config/model_routing.yaml is the
single source of truth. The SKILL.md flow shells out to this module's CLI
at dispatch time to resolve which model a given layer should use.

CLI usage:
    python -m skills.mesh_trajectory.scripts.model_routing layer1
    # prints: haiku

Library usage:
    from skills.mesh_trajectory.scripts.model_routing import get_model
    model = get_model("layer1")  # "haiku"
"""
from __future__ import annotations

import sys
from pathlib import Path
import yaml

CONFIG_PATH = Path(__file__).parent.parent / "config" / "model_routing.yaml"

ALLOWED_MODELS = frozenset({"haiku", "sonnet", "opus"})


class UnknownLayerError(KeyError):
    pass


class InvalidModelError(ValueError):
    pass


def all_routes() -> dict[str, str]:
    """Return the full {layer: model} mapping. Validates allow-list."""
    raw = yaml.safe_load(CONFIG_PATH.read_text())
    if not isinstance(raw, dict):
        raise InvalidModelError(f"config root must be a mapping, got {type(raw).__name__}")
    routes: dict[str, str] = {}
    for layer, model in raw.items():
        if model not in ALLOWED_MODELS:
            raise InvalidModelError(
                f"layer {layer!r} maps to {model!r}; allowed: {sorted(ALLOWED_MODELS)}"
            )
        routes[str(layer)] = str(model)
    return routes


def get_model(layer: str) -> str:
    routes = all_routes()
    if layer not in routes:
        raise UnknownLayerError(
            f"unknown layer {layer!r}; known: {sorted(routes.keys())}"
        )
    return routes[layer]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: model_routing.py <layer>", file=sys.stderr)
        print(f"known layers: {sorted(all_routes().keys())}", file=sys.stderr)
        return 2
    layer = sys.argv[1]
    try:
        print(get_model(layer))
    except UnknownLayerError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
