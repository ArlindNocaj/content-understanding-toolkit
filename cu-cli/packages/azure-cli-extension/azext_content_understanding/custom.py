# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Thin Azure CLI adapters over framework-neutral CU operations."""

from __future__ import annotations

from typing import Any

from cu_cli_core.command_spec import ANALYZER_LIST, build_request, resolve_identifier
from cu_cli_core.errors import CuCoreError
from cu_cli_core.serialization import to_plain_value

from ._client_factory import create_content_understanding_client
from ._errors import azure_cli_error


def list_analyzers(
    cmd: Any,
    endpoint: str | None = None,
    api_version: str | None = None,
    profile_name: str | None = None,
    kind: str = "all",
    sort_by: str = "analyzerId",
) -> list[dict[str, Any]]:
    """List analyzers using Azure CLI host context and shared CU core logic."""

    try:
        request = build_request(
            ANALYZER_LIST,
            {
                "kind": kind,
                "sort_by": sort_by,
            },
        )
        client = create_content_understanding_client(
            cmd,
            endpoint=endpoint,
            api_version=api_version,
            profile_name=profile_name,
        )
        operation = resolve_identifier(ANALYZER_LIST.operation)
        result = operation(client, kind=request.kind, sort_by=request.sort_by)
        plain_result = to_plain_value(result)
    except CuCoreError as exc:
        raise azure_cli_error(exc) from exc

    if not isinstance(plain_result, list):
        raise TypeError("analyzer list operation returned a non-list result")
    return plain_result
