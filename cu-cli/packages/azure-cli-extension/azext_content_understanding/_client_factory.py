# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Construct CU clients from Azure CLI host identity and shared CU settings."""

from __future__ import annotations

from typing import Any

from azure.cli.core._profile import Profile as AzureCliProfile
from azure.cli.core.azclierror import ArgumentUsageError, AzureConnectionError
from azure.cli.core.util import get_az_user_agent

from cu_cli_core.client import build_content_understanding_client
from cu_cli_core.profiles import Profile as CuProfile

from . import __version__


def resolve_service_settings(
    *,
    endpoint: str | None,
    api_version: str | None,
    profile_name: str | None,
) -> tuple[str, str]:
    """Resolve explicit options over environment and the selected CU profile."""

    profile = CuProfile.load(profile_name=profile_name)
    resolved_endpoint = endpoint or profile.endpoint
    if not resolved_endpoint:
        raise ArgumentUsageError(
            "No Content Understanding endpoint is configured. Pass --endpoint, set "
            "CU_ENDPOINT, or configure one with 'cu profile set endpoint <URL>'."
        )
    return resolved_endpoint, api_version or profile.api_version


def get_cli_credential(cli_ctx: Any, subscription_id: str | None = None) -> Any:
    """Return a token credential for the active Azure CLI login and subscription."""

    profile = AzureCliProfile(cli_ctx=cli_ctx)
    selected_subscription = subscription_id or profile.get_subscription_id()
    credential, _, _ = profile.get_login_credentials(subscription_id=selected_subscription)
    return credential


def get_subscription_id(cli_ctx: Any) -> str:
    """Return the subscription selected by the Azure CLI host."""

    return AzureCliProfile(cli_ctx=cli_ctx).get_subscription_id()


def get_cli_credential_for_subscription(cli_ctx: Any, subscription_id: str) -> Any:
    """Return the host credential scoped to an explicitly selected subscription."""

    credential, _, _ = AzureCliProfile(cli_ctx=cli_ctx).get_login_credentials(
        subscription_id=subscription_id
    )
    return credential


def ensure_supported_cloud(cli_ctx: Any) -> None:
    """Reject clouds not explicitly supported by this preview."""

    cloud_name = getattr(getattr(cli_ctx, "cloud", None), "name", "AzureCloud")
    if cloud_name != "AzureCloud":
        raise AzureConnectionError(
            f"Azure cloud '{cloud_name}' is not supported by this preview extension."
        )


def create_content_understanding_client(
    cmd: Any,
    *,
    endpoint: str | None,
    api_version: str | None,
    profile_name: str | None,
    subscription_id: str | None = None,
) -> Any:
    """Build a CU SDK client using Azure CLI host context."""

    resolved_endpoint, resolved_api_version = resolve_service_settings(
        endpoint=endpoint,
        api_version=api_version,
        profile_name=profile_name,
    )
    ensure_supported_cloud(cmd.cli_ctx)
    return build_content_understanding_client(
        endpoint=resolved_endpoint,
        credential=get_cli_credential(cmd.cli_ctx, subscription_id),
        api_version=resolved_api_version,
        user_agent=f"{get_az_user_agent()} content-understanding/{__version__}",
    )
