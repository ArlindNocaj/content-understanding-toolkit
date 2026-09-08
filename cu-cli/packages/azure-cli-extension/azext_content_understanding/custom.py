# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Thin Azure CLI adapters over framework-neutral CU operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from azure.cli.core.azclierror import InvalidArgumentValueError
from azure.cli.core.util import user_confirmation

from cu_cli_core.command_spec import (
    ANALYZE,
    ANALYZER_CREATE,
    ANALYZER_DELETE,
    ANALYZER_LIST,
    ANALYZER_SHOW,
    DEFAULTS_SET,
    DEFAULTS_SHOW,
    CommandBindingError,
    build_request,
    resolve_identifier,
)
from cu_cli_core.defaults import parse_model_kv
from cu_cli_core.errors import CuCoreError, ValidationError
from cu_cli_core.input_planning import plan_inputs
from cu_cli_core.profiles import Profile as CuProfile
from cu_cli_core.schema_validation import (
    custom_analyzer_id_error,
    parse_and_validate,
    schema_pinned_version,
)
from cu_cli_core.serialization import to_plain_value

from ._client_factory import create_content_understanding_client
from ._errors import TRANSLATABLE_ERRORS, azure_cli_error


def _client(
    cmd: Any,
    *,
    endpoint: str | None,
    api_version: str | None,
    profile_name: str | None,
) -> Any:
    return create_content_understanding_client(
        cmd,
        endpoint=endpoint,
        api_version=api_version,
        profile_name=profile_name,
    )


def _request(spec: Any, parsed: Mapping[str, Any]) -> Any:
    try:
        return build_request(spec, parsed)
    except CommandBindingError as exc:
        raise InvalidArgumentValueError(str(exc)) from exc


def _plain(value: Any) -> Any:
    return to_plain_value(value)


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
        request = _request(
            ANALYZER_LIST,
            {
                "kind": kind,
                "sort_by": sort_by,
            },
        )
        client = _client(
            cmd,
            endpoint=endpoint,
            api_version=api_version,
            profile_name=profile_name,
        )
        operation = resolve_identifier(ANALYZER_LIST.operation)
        result = operation(client, kind=request.kind, sort_by=request.sort_by)
        plain_result = to_plain_value(result)
    except TRANSLATABLE_ERRORS as exc:
        raise azure_cli_error(exc) from exc

    if not isinstance(plain_result, list):
        raise TypeError("analyzer list operation returned a non-list result")
    return plain_result


def show_analyzer(
    cmd: Any,
    analyzer_name: str,
    endpoint: str | None = None,
    api_version: str | None = None,
    profile_name: str | None = None,
) -> dict[str, Any]:
    """Return one analyzer definition."""

    try:
        request = _request(ANALYZER_SHOW, {"analyzer_name": analyzer_name})
        client = _client(
            cmd,
            endpoint=endpoint,
            api_version=api_version,
            profile_name=profile_name,
        )
        result = resolve_identifier(ANALYZER_SHOW.operation)(client, request.name)
        plain_result = _plain(result)
    except TRANSLATABLE_ERRORS as exc:
        raise azure_cli_error(exc) from exc
    if not isinstance(plain_result, dict):
        raise TypeError("analyzer show operation returned a non-object result")
    return plain_result


def create_analyzer(
    cmd: Any,
    analyzer_name: str,
    schema_path: str,
    endpoint: str | None = None,
    api_version: str | None = None,
    profile_name: str | None = None,
) -> dict[str, Any]:
    """Create an analyzer from a validated local JSON schema."""

    try:
        request = _request(
            ANALYZER_CREATE,
            {"analyzer_name": analyzer_name, "schema_path": schema_path},
        )
        analyzer_id_error = custom_analyzer_id_error(request.name)
        if analyzer_id_error:
            raise ValidationError(f"invalid analyzer name '{request.name}'.", hint=analyzer_id_error)
        parse_result, body = parse_and_validate(request.schema.read_text(encoding="utf-8"))
        if body is None:
            raise ValidationError(parse_result.errors[0].msg)
        if parse_result.errors:
            finding = parse_result.errors[0]
            raise ValidationError(
                f"invalid schema at {finding.path}: {finding.msg}",
                hint="Run 'cu analyzer validate SCHEMA' for all validation findings.",
            )
        pinned_version = schema_pinned_version(body)
        if api_version and pinned_version and api_version != pinned_version:
            raise ValidationError(
                f"schema pins apiVersion '{pinned_version}' but --api-version "
                f"'{api_version}' was passed.",
                hint="Remove --api-version or align it with the schema.",
            )
        client = _client(
            cmd,
            endpoint=endpoint,
            api_version=pinned_version or api_version,
            profile_name=profile_name,
        )
        result = resolve_identifier(ANALYZER_CREATE.operation)(client, request.name, body)
        plain_result = _plain(result)
    except OSError as exc:
        raise InvalidArgumentValueError(f"could not read schema file '{schema_path}': {exc}") from exc
    except TRANSLATABLE_ERRORS as exc:
        raise azure_cli_error(exc) from exc
    if not isinstance(plain_result, dict):
        raise TypeError("analyzer create operation returned a non-object result")
    return plain_result


def delete_analyzer(
    cmd: Any,
    analyzer_name: str,
    endpoint: str | None = None,
    api_version: str | None = None,
    profile_name: str | None = None,
    yes: bool = False,
) -> dict[str, str]:
    """Confirm and delete one analyzer."""

    try:
        request = _request(ANALYZER_DELETE, {"analyzer_name": analyzer_name, "yes": yes})
        user_confirmation(f"Delete analyzer '{request.name}'?", yes=request.yes)
        client = _client(
            cmd,
            endpoint=endpoint,
            api_version=api_version,
            profile_name=profile_name,
        )
        resolve_identifier(ANALYZER_DELETE.operation)(client, request.name)
    except TRANSLATABLE_ERRORS as exc:
        raise azure_cli_error(exc) from exc
    return {"analyzerId": request.name, "status": "deleted"}


def analyze_file(
    cmd: Any,
    file_path: str,
    analyzer_id: str | None = None,
    endpoint: str | None = None,
    api_version: str | None = None,
    profile_name: str | None = None,
) -> Any:
    """Analyze one local file and return its complete service result."""

    try:
        profile = CuProfile.load(profile_name=profile_name)
        effective_analyzer = analyzer_id or profile.default_analyzer
        if not effective_analyzer:
            raise ValidationError(
                "no analyzer was specified and no default_analyzer is configured.",
                hint="Pass --analyzer-name or configure default_analyzer in the CU profile.",
            )
        request = _request(
            ANALYZE,
            {
                "files": (Path(file_path),),
                "analyzer_id": effective_analyzer,
                "concurrency": 1,
            },
        )
        input_plan = plan_inputs(files=request.files)
        client = _client(
            cmd,
            endpoint=endpoint,
            api_version=api_version,
            profile_name=profile_name,
        )
        batch = resolve_identifier(ANALYZE.operation)(client, request, input_plan=input_plan)
        if batch.failures:
            error = batch.failures[0].error
            if isinstance(error, CuCoreError):
                raise azure_cli_error(error) from error
            if isinstance(error, Exception):
                raise error
            raise RuntimeError(str(error))
        if not batch.successes:
            raise RuntimeError("analysis completed without a result")
        return _plain(batch.successes[0].result)
    except OSError as exc:
        raise InvalidArgumentValueError(f"could not read input file '{file_path}': {exc}") from exc
    except TRANSLATABLE_ERRORS as exc:
        raise azure_cli_error(exc) from exc


def show_defaults(
    cmd: Any,
    endpoint: str | None = None,
    api_version: str | None = None,
    profile_name: str | None = None,
) -> dict[str, Any]:
    """Return Content Understanding resource defaults."""

    try:
        _request(DEFAULTS_SHOW, {})
        client = _client(
            cmd,
            endpoint=endpoint,
            api_version=api_version,
            profile_name=profile_name,
        )
        result = resolve_identifier(DEFAULTS_SHOW.operation)(client)
        plain_result = _plain(result)
    except TRANSLATABLE_ERRORS as exc:
        raise azure_cli_error(exc) from exc
    if not isinstance(plain_result, dict):
        raise TypeError("defaults show operation returned a non-object result")
    return plain_result


def set_defaults(
    cmd: Any,
    model_kv: list[str],
    endpoint: str | None = None,
    api_version: str | None = None,
    profile_name: str | None = None,
    replace: bool = False,
) -> dict[str, Any]:
    """Merge or replace Content Understanding model-deployment defaults."""

    try:
        request = _request(DEFAULTS_SET, {"model_kv": tuple(model_kv), "replace": replace})
        desired = parse_model_kv(request.models)
        client = _client(
            cmd,
            endpoint=endpoint,
            api_version=api_version,
            profile_name=profile_name,
        )
        updated, _ = resolve_identifier(DEFAULTS_SET.operation)(
            client,
            desired,
            replace=request.replace,
        )
        plain_result = _plain(updated)
    except TRANSLATABLE_ERRORS as exc:
        raise azure_cli_error(exc) from exc
    if not isinstance(plain_result, dict):
        raise TypeError("defaults set operation returned a non-object result")
    return plain_result
