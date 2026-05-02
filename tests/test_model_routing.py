import pytest
from skills.mesh_trajectory.scripts.model_routing import (
    get_model, all_routes, CONFIG_PATH, UnknownLayerError,
)


def test_config_file_exists():
    assert CONFIG_PATH.exists(), f"missing config at {CONFIG_PATH}"


def test_layer1_is_haiku():
    assert get_model("layer1") == "haiku"


def test_layer2_is_sonnet():
    assert get_model("layer2") == "sonnet"


def test_layer3_is_opus():
    assert get_model("layer3") == "opus"


def test_lint_is_opus():
    assert get_model("lint") == "opus"


def test_compose_is_opus():
    assert get_model("compose") == "opus"


def test_all_routes_returns_full_mapping():
    routes = all_routes()
    assert routes == {
        "layer1": "haiku",
        "layer2": "sonnet",
        "layer3": "opus",
        "lint":   "opus",
        "compose": "opus",
    }


def test_unknown_layer_raises():
    with pytest.raises(UnknownLayerError, match="layer42"):
        get_model("layer42")


def test_only_known_aliases_in_config():
    allowed = {"haiku", "sonnet", "opus"}
    for layer, model in all_routes().items():
        assert model in allowed, f"layer {layer} maps to unknown alias {model}"
