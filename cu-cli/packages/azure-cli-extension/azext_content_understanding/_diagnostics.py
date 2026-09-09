# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Structured diagnostics for the Azure CLI frontend."""

from __future__ import annotations

from typing import Any

from cu_cli_core.command_spec import ENV_VAR_LIST, build_request, resolve_identifier
from cu_cli_core.defaults import (
    extract_model_deployments,
    is_defaults_not_set,
    missing_model_requirements,
)
from cu_cli_core.profiles import Profile

from ._client_factory import create_content_understanding_client, resolve_service_settings


def doctor(cmd: Any, **values: Any) -> dict[str, Any]:
    profile = Profile.load(profile_name=values.get("profile_name"))
    endpoint, api_version = resolve_service_settings(
        endpoint=values.get("endpoint"),
        api_version=values.get("api_version"),
        profile_name=values.get("profile_name"),
    )
    client = create_content_understanding_client(
        cmd,
        endpoint=endpoint,
        api_version=api_version,
        profile_name=values.get("profile_name"),
    )
    from azure.core.exceptions import HttpResponseError

    try:
        mappings = extract_model_deployments(client.get_defaults())
    except HttpResponseError as exc:
        if not is_defaults_not_set(exc):
            raise
        mappings = {}
    missing = missing_model_requirements(mappings)
    return {
        "ready": not missing,
        "endpoint": endpoint,
        "apiVersion": api_version,
        "authentication": "Microsoft Entra ID (Azure CLI)",
        "profile": profile.profile_name,
        "defaultAnalyzer": profile.default_analyzer,
        "modelDeployments": mappings,
        "missingRequirements": missing,
    }


def list_environment_variables(_cmd: Any, **values: Any) -> Any:
    request = build_request(ENV_VAR_LIST, values)
    del request
    return resolve_identifier(ENV_VAR_LIST.operation)()