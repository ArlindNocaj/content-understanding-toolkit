# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from pathlib import Path

import pytest

from azext_content_understanding import _infra_models
from azext_content_understanding._infra_models import DeployableModel
from cu_cli_core.errors import ValidationError

pytestmark = pytest.mark.unit


def _model(name: str, version: str, kind: str, *, default: bool = False) -> DeployableModel:
    return DeployableModel(name, version, "OpenAI", kind, "GlobalStandard", 1, default)


def test_supported_models_accepts_sdk_and_wire_shapes() -> None:
    wire = {"supportedModels": {"completion": ["GPT-5"], "embedding": ["Embedding"]}}

    result = _infra_models._supported_models(wire)

    assert result == {"completion": {"gpt-5"}, "embedding": {"embedding"}}


def test_recommended_prefers_known_default_versions() -> None:
    candidates = [
        _model("gpt-5", "1", "completion", default=True),
        _model("gpt-5", "2", "completion"),
        _model("text-embedding-3-large", "1", "embedding", default=True),
    ]

    selected = _infra_models._recommended(candidates)

    assert [item.selector for item in selected] == ["gpt-5@1", "text-embedding-3-large@1"]


def test_select_requires_version_for_ambiguous_family() -> None:
    candidates = [_model("gpt-5", "1", "completion"), _model("gpt-5", "2", "completion")]

    with pytest.raises(ValidationError, match="multiple deployable versions"):
        _infra_models._select(candidates, ["gpt-5"])


def test_none_writes_empty_model_file_without_clients(tmp_path: Path) -> None:
    output = tmp_path / "infra/models.json"

    result = _infra_models.setup_models(object(), selection="none", out_path=str(output))

    assert output.read_text(encoding="utf-8") == "[]\n"
    assert result == {"models": [], "outputFile": str(output), "deployed": False}