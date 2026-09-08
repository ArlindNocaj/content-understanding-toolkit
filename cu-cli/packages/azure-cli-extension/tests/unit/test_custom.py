# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Unit tests for the analyzer-list Azure CLI adapter."""

from types import SimpleNamespace
from typing import Any

import pytest

from azext_content_understanding import custom


class FakeAnalyzer:
    def __init__(self, analyzer_id: str, description: str) -> None:
        self.analyzer_id = analyzer_id
        self.description = description

    def as_dict(self) -> dict[str, str]:
        return {
            "analyzerId": self.analyzer_id,
            "description": self.description,
        }


class FakeClient:
    def list_analyzers(self) -> list[FakeAnalyzer]:
        return [
            FakeAnalyzer("z-custom", "Custom analyzer"),
            FakeAnalyzer("prebuilt-layout", "Prebuilt analyzer"),
        ]


@pytest.mark.unit
def test_list_analyzers_delegates_filter_sort_and_serialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_create_client(cmd: Any, **kwargs: Any) -> FakeClient:
        captured.update(kwargs)
        return FakeClient()

    monkeypatch.setattr(custom, "create_content_understanding_client", fake_create_client)

    result = custom.list_analyzers(
        SimpleNamespace(cli_ctx=object()),
        endpoint="https://example.services.ai.azure.com",
        api_version="2025-11-01",
        profile_name="dev",
        kind="prebuilt",
        sort_by="analyzerId",
    )

    assert result == [
        {
            "analyzerId": "prebuilt-layout",
            "description": "Prebuilt analyzer",
        }
    ]
    assert captured == {
        "endpoint": "https://example.services.ai.azure.com",
        "api_version": "2025-11-01",
        "profile_name": "dev",
    }


@pytest.mark.unit
def test_list_analyzers_does_not_import_standalone_frontend() -> None:
    import sys

    assert "cu_cli" not in sys.modules
    assert "click" not in sys.modules
    assert "rich" not in sys.modules