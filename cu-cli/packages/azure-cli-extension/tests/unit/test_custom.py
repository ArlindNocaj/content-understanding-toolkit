# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Unit tests for the analyzer-list Azure CLI adapter."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from azure.cli.core.azclierror import InvalidArgumentValueError

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

    def get_analyzer(self, analyzer_id: str) -> FakeAnalyzer:
        return FakeAnalyzer(analyzer_id, "Selected analyzer")

    def begin_create_analyzer(self, analyzer_id: str, body: dict[str, Any]) -> Any:
        return SimpleNamespace(
            result=lambda: FakeAnalyzer(analyzer_id, str(body.get("description", "Created")))
        )

    def delete_analyzer(self, analyzer_id: str) -> None:
        assert analyzer_id

    def begin_analyze_binary(self, *, analyzer_id: str, binary_input: bytes) -> Any:
        return SimpleNamespace(
            result=lambda: {
                "analyzerId": analyzer_id,
                "contentLength": len(binary_input),
            }
        )

    def get_defaults(self) -> Any:
        return SimpleNamespace(
            as_dict=lambda: {"modelDeployments": {"gpt-5.2": "existing"}},
            model_deployments={"gpt-5.2": "existing"},
        )

    def update_defaults(self, *, model_deployments: dict[str, str]) -> Any:
        return SimpleNamespace(as_dict=lambda: {"modelDeployments": model_deployments})


def patch_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        custom,
        "create_content_understanding_client",
        lambda cmd, **kwargs: FakeClient(),
    )


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


@pytest.mark.unit
def test_show_analyzer_returns_plain_object(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_client(monkeypatch)

    result = custom.show_analyzer(SimpleNamespace(), "prebuilt-layout")

    assert result == {
        "analyzerId": "prebuilt-layout",
        "description": "Selected analyzer",
    }


@pytest.mark.unit
def test_create_analyzer_validates_schema_and_returns_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_client(monkeypatch)
    schema_path = tmp_path / "analyzer.json"
    schema_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        custom,
        "parse_and_validate",
        lambda text: (
            SimpleNamespace(errors=[]),
            {"description": "Created analyzer"},
        ),
    )

    result = custom.create_analyzer(SimpleNamespace(), "ContosoInvoice", str(schema_path))

    assert result == {
        "analyzerId": "ContosoInvoice",
        "description": "Created analyzer",
    }


@pytest.mark.unit
def test_delete_analyzer_uses_native_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_client(monkeypatch)
    calls: list[tuple[str, bool]] = []
    monkeypatch.setattr(
        custom,
        "user_confirmation",
        lambda message, yes: calls.append((message, yes)),
    )

    result = custom.delete_analyzer(SimpleNamespace(), "ContosoInvoice", yes=True)

    assert result == {"analyzerId": "ContosoInvoice", "status": "deleted"}
    assert calls == [("Delete analyzer 'ContosoInvoice'?", True)]


@pytest.mark.unit
def test_analyze_file_returns_plain_service_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_client(monkeypatch)
    input_path = tmp_path / "invoice.pdf"
    input_path.write_bytes(b"invoice")
    monkeypatch.setattr(
        custom.CuProfile,
        "load",
        lambda **kwargs: SimpleNamespace(default_analyzer=None),
    )

    result = custom.analyze_file(
        SimpleNamespace(),
        str(input_path),
        analyzer_id="prebuilt-invoice",
    )

    assert result == {"analyzerId": "prebuilt-invoice", "contentLength": 7}


@pytest.mark.unit
def test_analyze_file_uses_profile_default_analyzer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_client(monkeypatch)
    input_path = tmp_path / "invoice.pdf"
    input_path.write_bytes(b"invoice")
    monkeypatch.setattr(
        custom.CuProfile,
        "load",
        lambda **kwargs: SimpleNamespace(default_analyzer="profile-analyzer"),
    )

    result = custom.analyze_file(SimpleNamespace(), str(input_path))

    assert result["analyzerId"] == "profile-analyzer"


@pytest.mark.unit
def test_analyze_file_validates_input_before_creating_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        custom.CuProfile,
        "load",
        lambda **kwargs: SimpleNamespace(default_analyzer=None),
    )
    monkeypatch.setattr(
        custom,
        "create_content_understanding_client",
        lambda *args, **kwargs: pytest.fail("client must not be created for a missing file"),
    )

    with pytest.raises(InvalidArgumentValueError, match="does not exist"):
        custom.analyze_file(
            SimpleNamespace(),
            str(tmp_path / "missing.pdf"),
            analyzer_id="prebuilt-invoice",
        )


@pytest.mark.unit
def test_show_defaults_returns_plain_object(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_client(monkeypatch)

    result = custom.show_defaults(SimpleNamespace())

    assert result == {"modelDeployments": {"gpt-5.2": "existing"}}


@pytest.mark.unit
def test_set_defaults_parses_and_merges_models(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_client(monkeypatch)

    result = custom.set_defaults(
        SimpleNamespace(),
        ["text-embedding-3-large=embedding"],
    )

    assert result["modelDeployments"]["gpt-5.2"] == "existing"
    assert result["modelDeployments"]["text-embedding-3-large"] == "embedding"
    assert result["modelDeployments"]["prebuilt-analyzer-embedding"] == "embedding"