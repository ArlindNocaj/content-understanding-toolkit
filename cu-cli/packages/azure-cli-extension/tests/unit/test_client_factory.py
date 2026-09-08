# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Unit tests for Azure CLI credential and CU setting adaptation."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from azure.cli.core.azclierror import ArgumentUsageError

from azext_content_understanding import _client_factory


@pytest.mark.unit
def test_resolve_service_settings_prefers_explicit_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("CU_ENDPOINT", "https://environment.example")
    monkeypatch.setenv("CU_API_VERSION", "environment-version")

    endpoint, api_version = _client_factory.resolve_service_settings(
        endpoint="https://explicit.example",
        api_version="explicit-version",
        profile_name=None,
    )

    assert endpoint == "https://explicit.example"
    assert api_version == "explicit-version"


@pytest.mark.unit
def test_resolve_service_settings_requires_endpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("CU_ENDPOINT", raising=False)
    monkeypatch.delenv("CONTENTUNDERSTANDING_ENDPOINT", raising=False)

    with pytest.raises(ArgumentUsageError, match="--endpoint"):
        _client_factory.resolve_service_settings(
            endpoint=None,
            api_version=None,
            profile_name=None,
        )


@pytest.mark.unit
def test_get_cli_credential_uses_active_subscription(monkeypatch: pytest.MonkeyPatch) -> None:
    credential = object()
    calls: dict[str, Any] = {}

    class FakeProfile:
        def __init__(self, cli_ctx: Any) -> None:
            calls["cli_ctx"] = cli_ctx

        def get_subscription_id(self) -> str:
            return "subscription-id"

        def get_login_credentials(self, *, subscription_id: str) -> tuple[Any, None, None]:
            calls["subscription_id"] = subscription_id
            return credential, None, None

    monkeypatch.setattr(_client_factory, "AzureCliProfile", FakeProfile)
    cli_ctx = SimpleNamespace()

    assert _client_factory.get_cli_credential(cli_ctx) is credential
    assert calls == {"cli_ctx": cli_ctx, "subscription_id": "subscription-id"}