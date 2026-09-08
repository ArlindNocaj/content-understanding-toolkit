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


def get_cli_credential(cli_ctx: Any) -> Any:
    """Return a token credential for the active Azure CLI login and subscription."""

    profile = AzureCliProfile(cli_ctx=cli_ctx)
    subscription_id = profile.get_subscription_id()
    credential, _, _ = profile.get_login_credentials(subscription_id=subscription_id)
    return credential


def create_content_understanding_client(
    cmd: Any,
    *,
    endpoint: str | None,
    api_version: str | None,
    profile_name: str | None,
) -> Any:
    """Build a CU SDK client using Azure CLI host context."""

    resolved_endpoint, resolved_api_version = resolve_service_settings(
        endpoint=endpoint,
        api_version=api_version,
        profile_name=profile_name,
    )
    cloud_name = getattr(getattr(cmd.cli_ctx, "cloud", None), "name", "AzureCloud")
    if cloud_name != "AzureCloud":
        raise AzureConnectionError(
            f"Azure cloud '{cloud_name}' is not supported by this preview extension."
        )
    return build_content_understanding_client(
        endpoint=resolved_endpoint,
        credential=get_cli_credential(cmd.cli_ctx),
        api_version=resolved_api_version,
        user_agent=f"{get_az_user_agent()} content-understanding/{__version__}",
    )
