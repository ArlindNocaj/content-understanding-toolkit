# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Focused tests for Preview 2 and Preview 3 adapters."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from azext_content_understanding import _analyzers, _diagnostics, _profiles


@pytest.mark.unit
def test_profile_get_redacts_saved_api_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_CONFIG_DIR", str(tmp_path))
    config = tmp_path / "config"
    config.write_text("[cu]\ndefault.api_key = top-secret\n", encoding="utf-8")

    result = _profiles.get_profile(
        SimpleNamespace(), profile_key="api_key", profile_name="default"
    )

    assert result["value"] == "***redacted***"
    assert "top-secret" not in str(result)


@pytest.mark.unit
def test_profile_delete_uses_native_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AZURE_CONFIG_DIR", str(tmp_path))
    config = tmp_path / "config"
    config.write_text("[cu]\ntest._created = true\n", encoding="utf-8")
    confirmations: list[tuple[str, bool]] = []
    monkeypatch.setattr(
        _profiles,
        "user_confirmation",
        lambda message, yes: confirmations.append((message, yes)),
    )

    result = _profiles.delete_profile(SimpleNamespace(), profile_name="test", yes=True)

    assert result["deleted"] is True
    assert confirmations == [("Delete CU profile 'test'?", True)]


@pytest.mark.unit
def test_env_var_list_redacts_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CU_API_KEY", "top-secret")
    monkeypatch.setenv("CU_ENDPOINT", "https://example.test")

    result = _diagnostics.list_environment_variables(SimpleNamespace())

    keyed = {item["name"]: item for item in result}
    assert keyed["CU_API_KEY"]["value"] == "********"
    assert "top-secret" not in str(result)


@pytest.mark.unit
def test_analyzer_copy_uses_host_resolved_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_client = SimpleNamespace()
    destination_client = SimpleNamespace()
    source_resource = SimpleNamespace(
        arm_id="/subscriptions/s/resourceGroups/r/providers/Microsoft.CognitiveServices/accounts/a",
        endpoint="https://a.services.ai.azure.com/",
        subscription_id="s",
        resource_group="r",
        account_name="a",
        region="eastus",
    )
    destination_resource = SimpleNamespace(
        arm_id="/subscriptions/d/resourceGroups/r/providers/Microsoft.CognitiveServices/accounts/b",
        endpoint="https://b.services.ai.azure.com/",
        subscription_id="d",
        resource_group="r",
        account_name="b",
        region="westus",
    )
    resources = {"a": source_resource, "b": destination_resource}
    clients = {
        source_resource.endpoint: source_client,
        destination_resource.endpoint: destination_client,
    }
    monkeypatch.setattr(
        _analyzers,
        "resolve_resource",
        lambda cmd, selector, **kwargs: resources[selector],
    )
    monkeypatch.setattr(
        _analyzers,
        "create_content_understanding_client",
        lambda cmd, endpoint, **kwargs: clients[endpoint],
    )
    monkeypatch.setattr(
        _analyzers,
        "resources_equal",
        lambda left, right: left.arm_id == right.arm_id,
    )
    operations = __import__(
        "cu_cli_core.operations.analyzer_copy", fromlist=["copy_analyzer"]
    )
    monkeypatch.setattr(operations, "get_copy_source_analyzer", lambda *args: object())
    monkeypatch.setattr(operations, "collect_custom_dependencies", lambda value: [])
    monkeypatch.setattr(operations, "preflight_dependencies_on_target", lambda *args: [])
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        operations,
        "copy_analyzer",
        lambda *args, **kwargs: captured.update(args=args, kwargs=kwargs) or {"copied": True},
    )
    from cu_cli_core.command_spec import resolve_identifier

    resolve_identifier.cache_clear()

    result = _analyzers.copy_analyzer(
        SimpleNamespace(),
        named_source="source",
        named_destination="destination",
        source_resource="a",
        destination_resource="b",
    )

    assert result == {"copied": True}
    assert captured["args"][0] is source_client
    assert captured["kwargs"]["target_client"] is destination_client
    assert captured["kwargs"]["source_azure_resource_id"] == source_resource.arm_id
    assert captured["kwargs"]["target_azure_resource_id"] == destination_resource.arm_id
